"""010 T107: PUT /api/podcasts/favourites and DELETE /api/podcasts/shows/{id} (contracts §3)."""

import pytest

from tests.support.podcast_harness import podcast_harness

FAVOURITES = "/api/podcasts/favourites"
SHOWS = "/api/podcasts/shows"
SHOW_GONE = "That show isn't kept any more. Pick another one."
SUGGESTION = {
    "source": "suggested",
    "show_id": None,
    "title": "Night Trains of Europe",
    "premise": "Sleeper trains, border crossings and dining cars.",
    "topic": "night trains",
    "learner_role": "guest",
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
            "personality_id": "pragmatist",
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


def _favourite(harness, show: dict, is_favourite: bool = True):
    return harness.client.put(FAVOURITES, json={"show": show, "is_favourite": is_favourite})


def test_favouriting_a_ready_made_show_returns_its_listing(harness):
    response = _favourite(harness, harness.listing("game-day"))

    assert response.status_code == 200
    listing = response.json()
    assert (listing["show_id"], listing["is_favourite"], listing["saved_show_id"]) == (
        "game-day",
        True,
        None,
    )


def test_favouriting_an_unsaved_suggestion_keeps_it(harness):
    listing = _favourite(harness, SUGGESTION).json()

    assert listing["is_favourite"] is True
    assert isinstance(listing["saved_show_id"], int)
    assert listing["title"] == SUGGESTION["title"]


@pytest.mark.parametrize("show", ["ready", "unplayed"])
def test_unfavouriting_a_show_kept_only_by_its_favourite_is_a_204(harness, show):
    draft = (
        harness.listing("game-day") if show == "ready" else _favourite(harness, SUGGESTION).json()
    )
    _favourite(harness, draft)

    response = _favourite(harness, draft, is_favourite=False)

    assert response.status_code == 204


def test_unfavouriting_a_show_with_a_series_returns_its_listing(harness):
    harness.start_series(show_id="game-day")
    _favourite(harness, harness.listing("game-day"))

    response = _favourite(harness, harness.listing("game-day"), is_favourite=False)

    assert response.status_code == 200
    assert response.json()["is_favourite"] is False


def test_a_bad_draft_is_a_422(harness):
    bad = {**harness.listing("game-day"), "show_id": "no-such-show"}

    assert _favourite(harness, bad).status_code == 422


def test_removing_a_kept_learner_made_show_is_a_204(harness):
    saved = _favourite(harness, SUGGESTION).json()["saved_show_id"]

    assert harness.client.delete(f"{SHOWS}/{saved}").status_code == 204


@pytest.mark.parametrize("which", ["unknown", "ready-made"])
def test_removing_an_unknown_or_ready_made_show_is_a_404(harness, which):
    if which == "ready-made":
        _favourite(harness, harness.listing("game-day"))
        from app.podcasts.models import PodcastShow

        show_row_id = harness.session().query(PodcastShow).one().id
    else:
        show_row_id = 999

    response = harness.client.delete(f"{SHOWS}/{show_row_id}")

    assert (response.status_code, response.json()["detail"]) == (404, SHOW_GONE)
