"""T016: the turn policy's guarantees hold over thousands of simulated episodes (data-model §5).

A simulated learner replies, passes, jumps in, names hosts and ends episodes at random. The
policy's own random draws are seeded, so every run checks the same episodes.
"""

import random
import unicodedata
from dataclasses import dataclass, field

import pytest

from app.podcasts.catalog import EPISODE_LENGTHS, PODCAST_FORMATS
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.turn_policy import LEARNER, EpisodeState, LineFacts, TurnPolicy

EPISODES_PER_FORMAT = 1000
LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")
NAMES = {"lead": "Lucía", "second": "Marco"}
LEARNER_REPLIES = ("Sí.", "Lucía, ¿y tú?", "marco, no sé", "Me gusta.", "Lucia y Marco, hola")
SHARE_THRESHOLD_LINES = 8
MINIMUM_SHARE = 0.25
WRAP_UP_WINDOW = 2


@dataclass
class Episode:
    format_id: str
    length_id: str
    lines: list[LineFacts] = field(default_factory=list)
    is_finished: bool = False
    was_ended: bool = False

    def state(self) -> EpisodeState:
        podcast_format = PODCAST_FORMATS[self.format_id]
        second = MARCO if podcast_format.host_count == 2 else None
        return EpisodeState(
            format=podcast_format,
            length=EPISODE_LENGTHS[self.length_id],
            cast=Cast.for_format(podcast_format, LUCIA, second),
            lines=tuple(self.lines),
            is_finished=self.is_finished,
        )


def _host_text(chooser: random.Random, speaker: str) -> str:
    other = "Marco" if speaker == "lead" else "Lucía"
    return chooser.choice(("Una idea.", f"¿Qué opinas, {other}?", "Claro que sí."))


def _host_line(episode: Episode, policy: TurnPolicy, chooser: random.Random, end: bool) -> None:
    state = episode.state()
    cue = policy.end_cue(state) if end else policy.next_cue(state)
    text = _host_text(chooser, cue.speaker_slot)
    episode.lines.append(LineFacts(cue.speaker_slot, cue.intent, cue.invites_learner, False, text))
    episode.was_ended = episode.was_ended or end
    episode.is_finished = cue.intent == "sign_off"


def _learner_acts(episode: Episode, chooser: random.Random) -> str:
    roll = chooser.random()
    if roll < 0.03:
        return "end"
    if roll < 0.2 and PODCAST_FORMATS[episode.format_id].has_jump_in:
        last = episode.lines[-1]
        episode.lines[-1] = LineFacts(last.speaker, last.intent, True, True, last.text)
        return "pass"
    episode.lines.append(LineFacts(LEARNER, None, False, False, chooser.choice(LEARNER_REPLIES)))
    return "reply"


def _step(episode: Episode, policy: TurnPolicy, chooser: random.Random, limit: int) -> None:
    turn = policy.turn(episode.state())
    host_count = sum(1 for line in episode.lines if line.speaker != LEARNER)
    if turn.turn == "learner":
        if _learner_acts(episode, chooser) == "end":
            _host_line(episode, policy, chooser, end=True)
        return
    is_jump_in = turn.awaiting == "continue" and chooser.random() < 0.1
    if is_jump_in and PODCAST_FORMATS[episode.format_id].has_jump_in:
        episode.lines.append(
            LineFacts(LEARNER, None, False, False, chooser.choice(LEARNER_REPLIES))
        )
        return
    _host_line(episode, policy, chooser, end=host_count >= limit or chooser.random() < 0.01)


def simulate(format_id: str, seed: int) -> Episode:
    chooser = random.Random(seed)
    length_id = chooser.choice(list(EPISODE_LENGTHS))
    episode = Episode(format_id, length_id)
    policy = TurnPolicy(random.Random(seed + 1_000_000))
    limit = EPISODE_LENGTHS[length_id].target_host_lines + 8
    while not episode.is_finished:
        _step(episode, policy, chooser, limit)
    return episode


