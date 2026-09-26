"""CorrectionStorageProvider ABC and its transport value objects.

Its own abstraction rather than four more methods on the core StorageProvider,
so existing consumers are not made to depend on correction persistence (ISP).
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeedbackDraft:
    """A note a strategy decided on, before it is persisted."""

    kind: str
    category: str | None
    error_fragment: str | None
    corrected_text: str | None
    explanation: str
    mode: str
    rank: int = 0


@dataclass(frozen=True)
class FeedbackRecord:
    """A persisted note, as the API and the client see it."""

    id: int
    message_id: int
    kind: str
    category: str | None
    error_fragment: str | None
    corrected_text: str | None
    explanation: str
    mode: str
    rank: int
    created_at: datetime


@dataclass(frozen=True)
class PauseSnapshot:
    """The Strict pause for one conversation. ``awaiting_retry`` is derived."""

    consecutive_corrected_attempts: int
    awaiting_clarification: bool
    awaiting_retry: bool


class CorrectionStorageProvider(ABC):
    @abstractmethod
    def save_feedback(
        self, message_id: int, drafts: Sequence[FeedbackDraft]
    ) -> list[FeedbackRecord]:
        """Insert notes against a learner message. Insert-only; never updates."""
        ...

    @abstractmethod
    def list_feedback(self, conversation_id: int) -> list[FeedbackRecord]:
        """Return every note in the conversation, ordered by (message_id, rank)."""
        ...

    @abstractmethod
    def get_pause_state(self, conversation_id: int) -> PauseSnapshot:
        """Return the pause snapshot, zeroed when no row exists. Creates nothing."""
        ...

    @abstractmethod
    def set_pause_state(
        self, conversation_id: int, attempts: int, awaiting_clarification: bool
    ) -> PauseSnapshot:
        """Persist the pause counters, creating the row on first use."""
        ...
