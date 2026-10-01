"""The vocabulary of conversation sessions: what a router asks for, and what a provider keeps.

The saved history is always the source of truth. A session is a provider's live hold on
one conversation, reused only while it lines up with that history (research R-15).
"""

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.services.llm.selection_types import LLMSelection

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
_TURN_ROLES = frozenset({USER_ROLE, ASSISTANT_ROLE})


class SessionKind(StrEnum):
    ROLEPLAY = "roleplay"
    HELPER = "helper"
    PODCAST = "podcast"


@dataclass(frozen=True, slots=True)
class SessionKey:
    """Identifies one conversation's session: a roleplay conversation or a helper thread."""

    kind: SessionKind
    identifier: str


@dataclass(frozen=True, slots=True)
class SavedTurn:
    """One message of saved history, with the id that ties it to storage."""

    turn_id: str
    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in _TURN_ROLES:
            raise ValueError(f"A saved turn is 'user' or 'assistant', not {self.role!r}")


@dataclass(frozen=True, slots=True)
class SessionFingerprint:
    """What a session was built for. Any difference forces a rebuild (FR-S04)."""

    selection: LLMSelection
    effort: str
    standing_prompt_digest: str

    @staticmethod
    def digest_prompt(standing_prompt: str) -> str:
        return hashlib.sha256(standing_prompt.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TurnRequest:
    """Everything the engine needs to produce the next reply of one conversation."""

    key: SessionKey
    standing_prompt: str
    history: tuple[SavedTurn, ...]
    guidance: str | None
    opening_instruction: str | None

    def __post_init__(self) -> None:
        if self.opening_instruction is not None:
            self._require_no_learner_turns()
        elif not self.history or self.history[-1].role != USER_ROLE:
            raise ValueError("A turn request must end with the learner's message")

    def _require_no_learner_turns(self) -> None:
        if any(turn.role == USER_ROLE for turn in self.history):
            raise ValueError("An opening turn cannot follow learner messages")


class ConversationSession(ABC):
    """A provider's live hold on one conversation. The saved history is the source of truth."""

    @property
    @abstractmethod
    def fingerprint(self) -> SessionFingerprint: ...

    @property
    @abstractmethod
    def synced_turn_ids(self) -> Sequence[str]:
        """Saved turns already in the provider's context, in order."""

    @property
    @abstractmethod
    def is_broken(self) -> bool:
        """True once a turn failed part-way. A broken session is never reused."""

    @abstractmethod
    def warm(self) -> None:
        """Get ready for the first turn without producing a reply or using plan quota."""

    @abstractmethod
    def reply(self, pending: Sequence[SavedTurn], guidance: str | None) -> Iterator[str]:
        """Yield the reply to the pending learner turns. Raises LLMError on failure."""

    @abstractmethod
    def reply_to_opening(self, instruction: str) -> Iterator[str]:
        """Yield the character's opening line. The instruction is never recorded as a turn."""

    @abstractmethod
    def acknowledge(self, turn_id: str) -> None:
        """Record the saved id of the reply just produced."""

    @abstractmethod
    def close(self) -> None:
        """Release whatever the session holds. Idempotent."""


class SessionCapableProvider(ABC):
    """A provider that can hold a conversation open between turns (ISP: separate from chat)."""

    @abstractmethod
    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint: ...

    @abstractmethod
    def open_session(
        self, key: SessionKey, standing_prompt: str, history: Sequence[SavedTurn]
    ) -> ConversationSession:
        """Open a session holding `history`. `key` names the conversation, e.g. for its logs."""
