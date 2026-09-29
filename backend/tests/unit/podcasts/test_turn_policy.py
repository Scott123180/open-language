"""T015: the turn policy, one test per rule (data-model §4, §5).

The policy draws from an injected `random.Random`. `Constant(x)` makes every draw `x`, so a test
can say "the random choice would have picked the other host" and see a rule overrule it.
"""

import random

import pytest

from app.podcasts.catalog import EPISODE_LENGTHS, PODCAST_FORMATS
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.turn_policy import (
    LEARNER,
    EpisodeState,
    LineFacts,
    Turn,
    TurnPolicy,
)

ONE_HOST = PODCAST_FORMATS["one_host"]
PANEL = PODCAST_FORMATS["panel"]
LISTEN = PODCAST_FORMATS["listen"]
SHORT = EPISODE_LENGTHS["short"]
LUCIA = Host("lead", "Lucía", "enthusiast", "es_AR-daniela-high", "host")
MARCO = Host("second", "Marco", "dry_sceptic", "es_ES-davefx-medium", "co_host")
L, S = "lead", "second"


class Constant(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


def host(slot: str, intent: str = "discuss", invites: bool = False, **facts) -> LineFacts:
    return LineFacts(
        speaker=slot,
        intent=intent,
        invites_learner=invites,
        is_passed=facts.get("passed", False),
        text=facts.get("text", "Una frase."),
    )


def learner(text: str = "Sí, claro.") -> LineFacts:
    return LineFacts(speaker=LEARNER, intent=None, invites_learner=False, text=text)


def state(podcast_format=PANEL, lines=(), **overrides) -> EpisodeState:
    second = None if podcast_format.host_count == 1 else MARCO
    values = {
        "format": podcast_format,
        "length": SHORT,
        "cast": Cast.for_format(podcast_format, LUCIA, second),
        "lines": tuple(lines),
        "is_finished": False,
    }
    return EpisodeState(**{**values, **overrides})


def cue(lines, podcast_format=PANEL, draw: float = 0.99):
    return TurnPolicy(Constant(draw)).next_cue(state(podcast_format, lines))


def balanced(count: int) -> list[LineFacts]:
    """`count` host lines alternating lead, second, with nothing that names anyone."""
    return [host(L if index % 2 == 0 else S) for index in range(count)]


# --- whose turn it is (data-model §4) ---------------------------------------------------


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        ((), Turn("hosts", "opening")),
        ((host(L, "open", True), learner()), Turn("hosts", "reply")),
        ((host(L, "open"),), Turn("hosts", "continue")),
        ((host(L, "open", True, passed=True),), Turn("hosts", "continue")),
        ((host(L, "open", True),), Turn("learner", None)),
    ],
    ids=["opening", "reply", "continue", "passed", "learner"],
)
def test_the_turn_follows_the_last_line(lines, expected):
    assert TurnPolicy(Constant(0.5)).turn(state(PANEL, lines)) == expected


def test_a_finished_episode_is_finished():
    finished = state(PANEL, (host(L, "open"),), is_finished=True)

    assert TurnPolicy(Constant(0.5)).turn(finished) == Turn("finished", None)


def test_a_paused_correction_leaves_the_turn_with_the_learner():
    paused = state(ONE_HOST, (host(L, "open", True), learner()), is_awaiting_retry=True)

    assert TurnPolicy(Constant(0.5)).turn(paused) == Turn("learner", None)


# --- intent -----------------------------------------------------------------------------


def test_the_first_line_opens_the_show_and_is_the_leads():
    opening = cue(())

    assert (opening.intent, opening.speaker_slot) == ("open", L)


@pytest.mark.parametrize("podcast_format", [PANEL, LISTEN], ids=["panel", "listen"])
def test_the_second_line_is_the_second_hosts_greeting(podcast_format):
    greeting = cue([host(L, "open")], podcast_format, draw=0.99)

    assert (greeting.intent, greeting.speaker_slot) == ("greet", S)


def test_one_host_never_greets():
    assert cue([host(L, "open", True), learner()], ONE_HOST).intent == "discuss"


def test_an_end_request_signs_off():
    ending = TurnPolicy(Constant(0.5)).end_cue(state(PANEL, balanced(4)))

    assert ending.intent == "sign_off"


def test_reaching_the_length_wraps_up():
    wrap = cue(balanced(SHORT.target_host_lines - 1))

    assert wrap.intent == "wrap_up"


def test_only_one_wrap_up_is_given():
    lines = [*balanced(SHORT.target_host_lines - 1), host(S, "wrap_up", True), learner()]

    assert cue(lines).intent == "discuss"


def test_listen_signs_off_after_the_wrap_up():
    lines = [*balanced(SHORT.target_host_lines - 1), host(S, "wrap_up")]

    assert cue(lines, LISTEN).intent == "sign_off"


def test_otherwise_the_hosts_discuss():
    assert cue(balanced(4)).intent == "discuss"


# --- speaker ----------------------------------------------------------------------------


def test_a_host_with_three_lines_in_a_row_is_excluded():
    lines = [host(S), host(S), host(L), host(L), host(L)]

    assert cue(lines, draw=0.99).speaker_slot == S


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Marco, ¿y tú qué piensas?", S),
        ("marco tiene razón", S),
        ("Lucia, ¿de verdad?", L),
        ("LUCÍA, no estoy de acuerdo", L),
        ("Lucía y Marco, hola", L),
        ("Marco y Lucía, hola", S),
    ],
)
def test_the_learner_names_who_speaks_next(text, expected):
    lines = [host(L, "open"), host(S, "greet"), host(L, invites=True), learner(text)]

    assert cue(lines, draw=0.0).speaker_slot == expected
    assert cue(lines, draw=0.99).speaker_slot == expected


