"""SubjectCheck: Today's subject is judged by the same rule as a show idea (011 research R14).

One structured call through the selected provider, made only when a subject is given. A decline
is logged with its reason and refused with a plain message; a provider failure is raised as is.
"""

import json
import logging

from app.podcasts.prompts import SUBJECT_CHECK_JSON_SCHEMA, subject_check_prompt
from app.practice_languages import ConversationLanguages
from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

logger = logging.getLogger(__name__)

SUBJECT_DECLINED = "That subject can't be used for an episode. Change it or clear it, then start."
UNREADABLE_CHECK = "The subject check came back unreadable. Please try again."
USER_ROLE = "user"


class SubjectDeclined(Exception):  # noqa: N818 — reads as what happened to the subject
    def __init__(self) -> None:
        super().__init__(SUBJECT_DECLINED)


class SubjectCheck:
    def __init__(self, structured_llm: StructuredLLMProvider) -> None:
        self._llm = structured_llm

    def check(self, subject: str, languages: ConversationLanguages) -> None:
        """Return when the subject is suitable; raise SubjectDeclined or LLMError otherwise."""
        prompt = subject_check_prompt(subject, languages)
        raw = self._llm.chat_json([ChatMessage(USER_ROLE, prompt)], SUBJECT_CHECK_JSON_SCHEMA)
        verdict = _read(raw)
        if not verdict.get("is_suitable"):
            logger.info("Today's subject declined: %s", verdict.get("decline_reason", ""))
            raise SubjectDeclined()


def _read(raw: str) -> dict:
    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError as unreadable:
        raise LLMError(f"unreadable subject check: {raw[:80]}", UNREADABLE_CHECK) from unreadable
    if not isinstance(verdict, dict):
        raise LLMError("subject check was not an object", UNREADABLE_CHECK)
    return verdict
