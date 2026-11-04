"""011 T037b: one subject per episode, and the hosts end it (FR-007a, FR-007b, SC-015, R20, R21)."""

import random

import pytest

from app.main import app
from app.podcasts.routes import get_turn_policy
from app.podcasts.services.turn_policy import TurnPolicy
from app.services.factory import get_episode_endings
from tests.support.podcast_harness import done_of, lines_of, podcast_harness

SHORT_TARGET = 10
STATEMENT = "Hoy hablamos de comida rica. [@all]"


class Constant(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


class SpyEndings:
    def __init__(self) -> None:
        self.finished: list[int] = []

    def episode_finished(self, conversation_id: int) -> None:
        self.finished.append(conversation_id)


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        app.dependency_overrides[get_turn_policy] = lambda: TurnPolicy(Constant(0.99))
        yield podcast


def _last_cue(harness) -> str:
    return harness.writer.received[-1][1][-1].content


def _host_lines(harness, conversation_id: int):
    return [line for line in harness.podcasts.get_lines(conversation_id) if line.is_host]


def _to_wrap_up(harness, conversation_id: int) -> None:
    """Continue, or reply with a statement, until the wrap-up line has been written."""
    while not any(line.host.intent == "wrap_up" for line in _host_lines(harness, conversation_id)):
        harness.writer.script(STATEMENT)
        if harness.episode(conversation_id)["turn"] == "learner":
            harness.say(conversation_id, "Me gusta.")
        else:
            harness.stream(conversation_id, "next")


# --- the opening (R20) ----------------------------------------------------------------------


def test_an_opening_without_a_subject_asks_the_host_to_name_one(harness):
    harness.stream(harness.start("one_host"), "next")

    assert "name today's subject: one concrete question within the topic" in _last_cue(harness)


def test_a_later_series_opening_names_a_subject_not_yet_covered(harness):
    harness.play_through(harness.start_series("one_host")["conversation_id"])
    second = harness.start_series("one_host")["conversation_id"]

    harness.stream(second, "next")

    assert "within the topic, not in the covered list." in _last_cue(harness)


# --- the wrap-up and the sign-off (R21) ------------------------------------------------------


def test_a_short_episode_wraps_up_on_its_tenth_host_line_and_asks_for_a_last_thought(harness):
    conversation_id = harness.start("one_host")

    _to_wrap_up(harness, conversation_id)

    wrap_up = _host_lines(harness, conversation_id)[-1]
    assert len(_host_lines(harness, conversation_id)) == SHORT_TARGET
    assert wrap_up.host.invites_learner is True
    assert "tell our guest the show is nearly over" in _last_cue(harness)
    assert _last_cue(harness).endswith("Then ask our guest for one last thought on it.")


def test_a_last_thought_is_followed_by_the_sign_off(harness):
    endings = SpyEndings()
    app.dependency_overrides[get_episode_endings] = lambda: endings
    conversation_id = harness.start("one_host")
    _to_wrap_up(harness, conversation_id)

    frames = harness.say(conversation_id, "Me gustó mucho.")

    assert lines_of(frames)[0]["intent"] == "sign_off"
    assert done_of(frames)["turn"] == "finished"
    assert harness.episode(conversation_id)["status"] == "completed"
    assert endings.finished == [conversation_id]


def test_a_last_question_is_answered_then_the_hosts_sign_off(harness):
    conversation_id = harness.start("one_host")
    _to_wrap_up(harness, conversation_id)
    harness.writer.script(STATEMENT)

    harness.say(conversation_id, "¿Y mañana qué?")
    answer = _host_lines(harness, conversation_id)[-1]
    frames = harness.stream(conversation_id, "next")

    assert (answer.host.intent, answer.host.ask) == ("answer", "none")
    assert lines_of(frames)[0]["intent"] == "sign_off"


def test_a_question_jumped_in_after_the_answer_is_answered_too(harness):
    conversation_id = harness.start("one_host")
    _to_wrap_up(harness, conversation_id)
    harness.writer.script(STATEMENT, STATEMENT)
    harness.say(conversation_id, "¿Y mañana qué?")

    harness.say(conversation_id, "¿Y el domingo?")

    assert [line.host.intent for line in _host_lines(harness, conversation_id)][-2:] == [
        "answer",
        "answer",
    ]
    assert lines_of(harness.stream(conversation_id, "next"))[0]["intent"] == "sign_off"


def test_passing_on_the_panel_wrap_up_signs_off(harness):
    conversation_id = harness.start("panel")
    _to_wrap_up(harness, conversation_id)
    assert harness.episode(conversation_id)["turn"] == "learner"

    frames = harness.stream(conversation_id, "pass")

    assert lines_of(frames)[0]["intent"] == "sign_off"


def test_listen_wraps_up_without_asking_then_signs_off(harness):
    conversation_id = harness.start("listen")
    _to_wrap_up(harness, conversation_id)

    frames = harness.stream(conversation_id, "next")

    assert _host_lines(harness, conversation_id)[-2].host.ask == "none"
    assert lines_of(frames)[0]["intent"] == "sign_off"


def test_end_episode_before_the_wrap_up_signs_off_at_once(harness):
    conversation_id = harness.start("one_host")
    harness.stream(conversation_id, "next")

    frames = harness.stream(conversation_id, "end")

    assert lines_of(frames)[0]["intent"] == "sign_off"
    assert done_of(frames)["turn"] == "finished"


def test_a_legacy_episode_past_its_wrap_up_keeps_discussing_until_end(harness):
    conversation_id = harness.legacy_episode("one_host")
    harness.stream(conversation_id, "next")
    intents = []
    for turn in range(SHORT_TARGET + 2):
        intents += [line["intent"] for line in lines_of(harness.say(conversation_id, f"R{turn}"))]

    assert "wrap_up" in intents
    assert intents[-1] == "discuss"
    assert "sign_off" not in intents
