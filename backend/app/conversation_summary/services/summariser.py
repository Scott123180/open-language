"""Summariser: a short, grounded summary of the conversation so far (research R13).

It reads saved lines only, through the stateless structured provider, never the conversation's
session, so opening a summary adds, skips and advances nothing (FR-041). Long transcripts are
folded in chunks; a cached summary covers everything up to its last line at its level.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass

from app.conversation_levels import ConversationLevel
from app.conversation_summary.prompts import (
    MAX_SUMMARY_POINTS,
    SUMMARY_SCHEMA,
    build_summary_prompt,
)
from app.conversation_summary.services.speaker_names import SpeakerNames
from app.conversation_summary.services.storage import StoredSummary, SummaryPoint, SummaryStorage
from app.practice_languages import ConversationLanguages
from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

SUMMARY_CHUNK_CHARACTERS = 6000
MIN_LINES_TO_SUMMARISE = 2
LEARNER_LABEL, PARTNER_LABEL = "Learner", "Partner"
USER_ROLE = "user"
UNUSABLE_SUMMARY = "The summary came back unreadable. Please try again."


class SummaryUnavailableError(LLMError):
    """The model's summary could not be read. Shown as a plain retry message (503)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, UNUSABLE_SUMMARY)


@dataclass(frozen=True, slots=True)
class SummaryLine:
    message_id: int
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class SummaryRequest:
    conversation_id: int
    lines: tuple[SummaryLine, ...]
    languages: ConversationLanguages
    level: ConversationLevel


@dataclass(frozen=True, slots=True)
class SummaryResult:
    """A summary, or None points when there is nothing to summarise yet."""

    points: tuple[SummaryPoint, ...] | None
    up_to_message_id: int | None

    @property
    def is_too_early(self) -> bool:
        return self.points is None


class Summariser:
    def __init__(
        self,
        structured_llm: StructuredLLMProvider,
        storage: SummaryStorage,
        speaker_names: SpeakerNames | None,
    ) -> None:
        self._llm = structured_llm
        self._storage = storage
        self._speaker_names = speaker_names

    def summarise(self, request: SummaryRequest) -> SummaryResult:
        if len(request.lines) < MIN_LINES_TO_SUMMARISE:
            return SummaryResult(points=None, up_to_message_id=None)
        last_id = request.lines[-1].message_id
        cached = self._usable_cache(request)
        if cached is not None and cached.up_to_message_id == last_id:
            return SummaryResult(cached.points, last_id)
        points = self._fold(request, cached)
        level = request.level.value
        self._storage.save(StoredSummary(request.conversation_id, last_id, level, points))
        return SummaryResult(points, last_id)

    def _usable_cache(self, request: SummaryRequest) -> StoredSummary | None:
        """The stored summary, if it was written at this level over lines still present."""
        cached = self._storage.get_latest(request.conversation_id)
        known_ids = {line.message_id for line in request.lines}
        if cached is None or cached.level != request.level.value:
            return None
        return cached if cached.up_to_message_id in known_ids else None

    def _fold(
        self, request: SummaryRequest, cached: StoredSummary | None
    ) -> tuple[SummaryPoint, ...]:
        names = self._names(request.conversation_id)
        start = cached.up_to_message_id if cached is not None else None
        lines = tuple(line for line in request.lines if start is None or line.message_id > start)
        points = cached.points if cached is not None else ()
        for chunk in _chunks(lines, names):
            points = self._summarise_chunk(request, chunk, names is not None, points)
        return points

    def _summarise_chunk(
        self,
        request: SummaryRequest,
        transcript: str,
        has_names: bool,
        previous: tuple[SummaryPoint, ...],
    ) -> tuple[SummaryPoint, ...]:
        earlier = tuple(point.english for point in previous)
        prompt = build_summary_prompt(
            transcript, request.languages, request.level, has_names, earlier
        )
        reply = self._llm.chat_json([ChatMessage(role=USER_ROLE, content=prompt)], SUMMARY_SCHEMA)
        return parse_points(reply)

    def _names(self, conversation_id: int) -> Mapping[int, str] | None:
        if self._speaker_names is None:
            return None
        return self._speaker_names.names_for(conversation_id)


def label_transcript(lines: tuple[SummaryLine, ...], names: Mapping[int, str] | None) -> str:
    return "\n".join(_labelled(line, names) for line in lines)


def _labelled(line: SummaryLine, names: Mapping[int, str] | None) -> str:
    role_label = LEARNER_LABEL if line.role == USER_ROLE else PARTNER_LABEL
    label = (names or {}).get(line.message_id, role_label)
    return f"{label}: {line.content}"


def _chunks(lines: tuple[SummaryLine, ...], names: Mapping[int, str] | None) -> list[str]:
    """The labelled transcript in pieces of at most the chunk budget (a longer line stands alone)."""
    chunks: list[list[str]] = [[]]
    size = 0
    for text in (_labelled(line, names) for line in lines):
        if chunks[-1] and size + len(text) > SUMMARY_CHUNK_CHARACTERS:
            chunks.append([])
            size = 0
        chunks[-1].append(text)
        size += len(text) + 1
    return ["\n".join(chunk) for chunk in chunks if chunk]


def parse_points(reply: str) -> tuple[SummaryPoint, ...]:
    """1–5 points, each in both languages; anything else is a retryable failure."""
    try:
        raw_points = json.loads(reply)["points"]
        points = tuple(_point(raw) for raw in raw_points)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise SummaryUnavailableError(f"malformed summary reply: {exc}") from exc
    if not 1 <= len(points) <= MAX_SUMMARY_POINTS:
        raise SummaryUnavailableError(f"a summary needs 1–5 points, not {len(points)}")
    return points


def _point(raw: dict) -> SummaryPoint:
    point = SummaryPoint(str(raw["conversation_language"]).strip(), str(raw["english"]).strip())
    if not point.conversation_language or not point.english:
        raise ValueError("a point is missing one of its two versions")
    return point
