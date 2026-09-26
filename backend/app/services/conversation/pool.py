"""A bounded, expiring set of live conversation sessions (research R-16).

One per process. Each key has its own lock, held for the whole turn, so two turns of one
conversation never interleave while different conversations run side by side (FR-S10).
"""

import logging
import threading
from collections import OrderedDict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.conversation.session import (
    ConversationSession,
    SavedTurn,
    SessionCapableProvider,
    SessionKey,
    TurnRequest,
)
from app.services.conversation.sync import Rebuild, Reuse, SessionState, plan_session_use
from app.services.llm.base import LLMError

logger = logging.getLogger(__name__)

_GENERATIONS_PER_REBUILD = 1


@dataclass
class _Entry:
    session: ConversationSession
    last_used_at: datetime
    is_awaiting_acknowledgement: bool = False

    def state(self) -> SessionState:
        # A reply that was never acknowledged may be in the provider's context but not in
        # storage, so the session no longer lines up with the saved history.
        return SessionState(
            fingerprint=self.session.fingerprint,
            synced_turn_ids=tuple(self.session.synced_turn_ids),
            is_broken=self.session.is_broken or self.is_awaiting_acknowledgement,
        )


class ConversationSessionPool:
    def __init__(self, max_live: int, idle_ttl: timedelta, clock: Callable[[], datetime]) -> None:
        if max_live < 1:
            raise ValueError("max_live must be at least 1")
        self._max_live = max_live
        self._idle_ttl = idle_ttl
        self._clock = clock
        self._entries: OrderedDict[SessionKey, _Entry] = OrderedDict()
        self._key_locks: dict[SessionKey, threading.Lock] = {}
        self._pool_lock = threading.Lock()

    # --- public interface -------------------------------------------------------------

    def run_turn(self, provider: SessionCapableProvider, request: TurnRequest) -> Iterator[str]:
        """Yield the reply to `request`, reusing or rebuilding the key's session."""
        with self._key_lock(request.key):
            tokens = self._reply_with_one_retry(provider, request)
            try:
                yield from tokens
            except GeneratorExit:
                # An abandoned reply is never stored, so the session no longer matches storage.
                self.end(request.key)
                raise

    def warm(
        self,
        provider: SessionCapableProvider,
        key: SessionKey,
        standing_prompt: str,
        history: Sequence[SavedTurn],
    ) -> None:
        """Open the key's session on `history` and warm it, unless it is already live."""
        with self._key_lock(key):
            entry = self._touch(key)
            expected = provider.session_fingerprint(standing_prompt)
            if entry and plan_session_use(entry.state(), expected, history) == Reuse(()):
                return
            session = self._replace(key, provider.open_session(key, standing_prompt, history))
            self._warm_or_discard(key, session)

    def acknowledge(self, key: SessionKey, turn_id: str) -> None:
        """Tell the key's session the saved id of the reply it just produced."""
        with self._pool_lock:
            entry = self._entries.get(key)
            if entry is None:
                return
            entry.session.acknowledge(turn_id)
            entry.is_awaiting_acknowledgement = False

    def is_live(self, key: SessionKey) -> bool:
        """A pure query: does not refresh the idle clock."""
        with self._pool_lock:
            entry = self._entries.get(key)
            return entry is not None and not self._is_expired(entry)

    def end(self, key: SessionKey) -> None:
        with self._pool_lock:
            entry = self._entries.pop(key, None)
        if entry is not None:
            entry.session.close()

    def evict_idle(self) -> None:
        """Close every session idle past the TTL, skipping any whose turn is running."""
        with self._pool_lock:
            expired = self._pop_expired()
        _close_all(expired)

    def close_all(self) -> None:
        with self._pool_lock:
            closing = [entry.session for entry in self._entries.values()]
            self._entries.clear()
        _close_all(closing)

    # --- one turn -----------------------------------------------------------------------

    def _reply_with_one_retry(
        self, provider: SessionCapableProvider, request: TurnRequest
    ) -> list[str]:
        try:
            return self._complete_reply(provider, request)
        except LLMError as exc:
            if not exc.can_retry:
                raise
            logger.info("Retrying %s on a rebuilt session after: %s", _label(request.key), exc)
            return self._complete_reply(provider, request)

    def _complete_reply(self, provider: SessionCapableProvider, request: TurnRequest) -> list[str]:
        """One attempt, collected in full. Delivery is batched anyway (spec Assumptions), and a
        retry then replaces a partial reply instead of splicing onto it (FR-S11)."""
        session, pending = self._session_for(provider, request)
        is_complete = False
        try:
            tokens = list(_reply(session, request, pending))
            is_complete = True
        finally:
            self._finish_turn(request.key, session, is_complete)
        return tokens

    def _session_for(
        self, provider: SessionCapableProvider, request: TurnRequest
    ) -> tuple[ConversationSession, tuple[SavedTurn, ...]]:
        entry = self._touch(request.key)
        expected = provider.session_fingerprint(request.standing_prompt)
        plan = plan_session_use(entry.state() if entry else None, expected, request.history)
        if isinstance(plan, Reuse) and entry is not None:
            return entry.session, plan.pending
        return self._rebuild(provider, request, plan), plan.pending

    def _rebuild(
        self, provider: SessionCapableProvider, request: TurnRequest, plan: Rebuild
    ) -> ConversationSession:
        session = provider.open_session(request.key, request.standing_prompt, plan.synced)
        logger.info(
            "session rebuilt key=%s turns=%d generations=%d",
            _label(request.key),
            len(request.history),
            _GENERATIONS_PER_REBUILD,
        )
        return self._replace(request.key, session)

    def _finish_turn(
        self, key: SessionKey, session: ConversationSession, is_complete: bool
    ) -> None:
        """Keep a session whose reply finished; discard one that failed or was abandoned."""
        with self._pool_lock:
            entry = self._entries.get(key)
            is_current = entry is not None and entry.session is session
            if is_current and is_complete:
                entry.is_awaiting_acknowledgement = True
                entry.last_used_at = self._clock()
                return
            if is_current:
                del self._entries[key]
        session.close()

    # --- bookkeeping --------------------------------------------------------------------

    def _key_lock(self, key: SessionKey) -> threading.Lock:
        with self._pool_lock:
            return self._key_locks.setdefault(key, threading.Lock())

    def _touch(self, key: SessionKey) -> _Entry | None:
        """Return the key's live entry, marking it most recently used. Sweeps expired ones."""
        with self._pool_lock:
            expired = self._pop_expired(including=key)
            entry = self._entries.get(key)
            if entry is not None:
                entry.last_used_at = self._clock()
                self._entries.move_to_end(key)
        _close_all(expired)
        return entry

    def _replace(self, key: SessionKey, session: ConversationSession) -> ConversationSession:
        """Make `session` the key's live session, closing its predecessor and any LRU overflow."""
        with self._pool_lock:
            previous = self._entries.pop(key, None)
            self._entries[key] = _Entry(session=session, last_used_at=self._clock())
            closing = self._pop_overflow()
        if previous is not None:
            closing.append(previous.session)
        _close_all(closing)
        return session

    def _warm_or_discard(self, key: SessionKey, session: ConversationSession) -> None:
        try:
            session.warm()
        except LLMError:
            self._finish_turn(key, session, is_complete=False)
            raise

    def _pop_expired(self, including: SessionKey | None = None) -> list[ConversationSession]:
        """Remove expired entries. Caller holds the pool lock.

        Keys whose turn is running are skipped, except `including`, whose lock the caller holds.
        """
        expired = [
            key
            for key, entry in self._entries.items()
            if self._is_expired(entry) and (key == including or not self._is_running(key))
        ]
        return [self._entries.pop(key).session for key in expired]

    def _pop_overflow(self) -> list[ConversationSession]:
        """Remove least-recently-used idle entries beyond the bound. Caller holds the pool lock."""
        idle_keys = [key for key in self._entries if not self._is_running(key)]
        overflow = max(0, len(self._entries) - self._max_live)
        return [self._entries.pop(key).session for key in idle_keys[:overflow]]

    def _is_running(self, key: SessionKey) -> bool:
        lock = self._key_locks.get(key)
        return lock is not None and lock.locked()

    def _is_expired(self, entry: _Entry) -> bool:
        return entry.last_used_at <= self._clock() - self._idle_ttl


def _reply(
    session: ConversationSession, request: TurnRequest, pending: tuple[SavedTurn, ...]
) -> Iterator[str]:
    if request.opening_instruction is not None:
        return session.reply_to_opening(request.opening_instruction)
    return session.reply(pending, request.guidance)


def _close_all(sessions: list[ConversationSession]) -> None:
    for session in sessions:
        session.close()


def _label(key: SessionKey) -> str:
    return f"{key.kind.value}:{key.identifier}"
