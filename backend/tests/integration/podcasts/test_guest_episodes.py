"""011 T095: the show's expert joins a One host series for one episode (FR-024a, R10)."""

import pytest

from tests.support.podcast_harness import EPISODES, podcast_harness

SERIES = "/api/podcasts/series"


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _one_host_series(harness) -> dict:
    return harness.start_series("one_host", learner_name="Sam")


def _expert(harness, series_id: int, avoid=()) -> dict:
    body = {"language": "es", "slot": "second", "format": "panel", "learner_name": "Sam"}
    response = harness.client.post(
        f"{SERIES}/{series_id}/guest", json={**body, "avoid_names": list(avoid)}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _panel_with(harness, guest: dict) -> dict:
    payload = {"show": harness.listing(), "format": "panel", "length": "short", "kind": "series"}
    response = harness.client.post(
        EPISODES, json={**payload, "guest": guest, "learner_name": "Sam"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_a_panel_this_episode_start_seats_the_expert_guest_in_the_second_chair(harness):
    series_id = _one_host_series(harness)["series"]["series_id"]
    guest = _expert(harness, series_id)

    episode = _panel_with(harness, guest)

    hosts = harness.podcasts.get_hosts(episode["conversation_id"])
    assert [(host.slot, host.name) for host in hosts][1] == ("second", guest["name"])
    snapshot = harness.podcasts.get_episode(episode["conversation_id"]).series.snapshot
    assert (snapshot.guest_slot, snapshot.new_host_slots) == ("second", ())


def test_the_series_keeps_its_hosts_and_the_next_draft_has_them_only(harness):
    first = _one_host_series(harness)
    series_id = first["series"]["series_id"]
    before = harness.client.get(f"{SERIES}/{series_id}").json()["hosts"]
    guest = _expert(harness, series_id)

    _panel_with(harness, guest)

    assert harness.client.get(f"{SERIES}/{series_id}").json()["hosts"] == before
    assert guest["name"] not in {host["name"] for host in harness.listing()["hosts"]}


def test_the_guest_episode_counts_as_a_series_episode(harness):
    series_id = _one_host_series(harness)["series"]["series_id"]

    episode = _panel_with(harness, _expert(harness, series_id))

    assert episode["series"]["episode_number"] == 2
    assert harness.client.get(f"{SERIES}/{series_id}").json()["episode_count"] == 2


def test_a_second_panel_this_episode_casts_afresh(harness):
    series_id = _one_host_series(harness)["series"]["series_id"]
    first = _expert(harness, series_id)
    _panel_with(harness, first)

    again = _expert(harness, series_id, avoid=[first["name"]])

    assert again["name"] != first["name"]
    assert _panel_with(harness, again)["series"]["episode_number"] == 3
