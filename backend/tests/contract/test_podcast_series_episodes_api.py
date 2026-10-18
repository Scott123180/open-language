"""010 T039: series starts through POST /api/podcasts/episodes (contracts §1–§2)."""

import pytest

from tests.support.podcast_harness import EPISODES, SERIES_SHOW, podcast_harness

HOSTS_CHANGED = "This show's hosts changed. Open the show again."
SHOW_GONE = "That show isn't kept any more. Pick another one."
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
            "angle": None,
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


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _post(harness, show: dict, kind: str = "series", **body):
    payload = {"show": show, "format": "panel", "length": "short", "kind": kind, **body}
    return harness.client.post(EPISODES, json=payload)


def test_the_first_series_start_is_episode_1(harness):
    episode = harness.start_series()

    assert episode["series"]["episode_number"] == 1
    assert isinstance(episode["series"]["series_id"], int)


def test_the_next_start_with_the_same_hosts_is_episode_2(harness):
    first = harness.start_series()

    second = harness.start_series()

    assert second["series"] == {"series_id": first["series"]["series_id"], "episode_number": 2}


def test_changed_hosts_are_a_409(harness):
    harness.start_series()
    listing = harness.listing()
    listing["hosts"][1]["name"] = "Pablo"

    response = _post(harness, listing)

    assert (response.status_code, response.json()["detail"]) == (409, HOSTS_CHANGED)


def test_an_unknown_saved_show_is_a_404(harness):
    response = _post(harness, {**GENERATED, "saved_show_id": 41})

    assert (response.status_code, response.json()["detail"]) == (404, SHOW_GONE)


def test_a_learner_made_show_is_kept_with_a_saved_id(harness):
    episode = _post(harness, GENERATED).json()

    assert isinstance(episode["show"]["saved_show_id"], int)


def test_reading_the_episode_back_gives_its_series(harness):
    episode = harness.start_series()

    assert harness.episode(episode["conversation_id"])["series"] == episode["series"]


def test_past_chats_rows_carry_the_episode_number(harness):
    series_episode = harness.start_series()
    one_off = _post(harness, harness.listing("weekend-food-talk"), kind="one_off").json()

    rows = {row["conversation_id"]: row for row in harness.client.get(EPISODES).json()}

    assert rows[series_episode["conversation_id"]]["episode_number"] == 1
    assert rows[one_off["conversation_id"]]["episode_number"] is None


def test_the_catalogue_lists_a_show_with_its_series(harness):
    episode = harness.start_series("panel")

    listing = harness.listing(SERIES_SHOW)

    assert listing["series"] == {
        "series_id": episode["series"]["series_id"],
        "episode_count": 1,
        "next_episode_number": 2,
        "unfinished_episode": {"conversation_id": episode["conversation_id"], "episode_number": 1},
    }
    assert [host["name"] for host in listing["hosts"]] == [
        host["name"] for host in episode["hosts"]
    ]


def test_a_finished_episode_is_no_longer_unfinished(harness):
    episode = harness.start_series()
    harness.stream(episode["conversation_id"], "end")

    assert harness.listing(SERIES_SHOW)["series"]["unfinished_episode"] is None


# --- US2: one-off episodes (FR-007, FR-014) -------------------------------------------------


def _show_rows(harness):
    from app.podcasts.models import PodcastShow

    return harness.session().query(PodcastShow).all()


def test_a_request_without_a_kind_is_a_007_one_off(harness):
    body = {"show": harness.listing("weekend-food-talk"), "format": "panel", "length": "short"}

    response = harness.client.post(EPISODES, json=body)

    assert response.status_code == 201
    assert response.json()["series"] is None


def test_a_one_off_of_a_learner_made_show_keeps_it_and_marks_it_played(harness):
    episode = _post(harness, GENERATED, kind="one_off").json()

    (row,) = _show_rows(harness)
    assert episode["show"]["saved_show_id"] == row.id
    assert row.last_played_at is not None


def test_a_one_off_of_an_unkept_ready_made_show_keeps_nothing(harness):
    _post(harness, harness.listing("weekend-food-talk"), kind="one_off")

    assert _show_rows(harness) == []


def test_a_one_off_of_a_kept_ready_made_show_marks_it_played(harness):
    harness.start_series(show_id="game-day")
    (row,) = _show_rows(harness)
    first_played = row.last_played_at

    _post(harness, harness.listing("game-day"), kind="one_off")

    (row,) = _show_rows(harness)
    assert row.last_played_at > first_played
