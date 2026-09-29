"""The show generator: one structured request per idea; code casts the hosts (research R9).

The model judges the idea and describes the show. It never names a host: whatever names it
writes are ignored, and `HostCaster` casts names and voices that suit the practice language.
A show that comes back is a draft; nothing here is stored (spec Key Entities).
"""

import json
import logging
from dataclasses import dataclass

from app.podcasts.catalog import LEARNER_ROLES, PERSONALITIES, TITLE_MAX_LENGTH
from app.podcasts.prompts import SHOW_JSON_SCHEMA, ShowIdea, build_generator_prompt
from app.podcasts.services.casting import Host, HostCaster
from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

__all__ = ["GeneratedShow", "ShowDeclined", "ShowGenerator", "ShowIdea", "UnreadableShowError"]

logger = logging.getLogger(__name__)

UNREADABLE_SHOW = "The show came back unreadable. Please try again."
HOST_COUNT = 2
USER_ROLE = "user"


class ShowDeclined(Exception):  # noqa: N818 — reads as what happened to the idea
    """The model judged the idea unsuitable (FR-024). Its reason is logged, never shown."""


class UnreadableShowError(LLMError):
    """The model's show could not be read. Shown as a plain retry message (503)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, UNREADABLE_SHOW)


@dataclass(frozen=True, slots=True)
class GeneratedShow:
    title: str
    premise: str
    topic: str
    learner_role: str
    hosts: tuple[Host, Host]


@dataclass(frozen=True, slots=True)
class _ShowReply:
    """The model's show, checked against the catalogues, before any host is cast."""

    title: str
    premise: str
    topic: str
    learner_role: str
    personalities: tuple[str, str]
    angles: tuple[str | None, str | None]


class ShowGenerator:
    def __init__(self, structured_llm: StructuredLLMProvider, caster: HostCaster) -> None:
        self._llm = structured_llm
        self._caster = caster

    def generate(self, idea: ShowIdea) -> GeneratedShow:
        """A draft show for `idea`. Raises ShowDeclined, or an LLMError the router turns into 503."""
        prompt = build_generator_prompt(idea)
        raw = self._llm.chat_json([ChatMessage(USER_ROLE, prompt)], SHOW_JSON_SCHEMA)
        reply = _parse_reply(raw)
        hosts = self._caster.cast_personalities(
            reply.personalities, idea.languages.target_code, idea.learner_name, reply.angles
        )
        return GeneratedShow(reply.title, reply.premise, reply.topic, reply.learner_role, hosts)


def _parse_reply(raw: str) -> _ShowReply:
    try:
        parsed = json.loads(raw)
        if not parsed["is_suitable"]:
            logger.info("The generator declined an idea: %s", parsed.get("decline_reason", ""))
            raise ShowDeclined("The idea was judged unsuitable.")
        return _show_reply(parsed)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UnreadableShowError(f"malformed show reply: {exc}") from exc


def _show_reply(parsed: dict) -> _ShowReply:
    hosts = parsed["hosts"]
    if len(hosts) != HOST_COUNT:
        raise ValueError(f"a show needs {HOST_COUNT} hosts, not {len(hosts)}")
    lead, second = (_known(host["personality"], PERSONALITIES) for host in hosts)
    return _ShowReply(
        title=_text(parsed["title"], TITLE_MAX_LENGTH),
        premise=_text(parsed["premise"]),
        topic=_text(parsed["topic"], TITLE_MAX_LENGTH),
        learner_role=_known(parsed["learner_role"], LEARNER_ROLES),
        personalities=(lead, _next_free(second, lead)),
        angles=tuple(_angle(host.get("angle")) for host in hosts),
    )


def _text(value: object, max_length: int | None = None) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("a show's title, premise and topic cannot be blank")
    return text[:max_length] if max_length else text


def _known(value: object, catalogue) -> str:
    if value not in catalogue:
        raise ValueError(f"{value!r} is not in the catalogue")
    return str(value)


def _next_free(personality: str, taken: str) -> str:
    """A duplicate personality becomes the catalogue's next one, wrapping at the end."""
    if personality != taken:
        return personality
    order = list(PERSONALITIES)
    return order[(order.index(personality) + 1) % len(order)]


def _angle(value: object) -> str | None:
    angle = str(value or "").strip()
    return angle or None
