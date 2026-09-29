"""A SessionCapableProvider that writes podcast lines from a script.

Each reply is the next scripted line (or a numbered default line when the script is empty). It
records every standing prompt and pending turns it receives, counts the sessions it opens, can
fail the next reply with an `LLMError`, and can hold every reply behind a gate.
"""

import threading
from collections.abc import Iterator, Sequence

from app.services.conversation import (
    ConversationSession,
    SavedTurn,
    SessionCapableProvider,
    SessionFingerprint,
    SessionKey,
)
from app.services.llm.base import LLMError
from app.services.llm.selection_types import LLMSelection

DEFAULT_LINE = "Línea {number} del programa."


class ScriptedLineSession(ConversationSession):
    def __init__(self, writer: "ScriptedLineWriter", standing_prompt: str, history) -> None:
        self._writer = writer
        self._standing_prompt = standing_prompt
        self._fingerprint = writer.session_fingerprint(standing_prompt)
        self.history = tuple(history)
        self._synced = [turn.turn_id for turn in history]
        self._is_broken = False
        self._is_closed = False

    @property
    def fingerprint(self) -> SessionFingerprint:
        return self._fingerprint

    @property
    def synced_turn_ids(self) -> Sequence[str]:
        return tuple(self._synced)

    @property
    def is_broken(self) -> bool:
        return self._is_broken

    def warm(self) -> None:
        self._writer.warm_count += 1

    def reply(self, pending: Sequence[SavedTurn], guidance: str | None) -> Iterator[str]:
        self._writer.received.append((self._standing_prompt, tuple(pending)))
        self._writer.guidance.append(guidance)
        line = self._next_line()
        self._synced.extend(turn.turn_id for turn in pending)
        yield line

    def reply_to_opening(self, instruction: str) -> Iterator[str]:
        raise AssertionError("Podcast lines never use an opening instruction")

    def acknowledge(self, turn_id: str) -> None:
        self._synced.append(turn_id)

    def close(self) -> None:
        self._is_closed = True

    def _next_line(self) -> str:
        if self._is_closed:
            raise LLMError("session closed")
        self._writer.wait_if_gated()
        if self._writer.errors:
            self._is_broken = True
            raise self._writer.errors.pop(0)
        return self._writer.take_line()


class ScriptedLineWriter(SessionCapableProvider):
    def __init__(self, lines: Sequence[str] = ()) -> None:
        self._lines = list(lines)
        self._written = 0
        self.selection = LLMSelection("scripted", "scripted-model")
        self.received: list[tuple[str, tuple[SavedTurn, ...]]] = []
        self.guidance: list[str | None] = []
        self.errors: list[Exception] = []
        self.sessions: list[ScriptedLineSession] = []
        self.warm_count = 0
        self._gate: threading.Event | None = None

    @property
    def open_count(self) -> int:
        return len(self.sessions)

    def script(self, *lines: str) -> None:
        self._lines.extend(lines)

    def fail_next(self, error: Exception) -> None:
        self.errors.append(error)

    def take_line(self) -> str:
        self._written += 1
        if self._lines:
            return self._lines.pop(0)
        return DEFAULT_LINE.format(number=self._written)

    def gate(self) -> threading.Event:
        """Hold every reply until the returned event is set."""
        self._gate = threading.Event()
        return self._gate

    def wait_if_gated(self) -> None:
        if self._gate is not None:
            self._gate.wait(timeout=5)

    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint:
        digest = SessionFingerprint.digest_prompt(standing_prompt)
        return SessionFingerprint(self.selection, "", digest)

    def open_session(
        self, key: SessionKey, standing_prompt: str, history: Sequence[SavedTurn]
    ) -> ScriptedLineSession:
        session = ScriptedLineSession(self, standing_prompt, history)
        self.sessions.append(session)
        return session
