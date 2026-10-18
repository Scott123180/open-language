"""010 T108: My shows: favourites, series in this language, played learner-made shows (R9)."""

from app.podcasts.models import PodcastShow
from tests.support.podcast_harness import CATALOG, EPISODES, podcast_harness, podcast_harness_on
from tests.support.scratch_database import make_sessions

FAVOURITES = "/api/podcasts/favourites"
GENERATED = {
    "source": "generated",
    "show_id": None,
    "title": "Night Shift Abroad",
    "premise": "Two nurses swap stories about working far from home.",
    "topic": "living abroad as a nurse",
    "learner_role": "caller",
    "language": "es",
    "hosts": [
        {
            "slot": "lead",
            "name": "Lucía",
            "personality_id": "storyteller",
            "voice_key": "es_AR-daniela-high",
            "show_role": "host",
            "angle": "Misses home.",
        },
        {
            "slot": "second",
            "name": "Marco",
            "personality_id": "dry_sceptic",
            "voice_key": "es_ES-davefx-medium",
            "show_role": "co_host",
            "angle": None,
        },
    ],
}


def _mine(harness) -> list[dict]:
    return harness.client.get(CATALOG).json()["my_shows"]


def _titles(harness) -> list[str]:
    return [show["title"] for show in _mine(harness)]


def _favourite(harness, show: dict, is_favourite: bool = True):
    return harness.client.put(FAVOURITES, json={"show": show, "is_favourite": is_favourite})


def _play(harness, show: dict, kind: str = "series") -> dict:
    body = {"show": show, "format": "panel", "length": "short", "kind": kind}
    response = harness.client.post(EPISODES, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_my_shows_is_empty_without_favourites_series_or_kept_shows(tmp_path):
    with podcast_harness(tmp_path) as harness:
        assert _mine(harness) == []


def test_my_shows_holds_favourites_series_and_played_learner_made_shows_newest_first(tmp_path):
    with podcast_harness(tmp_path) as harness:
        harness.start_series(show_id="big-little-questions")
        _play(harness, GENERATED, kind="one_off")
        _favourite(harness, harness.listing("game-day"))

        assert _titles(harness) == ["Game Day", "Night Shift Abroad", "Big Little Questions"]


def test_a_ready_made_show_in_my_shows_equals_its_listing(tmp_path):
    with podcast_harness(tmp_path) as harness:
        harness.start_series(show_id="game-day")
        _favourite(harness, harness.listing("game-day"))

        (mine,) = _mine(harness)
        assert mine == harness.listing("game-day")


def test_a_favourite_is_shared_by_every_language_and_a_series_is_not(tmp_path):
    with podcast_harness(tmp_path) as harness:
        harness.start_series(show_id="game-day")
        _favourite(harness, harness.listing("game-day"))
        harness.conversations.update_settings(target_language="de")

        (mine,) = _mine(harness)
        assert (mine["show_id"], mine["is_favourite"], mine["series"]) == ("game-day", True, None)


def test_a_favourite_survives_a_restart(tmp_path):
    db_file = tmp_path / "restart.db"
    with podcast_harness_on(make_sessions(db_file), tmp_path) as harness:
        _favourite(harness, harness.listing("game-day"))
    with podcast_harness_on(make_sessions(db_file), tmp_path) as harness:
        assert _titles(harness) == ["Game Day"]


def test_unfavouriting_keeps_a_show_with_a_series_and_a_played_learner_made_show(tmp_path):
    with podcast_harness(tmp_path) as harness:
        harness.start_series(show_id="game-day")
        _favourite(harness, harness.listing("game-day"))
        played = _play(harness, GENERATED, kind="one_off")["show"]["saved_show_id"]
        kept = {**GENERATED, "saved_show_id": played}
        _favourite(harness, kept)

        _favourite(harness, harness.listing("game-day"), is_favourite=False)
        _favourite(harness, kept, is_favourite=False)

        assert sorted(_titles(harness)) == ["Game Day", "Night Shift Abroad"]


def test_removing_a_played_show_ends_its_series_everywhere_and_keeps_its_episodes(tmp_path):
    with podcast_harness(tmp_path) as harness:
        spanish = _play(harness, GENERATED)
        saved = spanish["show"]["saved_show_id"]
        harness.conversations.update_settings(target_language="de")
        german_hosts = [
            {**GENERATED["hosts"][0], "voice_key": "de_DE-kerstin-low", "name": "Lena"},
            {**GENERATED["hosts"][1], "voice_key": "de_DE-thorsten-medium", "name": "Jonas"},
        ]
        _play(
            harness, {**GENERATED, "language": "de", "hosts": german_hosts, "saved_show_id": saved}
        )

        assert harness.client.delete(f"/api/podcasts/shows/{saved}").status_code == 204

        assert _mine(harness) == []
        harness.conversations.update_settings(target_language="es")
        assert _mine(harness) == []
        rows = {row["conversation_id"]: row for row in harness.client.get(EPISODES).json()}
        assert rows[spanish["conversation_id"]]["episode_number"] is None


def test_favouriting_the_same_unsaved_draft_twice_keeps_one_show(tmp_path):
    with podcast_harness(tmp_path) as harness:
        _favourite(harness, GENERATED)
        _favourite(harness, GENERATED)

        assert harness.session().query(PodcastShow).count() == 1


def test_a_played_generated_show_is_listed_and_its_next_episode_keeps_the_hosts(tmp_path):
    with podcast_harness(tmp_path) as harness:
        first = _play(harness, GENERATED)

        (mine,) = _mine(harness)
        second = _play(harness, mine)

        assert mine["saved_show_id"] == first["show"]["saved_show_id"]
        assert [h["name"] for h in second["hosts"]] == [h["name"] for h in first["hosts"]]
        assert second["series"]["episode_number"] == 2


def test_a_stale_saved_show_cannot_start(tmp_path):
    with podcast_harness(tmp_path) as harness:
        response = harness.client.post(
            EPISODES,
            json={"show": {**GENERATED, "saved_show_id": 77}, "format": "panel", "length": "short"},
        )

        assert response.status_code == 404
