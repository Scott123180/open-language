"""SummaryStorage: the latest summary of a conversation, and the lines and level it covers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SummaryPoint:
    """One point of a summary, in the conversation's language and in English (FR-038)."""

    conversation_language: str
    english: str


@dataclass(frozen=True, slots=True)
class StoredSummary:
    conversation_id: int
    up_to_message_id: int
    level: str
    points: tuple[SummaryPoint, ...]


class SummaryStorage(ABC):
    @abstractmethod
    def get_latest(self, conversation_id: int) -> StoredSummary | None: ...

    @abstractmethod
    def save(self, summary: StoredSummary) -> None:
        """Replace the conversation's summary with this one."""