def test_a_name_must_be_a_whole_word():
    lines = [host(L, "open"), host(S, "greet", True), learner("Hablé con Marcos ayer")]

    assert cue(lines, draw=0.7).speaker_slot == L


def test_a_gap_of_two_lines_brings_in_the_quieter_host():
    lines = [host(L), host(S), host(L), host(L)]

    assert cue(lines, draw=0.99).speaker_slot == S


@pytest.mark.parametrize(
    ("last", "expected"),
    [(host(L, text="¿Qué opinas, Marco?"), S), (host(S, text="Lucía, eso no es verdad"), L)],
    ids=["lead-hands-over", "second-hands-over"],
)
def test_a_host_who_names_the_other_hands_over(last, expected):
    lines = [host(L), host(S), last]

    assert cue(lines, draw=0.99).speaker_slot == expected


def test_signing_off_prefers_the_lead():
    ending = TurnPolicy(Constant(0.99)).end_cue(state(PANEL, [host(L), host(S)]))

    assert ending.speaker_slot == L


@pytest.mark.parametrize(("draw", "expected"), [(0.69, L), (0.71, S)])
def test_otherwise_the_other_host_answers_seven_times_in_ten(draw, expected):
    assert cue([host(L), host(S)], draw=draw).speaker_slot == expected


@pytest.mark.parametrize(("draw", "expected"), [(0.59, S), (0.61, L)])
def test_after_the_learner_the_host_who_invited_them_answers_six_times_in_ten(draw, expected):
    lines = [host(L), host(S, invites=True), learner()]

    assert cue(lines, draw=draw).speaker_slot == expected


def test_one_host_always_speaks_as_the_lead():
    assert cue([host(L, "open", True), learner("Marco?")], ONE_HOST).speaker_slot == L


# --- invitation -------------------------------------------------------------------------


def test_one_host_invites_the_learner_on_every_line():
    assert cue([host(L, "open", True), learner()], ONE_HOST, draw=0.99).invites_learner is True


def test_one_host_opening_invites_the_learner():
    assert cue((), ONE_HOST, draw=0.99).invites_learner is True


def test_a_sign_off_never_invites():
    lines = [host(L, "open", True), learner()]

    assert TurnPolicy(Constant(0.0)).end_cue(state(ONE_HOST, lines)).invites_learner is False


def test_listen_never_invites():
    assert cue(balanced(3), LISTEN, draw=0.0).invites_learner is False


def _after_learner(host_lines: list[LineFacts]) -> list[LineFacts]:
    return [host(L), host(S, invites=True), learner(), *host_lines]


@pytest.mark.parametrize(
    ("host_lines", "hazard"),
    [([], 0.25), ([host(S)], 0.45), ([host(S), host(L)], 0.6)],
    ids=["run-1", "run-2", "run-3"],
)
def test_panel_invitations_grow_more_likely_with_each_host_line(host_lines, hazard):
    lines = _after_learner(host_lines)

    assert cue(lines, draw=hazard - 0.01).invites_learner is True
    assert cue(lines, draw=hazard + 0.01).invites_learner is False


def test_the_fourth_host_line_always_invites():
    lines = _after_learner([host(S), host(L), host(S)])

    assert cue(lines, draw=0.99).invites_learner is True


def test_a_pass_restarts_the_count():
    lines = [host(L), host(S), host(L), host(S, invites=True, passed=True)]

    assert cue(lines, draw=0.3).invites_learner is False


def test_a_wrap_up_always_invites_the_learner_in_a_panel():
    wrap = cue(balanced(SHORT.target_host_lines - 1), draw=0.99)

    assert (wrap.intent, wrap.invites_learner) == ("wrap_up", True)


def test_an_addressed_line_that_leaves_a_host_two_lines_ahead_does_not_invite():
    lines = [host(L), host(S), host(L), host(S), host(L, invites=True), learner("Lucía, dime")]

    addressed = cue(lines, draw=0.0)

    assert (addressed.speaker_slot, addressed.invites_learner) == (L, False)


# --- settle and pass --------------------------------------------------------------------


def test_an_invitation_after_two_hosts_disagree_asks_the_learner_to_settle_it():
    settle = cue([host(L), host(S)], draw=0.0)

    assert (settle.invites_learner, settle.is_settle_invite) == (True, True)


def test_an_invitation_after_one_host_is_not_a_settle_invite():
    invite = cue([host(S), host(L), host(L)], draw=0.0)

    assert (invite.invites_learner, invite.is_settle_invite) == (True, False)


def test_a_line_that_does_not_invite_is_never_a_settle_invite():
    assert cue([host(L), host(S)], draw=0.99).is_settle_invite is False


def test_the_line_after_a_pass_knows_the_learner_passed():
    lines = [host(L), host(S, invites=True, passed=True)]

    assert cue(lines, draw=0.5).is_after_pass is True


def test_an_ordinary_line_is_not_after_a_pass():
    assert cue([host(L), host(S)], draw=0.5).is_after_pass is False
