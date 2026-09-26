"""A SessionCapableProvider that records every open, reply, warm-up, and close.

Used by the pool, engine, and chat-session tests to count what the pool asked for.
"""

import threading
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta

from app.services.conversation import (
    ConversationSession,
    SavedTurn,
    SessionCapableProvider,
    SessionFingerprint,
    SessionKey,
)
from app.services.llm.base import LLMError
from app.services.llm.selection_types import LLMSelection

DEFAULT_TOKENS = ("Buenos", " días")


class FakeClock:
    """A settable clock for idle-expiry tests."""

    def __init__(self) -> None:
        self.now = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, minutes: float) -> None:
        self.now += timedelta(minutes=minutes)


class RecordingSession(ConversationSession):
    def __init__(self, provider: "RecordingSessionProvider", fingerprint, history) -> None:
        self._provider = provider
        self._fingerprint = fingerprint
        self.history = tuple(history)
        self.key: SessionKey | None = None
        self._synced = [turn.turn_id for turn in history]
        self.replies: list[tuple[tuple[SavedTurn, ...], str | None]] = []
        self.openings: list[str] = []
        self.acknowledged: list[str] = []
        self.warm_count = 0
        self.close_count = 0
        self._is_broken = False

    @property
    def fingerprint(self) -> SessionFingerprint:
        return self._fingerprint

    @property
    def synced_turn_ids(self) -> Sequence[str]:
        return tuple(self._synced)

    @property
    def is_broken(self) -> bool:
        return self._is_broken

    @property
    def is_closed(self) -> bool:
        return self.close_count > 0

    def warm(self) -> None:
        self.warm_count += 1

    def reply(self, pending: Sequence[SavedTurn], guidance: str | None) -> Iterator[str]:
        self.replies.append((tuple(pending), guidance))
        yield from self._generate()
        self._synced.extend(turn.turn_id for turn in pending)

    def reply_to_opening(self, instruction: str) -> Iterator[str]:
        self.openings.append(instruction)
        yield from self._generate()

    def acknowledge(self, turn_id: str) -> None:
        self.acknowledged.append(turn_id)
        self._synced.append(turn_id)

    def close(self) -> None:
        self.close_count += 1

    def _generate(self) -> Iterator[str]:
        if self.is_closed:
            raise LLMError("session closed")
        self._provider.log.append(("start", self))
        self._provider.wait_if_gated()
        if self._provider.errors:
            self._is_broken = True
            raise self._provider.errors.pop(0)
        yield from self._provider.tokens
        self._provider.log.append(("end", self))


class RecordingSessionProvider(SessionCapableProvider):
    def __init__(self, tokens: Sequence[str] = DEFAULT_TOKENS) -> None:
        self.tokens = tuple(tokens)
        self.selection = LLMSelection("fake", "fake-model")
        self.effort = ""
        self.opened: list[RecordingSession] = []
        self.errors: list[Exception] = []
        self.log: list[tuple[str, RecordingSession]] = []
        self._gate: threading.Event | None = None

    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint:
        digest = SessionFingerprint.digest_prompt(standing_prompt)
        return SessionFingerprint(self.selection, self.effort, digest)

    def open_session(
        self, key: SessionKey, standing_prompt: str, history: Sequence[SavedTurn]
    ) -> RecordingSession:
        session = RecordingSession(self, self.session_fingerprint(standing_prompt), history)
        session.key = key
        self.opened.append(session)
        return session

    def gate(self) -> threading.Event:
        """Make every generation wait until the returned event is set."""
        self._gate = threading.Event()
        return self._gate

    def wait_if_gated(self) -> None:
        if self._gate is not None:
            self._gate.wait(timeout=5)

    @property
    def reply_count(self) -> int:
        return sum(len(session.replies) for session in self.opened)
