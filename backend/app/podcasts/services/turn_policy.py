"""TurnPolicy: whose turn it is, and who speaks the next host line and why (research R2).

Pure: it reads stored facts and draws from an injected `random.Random`. The model is only ever
asked for the line the policy chose, so FR-013–FR-019 hold by construction (data-model §5).
Rules apply in priority order: run cap > addressed host > balance > hand-over > intent > random.
"""

import random
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from app.podcasts.catalog import LEAD_SLOT, SECOND_SLOT, EpisodeLength, PodcastFormat
from app.podcasts.services.casting import Cast

LEARNER = "learner"
OPEN, GREET, DISCUSS, WRAP_UP, SIGN_OFF = "open", "greet", "discuss", "wrap_up", "sign_off"
HOSTS_TURN, LEARNER_TURN, FINISHED = "hosts", "learner", "finished"
AWAITING_OPENING, AWAITING_REPLY, AWAITING_CONTINUE = "opening", "reply", "continue"

OTHER_HOST_ANSWERS = 0.7
"""After a host line, the other host answers with this probability (FR-013)."""
INVITER_ANSWERS = 0.6
"""After the learner speaks, the host who invited them answers with this probability."""
INVITATION_HAZARDS = (0.25, 0.45, 0.6)
"""Panel: the chance the 1st, 2nd and 3rd host line since the learner spoke invites them."""
BALANCING_GAP = 2
"""When one host is this many lines ahead, the other speaks next (FR-015)."""
_PREFERRED_SLOT = {OPEN: LEAD_SLOT, SIGN_OFF: LEAD_SLOT, GREET: SECOND_SLOT}


@dataclass(frozen=True, slots=True)
class LineFacts:
    """One stored line, as the policy sees it. `speaker` is a host slot or LEARNER."""

    speaker: str
    intent: str | None
    invites_learner: bool = False
    is_passed: bool = False
    text: str = ""
    message_id: int | None = None

    @property
    def is_host(self) -> bool:
        return self.speaker != LEARNER


@dataclass(frozen=True, slots=True)
class LineCue:
    speaker_slot: str
    intent: str
    invites_learner: bool
    is_after_pass: bool
    is_settle_invite: bool


@dataclass(frozen=True, slots=True)
class EpisodeState:
    format: PodcastFormat
    length: EpisodeLength
    cast: Cast
    lines: tuple[LineFacts, ...]
    is_finished: bool
    is_awaiting_retry: bool = False
    """A Strict correction paused the learner's message; the learner must try again."""

    @property
    def host_lines(self) -> tuple[LineFacts, ...]:
        return tuple(line for line in self.lines if line.is_host)

    @property
    def last(self) -> LineFacts | None:
        return self.lines[-1] if self.lines else None


@dataclass(frozen=True, slots=True)
class Turn:
    turn: str
    awaiting: str | None


class TurnPolicy:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def turn(self, state: EpisodeState) -> Turn:
        last = state.last
        if state.is_finished:
            return Turn(FINISHED, None)
        if last is None:
            return Turn(HOSTS_TURN, AWAITING_OPENING)
        if not last.is_host:
            return Turn(LEARNER_TURN, None) if state.is_awaiting_retry else _reply()
        if last.invites_learner and not last.is_passed:
            return Turn(LEARNER_TURN, None)
        return Turn(HOSTS_TURN, AWAITING_CONTINUE)

    def next_cue(self, state: EpisodeState) -> LineCue:
        """The next host line in the natural course of the episode."""
        return self._cue(state, _intent(state))

    def end_cue(self, state: EpisodeState) -> LineCue:
        """The sign-off the learner asked for with End episode (FR-019)."""
        return self._cue(state, SIGN_OFF)

    def _cue(self, state: EpisodeState, intent: str) -> LineCue:
        speaker = self._speaker(state, intent)
        invites = self._invites(state, intent, speaker)
        return LineCue(
            speaker_slot=speaker,
            intent=intent,
            invites_learner=invites,
            is_after_pass=follows_pass(state.lines),
            is_settle_invite=invites and is_settle_moment(state.lines),
        )

    def _speaker(self, state: EpisodeState, intent: str) -> str:
        if state.cast.second is None:
            return LEAD_SLOT
        candidates = _not_excluded_by_run(state)
        for rule in (_addressed_host, _balancing_host, _handed_over_host):
            chosen = rule(state)
            if chosen in candidates:
                return chosen
        preferred = _PREFERRED_SLOT.get(intent)
        if preferred in candidates:
            return preferred
        return self._random_host(state, candidates)

    def _random_host(self, state: EpisodeState, candidates: set[str]) -> str:
        if len(candidates) == 1:
            return next(iter(candidates))
        favoured, probability = _favoured_host(state)
        if self._rng.random() < probability:
            return favoured
        return _other(favoured)

    def _invites(self, state: EpisodeState, intent: str, speaker: str) -> bool:
        if not state.format.is_learner_speaking or intent == SIGN_OFF:
            return False
        if state.format.host_count == 1 or intent == WRAP_UP:
            return True
        run = _run_since_learner(state.lines) + 1
        if run >= state.format.invite_deadline:
            return True
        if _gap_after(state, speaker) >= BALANCING_GAP:
            return False
        return self._rng.random() < INVITATION_HAZARDS[min(run, len(INVITATION_HAZARDS)) - 1]


