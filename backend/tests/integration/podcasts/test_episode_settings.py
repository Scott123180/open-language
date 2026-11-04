"""011 T070: an episode keeps the settings it started with (FR-012, FR-013, US2 acceptance)."""

import random

import pytest

from app.main import app
from app.podcasts.routes import get_turn_policy
from app.podcasts.services.episodes import load_episode
from app.podcasts.services.turn_policy import TurnPolicy
from tests.support.podcast_harness import podcast_harness

PRESENTED = {"style": "presented", "line_length": "long", "invite_frequency": "rarely"}
CONVERSATION = {"style": "conversation", "line_length": "short", "invite_frequency": "often"}


class Constant(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        app.dependency_overrides[get_turn_policy] = lambda: TurnPolicy(Constant(0.99))
        yield podcast


def _prompt(harness, conversation_id: int) -> str:
    from app.conversation_levels import ConversationLevel

    episode = load_episode(harness.podcasts, conversation_id)
    return episode.standing_prompt(ConversationLevel.NATURAL)


def test_an_episode_resumes_with_its_own_settings_after_the_preferences_change(harness):
    conversation_id = harness.start_with(settings=PRESENTED).json()["conversation_id"]
    before = _prompt(harness, conversation_id)

    harness.start_with(settings=CONVERSATION)

    assert harness.episode(conversation_id)["settings"]["style"] == "presented"
    assert _prompt(harness, conversation_id) == before


def test_a_long_rarely_episode_asks_for_long_lines_and_says_not_to_ask(harness):
    conversation_id = harness.start_with(settings=PRESENTED).json()["conversation_id"]

    harness.stream(conversation_id, "next")
    harness.stream(conversation_id, "next")
    prompt, pending = harness.writer.received[-1]

    assert "Each host line has five to eight sentences" in prompt
    assert pending[-1].content.endswith("Don't ask our guest anything this time.")


def test_a_one_off_start_updates_the_last_used_settings_and_a_series_start_does_not(harness):
    harness.start_with(settings=PRESENTED)
    harness.start_series(settings=CONVERSATION)

    preferences = harness.client.get("/api/podcasts/preferences").json()

    assert (preferences["last_style"], preferences["last_line_length"]) == ("presented", "long")
    assert preferences["last_invite_frequency"] == "rarely"


def test_the_role_and_the_subject_are_never_remembered(harness):
    harness.start_with(settings={**PRESENTED, "learner_role": "caller", "today_subject": "el pan"})

    preferences = harness.client.get("/api/podcasts/preferences").json()
    next_episode = harness.start_with().json()

    assert "learner_role" not in preferences and "today_subject" not in preferences
    assert next_episode["settings"]["learner_role"] == "guest"
    assert next_episode["settings"]["today_subject"] is None
