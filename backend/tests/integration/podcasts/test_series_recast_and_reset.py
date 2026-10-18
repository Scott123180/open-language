"""010 T069: a recast host is new for one episode and stays; Start over keeps the episodes."""

from app.podcasts.models import PodcastSeriesEpisode
from app.podcasts.services.series_snapshot import SeriesSnapshot
from tests.support.podcast_harness import EPISODES, podcast_harness

SERIES = "/api/podcasts/series"


def _hosts(episode: dict) -> list[tuple]:
    return [(h["slot"], h["name"], h["personality_id"], h["voice_key"]) for h in episode["hosts"]]


def _snapshot(harness, conversation_id: int) -> SeriesSnapshot:
    link = harness.session().get(PodcastSeriesEpisode, conversation_id)
    return SeriesSnapshot.from_json(link.snapshot)


def test_a_recast_host_is_introduced_once_and_then_kept(tmp_path):
    with podcast_harness(tmp_path) as harness:
        first = harness.start_series("panel")
        second = harness.start_series("panel")
        series_id = first["series"]["series_id"]
        recast = harness.client.post(
            f"{SERIES}/{series_id}/hosts/second/recast",
            json={"language": "es", "learner_name": "Sam"},
        ).json()
        newcomer = recast["hosts"][1]["name"]

        third = harness.start_series("panel")
        harness.stream(third["conversation_id"], "next")
        standing_prompt, _pending = harness.writer.received[-1]
        fourth = harness.start_series("panel")

        assert _snapshot(harness, third["conversation_id"]).new_host_slots == ("second",)
        assert _hosts(third)[0] == _hosts(second)[0] == _hosts(first)[0]
        assert _hosts(third)[1][1] == newcomer
        assert f"{newcomer} is new to the show" in standing_prompt
        assert _hosts(fourth) == _hosts(third)
        assert _snapshot(harness, fourth["conversation_id"]).new_host_slots == ()


def test_start_over_forgets_the_series_and_keeps_its_episodes(tmp_path):
    with podcast_harness(tmp_path) as harness:
        first = harness.start_series("one_host", learner_name="Sam")
        harness.stream(first["conversation_id"], "next")
        harness.say(first["conversation_id"], "Odio las mañanas.")
        series_id = first["series"]["series_id"]
        harness.memory.queue(
            {
                "topic": {"conversation_language": "el sueño", "english": "Sleep"},
                "about_learner": [],
            }
        )
        harness.client.post(f"{SERIES}/{series_id}/memory")

        assert harness.client.delete(f"{SERIES}/{series_id}").status_code == 204

        rows = {row["conversation_id"]: row for row in harness.client.get(EPISODES).json()}
        assert rows[first["conversation_id"]]["episode_number"] is None
        assert harness.listing()["series"] is None
        assert harness.start_series()["series"]["episode_number"] == 1
        assert harness.episode(first["conversation_id"])["lines"]
