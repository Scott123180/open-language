"""011 T067: Episode settings on POST /api/podcasts/episodes (contracts §3, §5; data-model §5.1)."""

import pytest
from sqlalchemy import text

from app.services.llm.base import LLMError
from tests.support.podcast_harness import EPISODES, podcast_harness

PRESENTED = {
    "style": "presented",
    "line_length": "long",
    "invite_frequency": "rarely",
    "learner_role": "caller",
    "today_subject": "why we yawn",
}
DECLINED = "That subject can't be used for an episode. Change it or clear it, then start."


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _count(harness, table: str) -> int:
    with harness.session() as session:
        return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def _detail(response) -> str:
    detail = response.json()["detail"]
    message = detail if isinstance(detail, str) else detail[0]["msg"]
    return message.removeprefix("Value error, ")


def test_a_start_with_settings_returns_them_with_their_labels(harness):
    response = harness.start_with(settings=PRESENTED)

    assert response.status_code == 201
    assert response.json()["settings"] == {
        "style": "presented",
        "style_label": "Presented",
        "line_length": "long",
        "line_length_label": "Long",
        "invite_frequency": "rarely",
        "invite_frequency_label": "Rarely",
        "learner_role": "caller",
        "today_subject": "why we yawn",
    }


def test_a_start_without_settings_takes_the_defaults_and_the_shows_role(harness):
    settings = harness.start_with().json()["settings"]

    assert (settings["style"], settings["line_length"], settings["invite_frequency"]) == (
        "balanced",
        "medium",
        "sometimes",
    )
    assert settings["learner_role"] == "guest"
    assert settings["today_subject"] is None


def test_a_partial_settings_object_fills_in_the_rest(harness):
    settings = harness.start_with(settings={"style": "conversation"}).json()["settings"]

    assert (settings["style"], settings["line_length"]) == ("conversation", "medium")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"style": "loud"}, "That style isn't in the list. Pick one of the listed ones."),
        ({"learner_role": "judge"}, "Your role must be guest, co-host or caller."),
        ({"today_subject": "x" * 121}, "Today's subject can be at most 120 characters."),
    ],
)
def test_each_refusal_is_a_422_with_its_message(harness, change, message):
    response = harness.start_with(settings=change)

    assert (response.status_code, _detail(response)) == (422, message)


def test_a_declined_subject_starts_nothing(harness):
    harness.subjects.reply = {"is_suitable": False, "decline_reason": "unkind"}

    response = harness.start_with(settings={"today_subject": "something unkind"})

    assert (response.status_code, _detail(response)) == (422, DECLINED)
    assert _count(harness, "conversations") == 0


def test_a_subject_check_that_cannot_reach_the_provider_is_a_503(harness):
    harness.subjects.error = LLMError("down", "Ollama isn't running. Start it and try again.")

    response = harness.start_with(settings={"today_subject": "why we yawn"})

    assert (response.status_code, _detail(response)) == (
        503,
        "Ollama isn't running. Start it and try again.",
    )
    assert _count(harness, "conversations") == 0


def test_with_no_subject_the_model_is_not_asked(harness):
    harness.start_with(settings={"style": "presented"})

    assert harness.subjects.calls == []


def test_listen_keeps_the_default_frequency_and_the_shows_role(harness):
    settings = harness.start_with("listen", settings=PRESENTED).json()["settings"]

    assert (settings["invite_frequency"], settings["learner_role"]) == ("sometimes", "guest")
    assert (settings["style"], settings["today_subject"]) == ("presented", "why we yawn")


def test_a_pre_011_episode_has_no_settings(harness):
    conversation_id = harness.legacy_episode("panel")

    assert harness.client.get(f"{EPISODES}/{conversation_id}").json()["settings"] is None
