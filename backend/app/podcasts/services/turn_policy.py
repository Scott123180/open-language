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
from enum import StrEnum
from typing import TYPE_CHECKING

from app.podcasts.catalog import (
    LEAD_SLOT,
    QUESTION_MARK,
    SECOND_SLOT,
    EpisodeLength,
    PodcastFormat,
)
from app.podcasts.services.casting import Cast

if TYPE_CHECKING:
    from app.podcasts.services.host_talk import HostTalk

LEARNER = "learner"
OPEN, GREET, DISCUSS, WRAP_UP, SIGN_OFF = "open", "greet", "discuss", "wrap_up", "sign_off"
ANSWER, FOLLOW_UP = "answer", "follow_up"
HOSTS_TURN, LEARNER_TURN, FINISHED = "hosts", "learner", "finished"
AWAITING_OPENING, AWAITING_REPLY, AWAITING_CONTINUE = "opening", "reply", "continue"

OTHER_HOST_ANSWERS = 0.7
"""After a host line, the other host answers with this probability (FR-013)."""
INVITER_ANSWERS = 0.6
"""After the learner speaks, the host who invited them answers with this probability."""
BALANCING_GAP = 2
"""When one host is this many lines ahead, the other speaks next (FR-015)."""
_CLOSERS = " \t\n\"'»”’)]"
_PREFERRED_SLOT = {OPEN: LEAD_SLOT, SIGN_OFF: LEAD_SLOT, GREET: SECOND_SLOT}


class Ask(StrEnum):
    """How a cue asks for an invitation (011 research R19)."""

    REQUIRED = "required"
    """The line must hand the learner the turn."""
    ALLOWED = "allowed"
    """The line may end with a question to the learner, if it fits."""
    NONE = "none"
    """The line must not ask the learner anything; if it does, they still get the turn."""
    NEVER = "never"
    """The line must not ask the learner anything, and never hands them the turn: a
    two-host opening or greeting, which the other host's line must follow (R19)."""

    @property
    def may_invite(self) -> bool:
        return self in (Ask.REQUIRED, Ask.ALLOWED)


@dataclass(frozen=True, slots=True)
class LineFacts:
    """One stored line, as the policy sees it. `speaker` is a host slot or LEARNER."""

    speaker: str
    intent: str | None
    invites_learner: bool = False
    is_passed: bool = False
    text: str = ""
    message_id: int | None = None
    ask: Ask | None = None
    """The cue's ask. A line stored before 011 has none: it is read from `invites_learner`."""
    addressee: str | None = None
    """Who the line was for: learner, lead or second. None means no one in particular."""

    def __post_init__(self) -> None:
        if self.ask is None:
            object.__setattr__(self, "ask", stored_ask(None, self.invites_learner))

    @property
    def is_host(self) -> bool:
        return self.speaker != LEARNER


@dataclass(frozen=True, slots=True)
class LineCue:
    speaker_slot: str
    intent: str
    ask: Ask
    is_after_pass: bool
    is_settle_invite: bool
    asker: str | None = None
    """011: whose question an `answer` or `follow_up` replies to: LEARNER or a host slot."""
    is_for_both: bool = False
    """011: the learner's question named neither host or both, so the answer passes it on."""


@dataclass(frozen=True, slots=True)
class InvitePoint:
    """Where a host line falls, as its talk needs it to decide the line's `Ask`."""

    run: int
    """The line's position among the host lines since the learner last spoke or passed."""
    format: PodcastFormat
    intent: str
    is_unbalancing: bool = False
    """Inviting now would leave one host two lines ahead of the other (FR-015)."""


