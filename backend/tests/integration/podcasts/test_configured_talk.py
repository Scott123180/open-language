"""011 T037: every new episode runs on configured talk with the defaults (FR-001–FR-007, FR-026)."""

import pytest
from sqlalchemy import text

from app.podcasts.catalog import SHOW_TEMPLATES
from app.podcasts.services.episodes import load_episode
from tests.support.podcast_harness import podcast_harness

DONT_ASK = "anything this time."
WEEKEND = SHOW_TEMPLATES["weekend-food-talk"]


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _settings_row(harness, conversation_id: int):
    with harness.session() as session:
        return (
            session.execute(
                text("SELECT * FROM podcast_episode_settings WHERE conversation_id = :id"),
                {"id": conversation_id},
            )
            .mappings()
            .first()
        )


def _host_lines(harness, conversation_id: int):
    return [line for line in harness.podcasts.get_lines(conversation_id) if line.is_host]


def test_a_new_one_off_one_host_episode_stores_the_defaults_and_the_covered_role(harness):
    conversation_id = harness.start("one_host")

    row = _settings_row(harness, conversation_id)

    assert (row["style"], row["line_length"], row["invite_frequency"]) == (
        "balanced",
        "medium",
        "sometimes",
    )
    assert row["today_subject"] is None
    assert row["covered_personality"] == WEEKEND.default_personalities[1]
    assert harness.podcasts.get_episode(conversation_id).learner_role == WEEKEND.learner_role


def test_a_new_series_one_host_episode_covers_the_series_second_host(harness):
    episode = harness.start_series("one_host")
    series = harness.series_storage.get(episode["series"]["series_id"])

    row = _settings_row(harness, episode["conversation_id"])

    assert row["covered_personality"] == series.hosts[1].personality_id


@pytest.mark.parametrize("format_id", ["panel", "listen"])
def test_a_two_host_episode_covers_no_role(harness, format_id):
    assert _settings_row(harness, harness.start(format_id))["covered_personality"] is None


def test_the_standing_prompt_gives_the_line_count_and_the_covered_role(harness):
    harness.client.put("/api/settings", json={"conversation_level": "beginner"})
    conversation_id = harness.start("one_host")

    harness.stream(conversation_id, "next")
    prompt, _pending = harness.writer.received[-1]

    assert "Each host line has three to five sentences" in prompt
    assert "This show usually has a second host" in prompt
    assert "Say at most" not in prompt
    assert "Use at most" in prompt


def test_not_every_line_invites_and_the_deadline_still_holds(harness):
    conversation_id = harness.start("one_host")

    for _step in range(8):
        if harness.episode(conversation_id)["turn"] == "learner":
            harness.say(conversation_id, "Me gusta mucho.")
        else:
            harness.stream(conversation_id, "next")

    cues = [turn.content for _p, pending in harness.writer.received for turn in pending]
    assert any(DONT_ASK in cue or "If it fits" in cue for cue in cues if "Producer note" in cue)
    run = 0
    for line in harness.podcasts.get_lines(conversation_id):
        run = 0 if not line.is_host or line.host.invites_learner else run + 1
        assert run < 4


def test_one_host_accepts_a_jump_in_while_the_host_has_the_floor(harness):
    conversation_id = harness.start("one_host")
    harness.writer.script("¡Hola a todos! Hoy hablamos de comida rica. [@all]")
    harness.stream(conversation_id, "next")
    assert harness.episode(conversation_id)["awaiting"] == "continue"

    frames = harness.say(conversation_id, "¿Puedo decir algo?")

    assert any(frame.get("event") == "line" for frame in frames)


def test_a_learner_question_is_answered_next(harness):
    conversation_id = harness.start("one_host")
    harness.stream(conversation_id, "next")
    if harness.episode(conversation_id)["turn"] != "learner":
        harness.stream(conversation_id, "next")

    harness.say(conversation_id, "¿Por qué el pan sale mejor el domingo?")

    assert _host_lines(harness, conversation_id)[-1].host.intent == "answer"


def test_a_legacy_one_host_episode_keeps_inviting_on_every_line(harness):
    conversation_id = harness.legacy_episode("one_host")

    harness.stream(conversation_id, "next")
    for _step in range(3):
        harness.say(conversation_id, "¿Y tú?")

    lines = _host_lines(harness, conversation_id)
    assert all(line.host.invites_learner for line in lines)
    assert {line.host.intent for line in lines[1:]} == {"discuss"}
    assert {(line.host.ask, line.host.addressee) for line in lines} == {(None, None)}


def test_a_legacy_episode_has_no_settings(harness):
    conversation_id = harness.legacy_episode("panel")

    assert load_episode(harness.podcasts, conversation_id).record.settings is None
