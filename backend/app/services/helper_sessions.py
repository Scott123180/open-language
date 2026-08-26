"""In-memory store for expression-helper conversation threads.

Helper threads are throwaway reference lookups ("how do I say X?"), deliberately
kept separate from the role-play conversation so they never pollute its context.
They are not durable learning history, so they are not persisted — but a
long-running process must not accumulate them without limit, hence the
least-recently-used bound and the idle expiry.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

DEFAULT_MAX_SESSIONS = 50
DEFAULT_TTL = timedelta(hours=2)

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"


@dataclass(frozen=True, slots=True)
class HelperTurn:
    """One turn in a helper thread."""

    role: str
    content: str


@dataclass
class _HelperThread:
    turns: list[HelperTurn] = field(default_factory=list)
    last_used_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class HelperSessionStore:
    """Bounded, expiring map of helper session id to its conversation turns."""

    def __init__(
        self,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        ttl: timedelta = DEFAULT_TTL,
    ) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be at least 1")
        self._max_sessions = max_sessions
        self._ttl = ttl
        self._threads: OrderedDict[str, _HelperThread] = OrderedDict()

    def get_history(self, session_id: str) -> list[HelperTurn]:
        """Return a copy of the thread's turns, or an empty list if absent or expired."""
        thread = self._touch(session_id)
        return list(thread.turns) if thread else []

    def append_exchange(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Append one question-and-answer pair to the thread, creating it if needed."""
        thread = self._touch(session_id) or self._create(session_id)
        thread.turns.append(HelperTurn(role=USER_ROLE, content=user_message))
        thread.turns.append(HelperTurn(role=ASSISTANT_ROLE, content=assistant_message))

    def clear(self) -> None:
        """Drop every thread."""
        self._threads.clear()

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._threads)

    def _touch(self, session_id: str) -> _HelperThread | None:
        """Return the live thread for this id, marking it most-recently-used."""
        self._evict_expired()
        thread = self._threads.get(session_id)
        if thread is None:
            return None
        thread.last_used_at = datetime.now(UTC)
        self._threads.move_to_end(session_id)
        return thread

    def _create(self, session_id: str) -> _HelperThread:
        thread = _HelperThread()
        self._threads[session_id] = thread
        while len(self._threads) > self._max_sessions:
            self._threads.popitem(last=False)
        return thread

    def _evict_expired(self) -> None:
        cutoff = datetime.now(UTC) - self._ttl
        expired = [sid for sid, t in self._threads.items() if t.last_used_at <= cutoff]
        for session_id in expired:
            del self._threads[session_id]
