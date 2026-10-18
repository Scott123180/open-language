"""Find a new show: seeds drawn in code, one structured call, duplicates dropped (010 R10).

Seeds give variety a small model asked for "five different shows" does not, as Surprise me's
do (007 R9). Every show is parsed and judged as the generator's are; an unsuitable, unreadable
or duplicate one is dropped and never shown. Nothing here is stored (FR-019).
"""

import json
import logging
import random
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from app.podcasts.catalog import INTEREST_SEEDS, MIN_SUGGESTIONS, SHOW_TEMPLATES, SUGGESTION_SEEDS
from app.podcasts.prompts import DISCOVERY_JSON_SCHEMA, discovery_prompt
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.generator import GeneratedShow, parse_show
from app.podcasts.services.surprise import SURPRISE_ANGLES, SURPRISE_TOPICS, SurpriseIdea
from app.practice_languages import ConversationLanguages
from app.services.llm.base import ChatMessage, StructuredLLMProvider

logger = logging.getLogger(__name__)

USER_ROLE = "user"
_UNREADABLE = (KeyError, TypeError, ValueError, AttributeError)


class NotEnoughSuggestions(Exception):  # noqa: N818 — reads as what happened
    """Fewer than MIN_SUGGESTIONS shows survived, even after one top-up call (503)."""


def normalise_title(title: str) -> str:
    """A title for comparison: casefolded, punctuation dropped, spacing collapsed."""
    kept = "".join(" " if unicodedata.category(char).startswith("P") else char for char in title)
    return " ".join(kept.casefold().split())


class SuggestionSeeds:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def draw(
        self, interests: Sequence[str], count: int = SUGGESTION_SEEDS
    ) -> tuple[SurpriseIdea, ...]:
        """Distinct (topic, angle) seeds: INTEREST_SEEDS of them from the learner's interests
        when there are some, the rest from the built-in everyday topics (US5-4)."""
        from_interests = min(INTEREST_SEEDS, count) if interests else 0
        chosen = {interest.casefold() for interest in interests}
        built_in = [topic for topic in SURPRISE_TOPICS if topic.casefold() not in chosen]
        topics = [self._rng.choice(list(interests)) for _ in range(from_interests)]
        topics += self._rng.sample(built_in, count - from_interests)
        angles = self._rng.sample(SURPRISE_ANGLES, count)
        return tuple(
            SurpriseIdea(topic, angle) for topic, angle in zip(topics, angles, strict=True)
        )


@dataclass(frozen=True)
class SuggestionContext:
    """What a request knows: the titles not to repeat, the interests, and the languages."""

    avoid_titles: tuple[str, ...]
    interests: tuple[str, ...]
    mine_titles: tuple[str, ...]
    languages: ConversationLanguages
    learner_name: str | None


class ShowDiscovery:
    def __init__(
        self, structured_llm: StructuredLLMProvider, caster: HostCaster, seeds: SuggestionSeeds
    ) -> None:
        self._llm = structured_llm
        self._caster = caster
        self._seeds = seeds

    def suggest(self, context: SuggestionContext) -> list[GeneratedShow]:
        """Three to five new shows; one top-up call for a shortfall, then NotEnoughSuggestions."""
        taken = {normalise_title(title) for title in _seen_titles(context)}
        shows = self._round(self._seeds.draw(context.interests), context, taken)
        if len(shows) < MIN_SUGGESTIONS:
            fresh = self._seeds.draw(context.interests, SUGGESTION_SEEDS - len(shows))
            shows += self._round(fresh, context, taken)
        if len(shows) < MIN_SUGGESTIONS:
            raise NotEnoughSuggestions(f"{len(shows)} shows survived")
        return shows[:SUGGESTION_SEEDS]

    def _round(
        self, seeds: Sequence[SurpriseIdea], context: SuggestionContext, taken: set[str]
    ) -> list[GeneratedShow]:
        prompt = discovery_prompt(seeds, context.avoid_titles, context.languages)
        raw = self._llm.chat_json([ChatMessage(USER_ROLE, prompt)], DISCOVERY_JSON_SCHEMA)
        shows = []
        for item in _show_items(raw):
            show = self._readable_show(item, context)
            if show is not None and normalise_title(show.title) not in taken:
                taken.add(normalise_title(show.title))
                shows.append(show)
        return shows

    def _readable_show(self, item: object, context: SuggestionContext) -> GeneratedShow | None:
        """The show, cast by code, or None when it is unsuitable or cannot be read (FR-018)."""
        try:
            if not item["is_suitable"]:
                return None
            reply = parse_show(item)
        except _UNREADABLE as unreadable:
            logger.info("Find a new show dropped an unreadable show: %s", unreadable)
            return None
        language, name = context.languages.target_code, context.learner_name
        hosts = self._caster.cast_personalities(reply.personalities, language, name, reply.angles)
        return GeneratedShow(reply.title, reply.premise, reply.topic, reply.learner_role, hosts)


def _seen_titles(context: SuggestionContext) -> tuple[str, ...]:
    ready_made = tuple(template.title for template in SHOW_TEMPLATES.values())
    return (*ready_made, *context.mine_titles, *context.avoid_titles)


def _show_items(raw: str) -> list:
    try:
        items = json.loads(raw)["shows"]
    except _UNREADABLE as unreadable:
        logger.info("Find a new show got an unreadable reply: %s", unreadable)
        return []
    return items if isinstance(items, list) else []
