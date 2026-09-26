"""ClaudeCodeSession: one long-lived `claude` process per conversation (research R-14).

Each turn writes one user line to stdin and reads until that turn's result, so earlier turns are
never re-processed. A rebuilt session costs exactly one reply: history with learner turns travels
as one transcript line, and history without them is seeded natively as assistant lines.
"""

import json
import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from app.services.conversation.session import (
    USER_ROLE,
    ConversationSession,
    SavedTurn,
    SessionFingerprint,
    SessionKey,
)
from app.services.llm.availability import ProviderAvailabilityChecker
from app.services.llm.base import LLMError
from app.services.llm.claude_code.events import iter_text_deltas
from app.services.llm.claude_code.failures import ClaudeCodeFailure, failure_for_availability
from app.services.llm.claude_code.runner import ClaudeCodeRunner, InteractiveProcess
from app.services.llm.claude_code.transcript import render_rebuild_turn, with_guidance

TURN_GUIDANCE_PARAGRAPH = (
    "Some messages end with a <turn_guidance> block. Follow it for that one reply only, "
    "and never mention it, quote it, or refer to it."
)
_ASSISTANT_ROLE = "assistant"
_PENDING_SEPARATOR = "\n"
_CLOSED_DETAIL = "This Claude session was closed"
_UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^A-Za-z0-9_-]")

_Result = TypeVar("_Result")


def session_log_path(log_dir: Path, key: SessionKey) -> Path:
    # Helper ids come from the client, so they never reach the filesystem unfiltered.
    identifier = _UNSAFE_FILENAME_CHARACTERS.sub("_", key.identifier)
    return log_dir / f"session-{key.kind.value}-{identifier}.log"


@dataclass(frozen=True)
class ClaudeSessionConfig:
    runner: ClaudeCodeRunner
    availability: ProviderAvailabilityChecker
    argv: tuple[str, ...]
    log_path: Path
    turn_timeout_seconds: float
    fingerprint: SessionFingerprint


class ClaudeCodeSession(ConversationSession):
    def __init__(self, config: ClaudeSessionConfig, history: Sequence[SavedTurn]) -> None:
        self._config = config
        self._history = tuple(history)
        self._synced = [turn.turn_id for turn in history]
        self._has_learner_history = any(turn.role == USER_ROLE for turn in history)
        self._process: InteractiveProcess | None = None
        self._has_sent_a_turn = False
        self._is_broken = False
        self._is_closed = False

    @property
    def fingerprint(self) -> SessionFingerprint:
        return self._config.fingerprint

    @property
    def synced_turn_ids(self) -> Sequence[str]:
        return tuple(self._synced)

    @property
    def is_broken(self) -> bool:
        return self._is_broken

    def warm(self) -> None:
        """Spawn the process, which then waits on stdin: no model call, no plan usage."""
        self._require_open()
        self._guarded(self._ensure_process)

    def reply(self, pending: Sequence[SavedTurn], guidance: str | None) -> Iterator[str]:
        yield from self._turn(self._content_for(pending, guidance))
        self._synced.extend(turn.turn_id for turn in pending)

    def reply_to_opening(self, instruction: str) -> Iterator[str]:
        yield from self._turn(instruction)

    def acknowledge(self, turn_id: str) -> None:
        self._synced.append(turn_id)

    def close(self) -> None:
        self._is_closed = True
        if self._process is not None:
            self._process.close()

    def _content_for(self, pending: Sequence[SavedTurn], guidance: str | None) -> str:
        if not self._has_sent_a_turn and self._has_learner_history:
            return render_rebuild_turn(self._history, pending, guidance)
        merged = _PENDING_SEPARATOR.join(turn.content for turn in pending)
        return with_guidance(merged, guidance)

    def _turn(self, content: str) -> Iterator[str]:
        self._require_open()
        process = self._guarded(self._ensure_process)
        try:
            self._send_first_turn_seed(process)
            process.send_line(_line(USER_ROLE, content))
            lines = process.read_lines_until_result(self._config.turn_timeout_seconds)
            yield from iter_text_deltas(lines)
        except ClaudeCodeFailure:
            self._is_broken = True
            raise
        self._has_sent_a_turn = True

    def _send_first_turn_seed(self, process: InteractiveProcess) -> None:
        """Seed assistant-only history as native context: it triggers no generation."""
        if self._has_sent_a_turn or self._has_learner_history:
            return
        for turn in self._history:
            process.send_line(_line(_ASSISTANT_ROLE, turn.content))

    def _ensure_process(self) -> InteractiveProcess:
        if self._process is None:
            availability = self._config.availability.check()
            if not availability.is_available:
                raise failure_for_availability(availability.reason)
            self._process = self._config.runner.spawn_interactive(
                self._config.argv, self._config.log_path
            )
        return self._process

    def _guarded(self, action: Callable[[], _Result]) -> _Result:
        """Run `action`, marking the session broken if Claude Code fails."""
        try:
            return action()
        except ClaudeCodeFailure:
            self._is_broken = True
            raise

    def _require_open(self) -> None:
        if self._is_closed:
            raise LLMError(_CLOSED_DETAIL)


def _line(role: str, content: str) -> str:
    return json.dumps({"type": role, "message": {"role": role, "content": content}})