def is_settle_moment(previous: Sequence[LineFacts]) -> bool:
    """The two lines before an invitation came from two different hosts (US3)."""
    if len(previous) < 2:
        return False
    before, last = previous[-2], previous[-1]
    return before.is_host and last.is_host and before.speaker != last.speaker


def follows_pass(previous: Sequence[LineFacts]) -> bool:
    return bool(previous) and previous[-1].is_host and previous[-1].is_passed


def _reply() -> Turn:
    return Turn(HOSTS_TURN, AWAITING_REPLY)


def _intent(state: EpisodeState) -> str:
    host_lines = state.host_lines
    if not host_lines:
        return OPEN
    if state.format.host_count == 2 and len(host_lines) == 1 and len(state.lines) == 1:
        return GREET
    has_wrapped_up = any(line.intent == WRAP_UP for line in host_lines)
    if not has_wrapped_up and len(host_lines) + 1 >= state.length.target_host_lines:
        return WRAP_UP
    if not state.format.is_learner_speaking and state.last.intent == WRAP_UP:
        return SIGN_OFF
    return DISCUSS


def _other(slot: str) -> str:
    return SECOND_SLOT if slot == LEAD_SLOT else LEAD_SLOT


def _not_excluded_by_run(state: EpisodeState) -> set[str]:
    """Every host, less one who has already spoken `max_host_run` lines in a row."""
    run_speaker, run = _current_run(state.lines)
    hosts = {host.slot for host in state.cast.hosts}
    if run_speaker is not None and run >= state.format.max_host_run:
        return hosts - {run_speaker}
    return hosts


def _current_run(lines: Sequence[LineFacts]) -> tuple[str | None, int]:
    if not lines or not lines[-1].is_host:
        return None, 0
    speaker, run = lines[-1].speaker, 0
    for line in reversed(lines):
        if line.speaker != speaker:
            break
        run += 1
    return speaker, run


def _addressed_host(state: EpisodeState) -> str | None:
    """FR-018: the host the learner's last line names first, when that line is the last."""
    last = state.last
    if last is None or last.is_host:
        return None
    return _first_named(last.text, state.cast)


def _balancing_host(state: EpisodeState) -> str | None:
    counts = _line_counts(state)
    if abs(counts[LEAD_SLOT] - counts[SECOND_SLOT]) < BALANCING_GAP:
        return None
    return min(counts, key=counts.get)


def _handed_over_host(state: EpisodeState) -> str | None:
    """A host line that names the other host hands the conversation to them."""
    last = state.last
    if last is None or not last.is_host:
        return None
    named = _first_named(last.text, state.cast)
    return named if named != last.speaker else None


def _favoured_host(state: EpisodeState) -> tuple[str, float]:
    """After the learner: the host who invited them. After a host: the other host."""
    last_host = next(line for line in reversed(state.lines) if line.is_host)
    if not state.last.is_host:
        return last_host.speaker, INVITER_ANSWERS
    return _other(last_host.speaker), OTHER_HOST_ANSWERS


def _line_counts(state: EpisodeState) -> dict[str, int]:
    counts = {LEAD_SLOT: 0, SECOND_SLOT: 0}
    for line in state.host_lines:
        counts[line.speaker] += 1
    return counts


def _gap_after(state: EpisodeState, speaker: str) -> int:
    counts = _line_counts(state)
    counts[speaker] += 1
    return abs(counts[LEAD_SLOT] - counts[SECOND_SLOT])


def _run_since_learner(lines: Sequence[LineFacts]) -> int:
    """Host lines since the learner last spoke or passed (plan interpretation 3)."""
    run = 0
    for line in reversed(lines):
        if not line.is_host or line.is_passed:
            break
        run += 1
    return run


def _first_named(text: str, cast: Cast) -> str | None:
    folded = _fold(text)
    positions = {
        host.slot: match.start()
        for host in cast.hosts
        if (match := re.search(rf"\b{re.escape(_fold(host.name))}\b", folded))
    }
    return min(positions, key=positions.get) if positions else None


def _fold(text: str) -> str:
    """Case- and accent-insensitive form, so "lucia" names Lucía."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
