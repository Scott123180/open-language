"""010 T042: a series episode resumes with the memory it started with (research R5)."""

from app.conversation_levels import ConversationLevel
from app.podcasts.services.cues import episode_history
from app.podcasts.services.episodes import load_episode
from tests.support.podcast_harness import podcast_harness

SERIES = "/api/podcasts/series"
LATER_POINT = {
    "topic": {"conversation_language": "los ronquidos", "english": "Snoring"},
    "about_learner": [{"conversation_language": "Tiene un gato.", "english": "You have a cat."}],
}


def _rebuilt(harness, conversation_id: int):
    """The standing prompt and the history a rebuilt session would be given."""
    episode = load_episode(harness.podcasts, conversation_id)
    history = episode_history(
        episode.facts, episode.cast, episode.learner_label, episode.series_brief
    )
    return episode.standing_prompt(ConversationLevel.NATURAL), history


def test_resuming_after_new_memories_rebuilds_the_same_prompt_and_history(tmp_path):
    with podcast_harness(tmp_path) as harness:
        first = harness.start_series("one_host", learner_name="Sam")
        harness.stream(first["conversation_id"], "next")
        second = harness.start_series("one_host", learner_name="Sam")
        harness.stream(second["conversation_id"], "next")
        before = _rebuilt(harness, second["conversation_id"])

        harness.say(first["conversation_id"], "Tengo un gato.")
        harness.memory.queue(LATER_POINT)
        harness.client.post(f"{SERIES}/{first['series']['series_id']}/memory")

        after = _rebuilt(harness, second["conversation_id"])
        assert after == before
        assert "Tiene un gato." not in after[0]


def test_the_session_is_not_rebuilt_when_memory_grows_mid_episode(tmp_path):
    with podcast_harness(tmp_path) as harness:
        first = harness.start_series("one_host", learner_name="Sam")
        harness.stream(first["conversation_id"], "next")
        harness.say(first["conversation_id"], "Tengo un gato.")
        second = harness.start_series("one_host", learner_name="Sam")
        harness.stream(second["conversation_id"], "next")
        opened = harness.writer.open_count

        harness.memory.queue(LATER_POINT)
        harness.client.post(f"{SERIES}/{first['series']['series_id']}/memory")
        harness.say(second["conversation_id"], "Hola de nuevo.")

        assert harness.writer.open_count == opened
