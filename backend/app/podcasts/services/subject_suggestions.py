"""SubjectSuggester: Suggest subjects, up to three new ones for an episode (011 research R20).

One structured call through the selected provider, only when the learner presses Suggest
subjects. The reply is trimmed and filtered here: nothing too long, nothing covered, nothing
already shown, nothing twice. Nothing is stored.
"""

import json
from dataclasses import dataclass

from app.podcasts.catalog import SUBJECT_SUGGESTIONS, TODAY_SUBJECT_MAX_LENGTH
from app.podcasts.prompts import (
    SUBJECT_SUGGESTIONS_JSON_SCHEMA,
    ShowBrief,
    subject_suggestion_prompt,
)
from app.podcasts.services.names import fold
from app.practice_languages import ConversationLanguages
from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

UNREADABLE_SUBJECTS = "The suggestions came back unreadable. Please try again."
USER_ROLE = "user"


@dataclass(frozen=True, slots=True)
class SubjectRequest:
    show: ShowBrief
    languages: ConversationLanguages
    interests: tuple[str, ...] = ()
    covered: tuple[str, ...] = ()
    """The series' covered topics, in the conversation's language."""
    avoid: tuple[str, ...] = ()
    """Subjects already shown on this setup."""


class SubjectSuggester:
    def __init__(self, structured_llm: StructuredLLMProvider) -> None:
        self._llm = structured_llm

    def suggest(self, request: SubjectRequest) -> tuple[str, ...]:
        """Up to `SUBJECT_SUGGESTIONS` new subjects; empty when nothing new came back."""
        prompt = subject_suggestion_prompt(request)
        messages = [ChatMessage(USER_ROLE, prompt)]
        raw = self._llm.chat_json(messages, SUBJECT_SUGGESTIONS_JSON_SCHEMA)
        return _kept_subjects(_read(raw), request)


def _read(raw: str) -> list[str]:
    try:
        subjects = json.loads(raw).get("subjects")
    except (json.JSONDecodeError, AttributeError) as unreadable:
        raise LLMError("unreadable subject suggestions", UNREADABLE_SUBJECTS) from unreadable
    if not isinstance(subjects, list):
        raise LLMError("subject suggestions without a list", UNREADABLE_SUBJECTS)
    return [subject for subject in subjects if isinstance(subject, str)]


def _kept_subjects(subjects: list[str], request: SubjectRequest) -> tuple[str, ...]:
    """Trimmed, short enough, and new: not covered, not shown, not repeated."""
    seen = {fold(text) for text in (*request.covered, *request.avoid)}
    kept: list[str] = []
    for subject in (" ".join(raw.split()) for raw in subjects):
        if not subject or len(subject) > TODAY_SUBJECT_MAX_LENGTH or fold(subject) in seen:
            continue
        seen.add(fold(subject))
        kept.append(subject)
    return tuple(kept[:SUBJECT_SUGGESTIONS])