@pytest.fixture(scope="module")
def episodes() -> dict[str, list[Episode]]:
    return {
        format_id: [simulate(format_id, seed) for seed in range(EPISODES_PER_FORMAT)]
        for format_id in PODCAST_FORMATS
    }


def _host_lines(episode: Episode) -> list[LineFacts]:
    return [line for line in episode.lines if line.speaker != LEARNER]


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _first_named(text: str) -> str | None:
    words = [word.strip(",.?¿!¡") for word in _fold(text).split()]
    positions = {
        slot: words.index(_fold(name)) for slot, name in NAMES.items() if _fold(name) in words
    }
    return min(positions, key=positions.get) if positions else None


# --- guarantees -------------------------------------------------------------------------


@pytest.mark.parametrize("format_id", ["one_host", "panel"])
def test_the_invitation_deadline_is_never_exceeded(episodes, format_id):
    deadline = PODCAST_FORMATS[format_id].invite_deadline
    for episode in episodes[format_id]:
        run = 0
        for line in episode.lines:
            if line.speaker == LEARNER:
                run = 0
                continue
            run += 1
            if line.intent != "sign_off":
                assert run <= deadline and (run < deadline or line.invites_learner)
            if line.is_passed:
                run = 0


@pytest.mark.parametrize("format_id", ["panel", "listen"])
def test_no_host_runs_longer_than_the_cap(episodes, format_id):
    cap = PODCAST_FORMATS[format_id].max_host_run
    for episode in episodes[format_id]:
        run, previous = 0, None
        for line in episode.lines:
            run = run + 1 if line.speaker == previous and line.speaker != LEARNER else 1
            previous = line.speaker
            assert line.speaker == LEARNER or run <= cap


@pytest.mark.parametrize("format_id", ["panel", "listen"])
def test_each_host_speaks_at_least_a_quarter_of_a_long_enough_episode(episodes, format_id):
    for episode in episodes[format_id]:
        speakers = [line.speaker for line in _host_lines(episode)]
        if len(speakers) < SHARE_THRESHOLD_LINES:
            continue
        for slot in ("lead", "second"):
            assert speakers.count(slot) / len(speakers) >= MINIMUM_SHARE


@pytest.mark.parametrize("format_id", ["one_host", "panel"])
def test_an_addressed_host_always_speaks_next(episodes, format_id):
    participants = {"lead"} if format_id == "one_host" else {"lead", "second"}
    for episode in episodes[format_id]:
        for line, following in zip(episode.lines, episode.lines[1:], strict=False):
            named = _first_named(line.text) if line.speaker == LEARNER else None
            if named in participants and following.speaker != LEARNER:
                assert following.speaker == named


@pytest.mark.parametrize("format_id", list(PODCAST_FORMATS))
def test_the_wrap_up_comes_within_two_lines_of_the_target(episodes, format_id):
    for episode in episodes[format_id]:
        target = EPISODE_LENGTHS[episode.length_id].target_host_lines
        intents = [line.intent for line in _host_lines(episode)]
        if "wrap_up" not in intents:
            assert episode.was_ended and len(intents) <= target
            continue
        assert target <= intents.index("wrap_up") + 1 <= target + WRAP_UP_WINDOW


def test_every_listen_episode_ends_with_a_sign_off(episodes):
    for episode in episodes["listen"]:
        assert episode.lines[-1].intent == "sign_off"
        assert all(line.intent != "sign_off" for line in episode.lines[:-1])


def test_the_simulation_covers_every_learner_behaviour(episodes):
    panel_lines = [line for episode in episodes["panel"] for line in episode.lines]

    jump_ins = [
        following
        for episode in episodes["panel"]
        for line, following in zip(episode.lines, episode.lines[1:], strict=False)
        if line.speaker != LEARNER and not line.invites_learner and following.speaker == LEARNER
    ]

    assert any(line.is_passed for line in panel_lines)
    assert any(line.speaker == LEARNER and _first_named(line.text) for line in panel_lines)
    assert jump_ins