@dataclass(frozen=True, slots=True)
class EpisodeState:
    format: PodcastFormat
    length: EpisodeLength
    cast: Cast
    lines: tuple[LineFacts, ...]
    is_finished: bool
    talk: "HostTalk"
    """How this episode's hosts talk: the invitations and the kind of each line (011 R1)."""
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
        return self._cue(state, self._intent(state))

    def end_cue(self, state: EpisodeState) -> LineCue:
        """The sign-off the learner asked for with End episode (FR-019)."""
        return self._cue(state, SIGN_OFF)

    def _intent(self, state: EpisodeState) -> str:
        """The opening, greeting and wrap-up by position; every other line from the talk. An
        answer owed to the learner comes before the wrap-up (011 FR-005)."""
        host_lines = state.host_lines
        if not host_lines:
            return OPEN
        if state.format.host_count == 2 and len(host_lines) == 1 and len(state.lines) == 1:
            return GREET
        if not state.format.is_learner_speaking and state.last.intent == WRAP_UP:
            return SIGN_OFF
        intent = state.talk.discussion_intent(state, self._rng)
        asker, _is_for_both = answer_context(state.lines, state.cast, intent)
        if _is_wrap_up_due(state) and asker != LEARNER:
            return WRAP_UP
        return intent

    def _cue(self, state: EpisodeState, intent: str) -> LineCue:
        speaker = self._speaker(state, intent)
        ask = self._ask(state, intent, speaker)
        asker, is_for_both = answer_context(state.lines, state.cast, intent)
        return LineCue(
            speaker_slot=speaker,
            intent=intent,
            ask=ask,
            is_after_pass=follows_pass(state.lines),
            is_settle_invite=ask.may_invite and is_settle_moment(state.lines),
            asker=asker,
            is_for_both=is_for_both,
        )

    def _speaker(self, state: EpisodeState, intent: str) -> str:
        if state.cast.second is None:
            return LEAD_SLOT
        candidates = _not_excluded_by_run(state)
        for rule in (_addressed_host, _addressee_of_last_line, _balancing_host, _handed_over_host):
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

    def _ask(self, state: EpisodeState, intent: str, speaker: str) -> Ask:
        """Wrap-up and sign-off keep their rules; the talk decides every other line."""
        if not state.format.is_learner_speaking or intent == SIGN_OFF:
            return Ask.NONE
        if intent == WRAP_UP:
            return Ask.REQUIRED
        if intent == ANSWER and _has_wrapped_up(state):
            return Ask.NONE
        run = _run_since_learner(state.lines) + 1
        point = InvitePoint(run, state.format, intent, _would_unbalance(state, speaker))
        return state.talk.ask(point, self._rng)


def ends_with_question(text: str) -> bool:
    """The text ends with a question mark, ignoring closing quotes, brackets and spaces."""
    return text.rstrip(_CLOSERS).endswith(QUESTION_MARK)


def stored_ask(ask: str | None, invites_learner: bool) -> Ask:
    """A stored line's ask; a line from before 011 has none, so its invitation tells it."""
    if ask is not None:
        return Ask(ask)
    return Ask.REQUIRED if invites_learner else Ask.NONE


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


def answer_context(
    previous: Sequence[LineFacts], cast: Cast, intent: str
) -> tuple[str | None, bool]:
    """Whose question an answer replies to, and whether the learner asked both hosts (R4)."""
    last = previous[-1] if previous else None
    if intent == FOLLOW_UP:
        return LEARNER, False
    if intent != ANSWER or last is None:
        return None, False
    if last.is_host:
        return last.speaker, False
    return LEARNER, cast.second is not None and len(_named_hosts(last.text, cast)) != 1


def _is_wrap_up_due(state: EpisodeState) -> bool:
    if _has_wrapped_up(state):
        return False
    return len(state.host_lines) + 1 >= state.length.target_host_lines


def _has_wrapped_up(state: EpisodeState) -> bool:
    return any(line.intent == WRAP_UP for line in state.host_lines)


def _would_unbalance(state: EpisodeState, speaker: str) -> bool:
    """Two hosts: inviting after this line would leave one two lines ahead (FR-015)."""
    return state.cast.second is not None and _gap_after(state, speaker) >= BALANCING_GAP


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


def _addressee_of_last_line(state: EpisodeState) -> str | None:
    """011 R19: the host the last host line was for. Legacy lines have no addressee."""
    last = state.last
    if last is None or not last.is_host or last.addressee in (None, LEARNER):
        return None
    return last.addressee if last.addressee != last.speaker else None


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
    positions = _named_hosts(text, cast)
    return min(positions, key=positions.get) if positions else None


def _named_hosts(text: str, cast: Cast) -> dict[str, int]:
    """Each host the text names, with where the name first appears."""
    folded = _fold(text)
    return {
        host.slot: match.start()
        for host in cast.hosts
        if (match := re.search(rf"\b{re.escape(_fold(host.name))}\b", folded))
    }


def _fold(text: str) -> str:
    """Case- and accent-insensitive form, so "lucia" names Lucía."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
