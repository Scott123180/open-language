"""One line at a time per episode (research R12).

A second Continue while a line is being produced is refused at once rather than queued, so a
double press can never produce two lines from one stale state.
"""

import threading


class HeldEpisode:
    """A held episode lock. Leaving the `with` block, even by an exception, releases it."""

    def __init__(self, lock: threading.Lock) -> None:
        self._lock = lock
        self._is_held = True

    def __enter__(self) -> "HeldEpisode":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()

    def release(self) -> None:
        """Idempotent: a second release never frees a lock someone else now holds."""
        if self._is_held:
            self._is_held = False
            self._lock.release()


class EpisodeLocks:
    def __init__(self) -> None:
        self._locks: dict[int, threading.Lock] = {}
        self._guard = threading.Lock()

    def try_acquire(self, conversation_id: int) -> HeldEpisode | None:
        """The episode's lock, now held; or None when a line is already in progress."""
        lock = self._lock_for(conversation_id)
        if not lock.acquire(blocking=False):
            return None
        return HeldEpisode(lock)

    def is_held(self, conversation_id: int) -> bool:
        return self._lock_for(conversation_id).locked()

    def _lock_for(self, conversation_id: int) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(conversation_id, threading.Lock())
