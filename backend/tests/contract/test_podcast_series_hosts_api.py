"""010 T068: recast, Start over, stable defaults and the name clash (contracts §1, §6, §7)."""

import pytest

from app.podcasts.catalog import SHOW_TEMPLATES
from app.podcasts.schemas import LANGUAGE_CHANGED
from tests.support.podcast_harness import EPISODES, podcast_harness

SERIES = "/api/podcasts/series"
SERIES_GONE = "That series isn't there any more. Open the show again."


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _series(harness) -> tuple[int, dict]:
    episode = harness.start_series("panel")
    return episode["series"]["series_id"], episode


def _recast(harness, series_id: int, slot: str = "second", **body):
    payload = {"language": "es", "learner_name": "Sam", **body}
    return harness.client.post(f"{SERIES}/{series_id}/hosts/{slot}/recast", json=payload)


def test_a_recast_returns_the_series_with_the_new_host(harness):
    series_id, episode = _series(harness)

    response = _recast(harness, series_id, personality_id="joker")

    assert response.status_code == 200
    lead, second = response.json()["hosts"]
    assert lead["name"] == episode["hosts"][0]["name"]
    assert (second["personality_id"], second["has_history"], second["is_new_next_episode"]) == (
        "joker",
        False,
        True,
    )


@pytest.mark.parametrize(
    ("slot", "body"),
    [("third", {}), ("second", {"personality_id": "pirate"}), ("second", {"language": "de"})],
    ids=["bad-slot", "unknown-personality", "language-changed"],
)
def test_a_bad_recast_is_a_422(harness, slot, body):
    series_id, _episode = _series(harness)

    assert _recast(harness, series_id, slot, **body).status_code == 422


def test_the_other_hosts_personality_is_refused_plainly(harness):
    series_id, episode = _series(harness)
    lead = episode["hosts"][0]

    response = _recast(harness, series_id, personality_id=lead["personality_id"])

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == f"{lead['name']} already has that personality. Pick another one."
    )


def test_a_recast_after_a_language_change_says_so(harness):
    series_id, _episode = _series(harness)

    assert _recast(harness, series_id, language="de").json()["detail"] == LANGUAGE_CHANGED


def test_recasting_an_unknown_series_is_a_404(harness):
    assert _recast(harness, 999).status_code == 404


def test_start_over_deletes_the_series(harness):
    series_id, _episode = _series(harness)

    response = harness.client.delete(f"{SERIES}/{series_id}")

    assert response.status_code == 204
    gone = harness.client.get(f"{SERIES}/{series_id}")
    assert (gone.status_code, gone.json()["detail"]) == (404, SERIES_GONE)


def test_starting_over_an_unknown_series_is_a_404(harness):
    assert harness.client.delete(f"{SERIES}/999").status_code == 404


def test_unstarted_ready_made_shows_list_the_same_hosts_every_time(harness):
    first = harness.client.get("/api/podcasts/catalog").json()["shows"]
    second = harness.client.get("/api/podcasts/catalog").json()["shows"]

    assert [show["hosts"] for show in first] == [show["hosts"] for show in second]
    assert len(first) == len(SHOW_TEMPLATES)


def test_a_series_host_named_like_the_learner_is_refused_with_the_series_wording(harness):
    _series_id, episode = _series(harness)
    lead = episode["hosts"][0]["name"]
    body = {"show": harness.listing(), "format": "panel", "length": "short", "kind": "series"}

    response = harness.client.post(EPISODES, json={**body, "learner_name": lead.upper()})

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == f"{lead} has the same name as you. Change the name the hosts call you."
    )
