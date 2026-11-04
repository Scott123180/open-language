"""011 T037a: the written line decides who has the turn (FR-003a, FR-003b, FR-005, research R19).

A constant random source makes the cues predictable: 0.99 misses every hazard (`none` lines,
the second host after the greeting), 0.0 hits them (`allowed` lines, the lead after it).
"""

import random

import pytest

from app.main import app
from app.podcasts.routes import get_turn_policy
from app.podcasts.services.episodes import load_episode
from app.podcasts.services.turn_policy import TurnPolicy
from tests.support.podcast_harness import done_of, lines_of, podcast_harness

LEARNER = "Scott"


class Constant(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


def _always(draw: float) -> None:
    app.dependency_overrides[get_turn_policy] = lambda: TurnPolicy(Constant(draw))


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _names(harness, conversation_id: int) -> dict[str, str]:
    return {host["slot"]: host["name"] for host in harness.episode(conversation_id)["hosts"]}


def _opened(harness, legacy: bool = False) -> int:
    """A Panel episode past its opening and greeting, at the hosts' Continue."""
    start = harness.legacy_episode if legacy else harness.start
    conversation_id = start("panel", learner_name=LEARNER)
    harness.writer.script(
        "¡Hola a todos! Bienvenidos al programa. [@all]", "¡Hola a todos! Qué alegría. [@all]"
    )
    harness.stream(conversation_id, "next")
    harness.stream(conversation_id, "next")
    return conversation_id


def _last_host_line(harness, conversation_id: int):
    return [line for line in harness.podcasts.get_lines(conversation_id) if line.is_host][-1]


def _last_cue(harness) -> str:
    _prompt, pending = harness.writer.received[-1]
    return pending[-1].content


@pytest.mark.parametrize(
    "line",
    ["¿Y tú, Scott, comes pan? [@Scott]", "¿Y tú, Scott, comes pan?"],
    ids=["tag", "fallback"],
)
def test_a_question_to_the_learner_on_a_none_line_hands_them_the_turn(harness, line):
    _always(0.99)
    conversation_id = _opened(harness)
    harness.writer.script(line)

    frames = harness.stream(conversation_id, "next")

    stored = _last_host_line(harness, conversation_id).host
    assert (stored.ask, stored.addressee, stored.invites_learner) == ("none", "learner", True)
    assert next(f for f in frames if f.get("event") == "line")["turn"] == "learner"
    assert done_of(frames)["can_pass"] is True


def test_a_question_to_the_other_host_is_answered_by_that_host(harness):
    _always(0.0)
    conversation_id = _opened(harness)
    names = _names(harness, conversation_id)
    harness.writer.script(f"¿Cómo despierta la cafeína el cuerpo? [@{names['second']}]")
    harness.stream(conversation_id, "next")
    assert _last_host_line(harness, conversation_id).host.addressee == "second"

    harness.stream(conversation_id, "next")

    answer = _last_host_line(harness, conversation_id)
    assert answer.host.intent == "answer"
    assert f"Next: {names['second']}." in _last_cue(harness)
    assert f"Answer {names['lead']}'s question" in _last_cue(harness)


def test_a_required_line_that_asks_nobody_still_gives_the_learner_the_turn(harness):
    _always(0.99)
    conversation_id = _opened(harness)
    harness.writer.script("Hoy hablamos del pan de casa. [@all]", "Hoy hablamos del café. [@all]")
    harness.stream(conversation_id, "next")

    harness.stream(conversation_id, "next")

    stored = _last_host_line(harness, conversation_id).host
    assert (stored.ask, stored.invites_learner) == ("required", True)


def test_a_panel_opening_that_asks_the_learner_does_not_hand_over(harness):
    _always(0.0)
    conversation_id = harness.start("panel", learner_name=LEARNER)
    harness.writer.script("Bienvenidos al programa de hoy. ¿Verdad, Scott? [@Scott]")

    frames = harness.stream(conversation_id, "next")

    assert (done_of(frames)["turn"], done_of(frames)["awaiting"]) == ("hosts", "continue")
    assert lines_of(harness.stream(conversation_id, "next"))[0]["intent"] == "greet"


def test_a_question_for_both_hosts_is_passed_on(harness):
    _always(0.99)
    conversation_id = _opened(harness)
    harness.writer.script("¿Y tú, Scott, comes pan? [@Scott]")
    harness.stream(conversation_id, "next")

    harness.say(conversation_id, "¿Qué les gusta a ustedes dos?")

    assert "If it was for you both, answer, then ask" in _last_cue(harness)


def test_no_tag_reaches_a_frame_the_episode_storage_or_speech(harness):
    _always(0.99)
    conversation_id = _opened(harness)
    harness.writer.script_tokens(["Hoy hablamos de pan. ", "¿Y tú, Scott, comes pan? [@Sco", "tt]"])

    frames = harness.stream(conversation_id, "next")

    assert all("[@" not in str(frame) for frame in frames)
    assert all("[@" not in line["content"] for line in harness.episode(conversation_id)["lines"])
    assert all("[@" not in line.content for line in harness.podcasts.get_lines(conversation_id))
    assert all("[@" not in spoken for _voice, spoken, _path in harness.speech.synthesized)


def test_stripping_a_tag_keeps_the_session_and_the_rebuilt_history_ends_lines_with_tags(harness):
    _always(0.99)
    conversation_id = _opened(harness)
    key = load_episode(harness.podcasts, conversation_id).key
    assert _last_host_line(harness, conversation_id).host.was_trimmed is False
    assert harness.engine.is_live(key)
    harness.writer.script("¿Y tú, Scott, comes pan? [@Scott]")
    harness.stream(conversation_id, "next")
    harness.engine.end(key)

    harness.say(conversation_id, "Sí, mucho.")

    rebuilt = harness.writer.sessions[-1].history
    replies = [turn.content for turn in rebuilt if turn.role == "assistant"]
    assert replies[:2] == [
        "¡Hola a todos! Bienvenidos al programa. [@all]",
        "¡Hola a todos! Qué alegría. [@all]",
    ]
    assert replies[2] == f"¿Y tú, {LEARNER}, comes pan? [@{LEARNER}]"


def test_a_legacy_panel_takes_its_invitation_from_the_cue_and_replays_no_tag(harness):
    _always(0.99)
    conversation_id = _opened(harness, legacy=True)
    harness.writer.script("¿Y tú, Scott, comes pan? [@Scott]")

    harness.stream(conversation_id, "next")
    harness.engine.end(load_episode(harness.podcasts, conversation_id).key)
    harness.stream(conversation_id, "next")

    stored = _last_host_line(harness, conversation_id).host
    assert (stored.ask, stored.addressee) == (None, None)
    rebuilt = harness.writer.sessions[-1].history
    assert all("[@" not in turn.content for turn in rebuilt if turn.role == "assistant")
