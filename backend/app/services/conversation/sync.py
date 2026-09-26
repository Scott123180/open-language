"""Whether a live session can serve the next turn, or must be rebuilt (research R-15).

Pure: no I/O and no provider imports. The saved history is the source of truth, and a session
is reused only when the turns it has taken in are a prefix of that history.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.conversation.session import USER_ROLE, SavedTurn, SessionFingerprint


@dataclass(frozen=True, slots=True)
class SessionState:
    """What the pool knows about a live session when planning a turn."""

    fingerprint: SessionFingerprint
    synced_turn_ids: tuple[str, ...]
    is_broken: bool


@dataclass(frozen=True, slots=True)
class Reuse:
    """Send only the learner turns the session hasn't seen."""

    pending: tuple[SavedTurn, ...]


@dataclass(frozen=True, slots=True)
class Rebuild:
    """Open a new session on `synced`, then send `pending`."""

    synced: tuple[SavedTurn, ...]
    pending: tuple[SavedTurn, ...]


SessionPlan = Reuse | Rebuild


def plan_session_use(
    live: SessionState | None, expected: SessionFingerprint, history: Sequence[SavedTurn]
) -> SessionPlan:
    remaining = _unsynced_turns(live, expected, history)
    if remaining is not None and all(turn.role == USER_ROLE for turn in remaining):
        return Reuse(pending=remaining)
    return _rebuild(history)


def _unsynced_turns(
    live: SessionState | None, expected: SessionFingerprint, history: Sequence[SavedTurn]
) -> tuple[SavedTurn, ...] | None:
    """The turns after the session's synced prefix, or None if the session can't be used."""
    if live is None or live.is_broken or live.fingerprint != expected:
        return None
    synced_count = len(live.synced_turn_ids)
    history_ids = tuple(turn.turn_id for turn in history[:synced_count])
    if history_ids != live.synced_turn_ids:
        return None
    return tuple(history[synced_count:])


def _rebuild(history: Sequence[SavedTurn]) -> Rebuild:
    pending_count = 0
    for turn in reversed(history):
        if turn.role != USER_ROLE:
            break
        pending_count += 1
    split = len(history) - pending_count
    return Rebuild(synced=tuple(history[:split]), pending=tuple(history[split:]))
