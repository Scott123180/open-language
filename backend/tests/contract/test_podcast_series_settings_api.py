"""011 T093: the series settings reset and the guest casting (contracts §7–§8)."""

import pytest

from app.podcasts.schemas import LANGUAGE_CHANGED
from tests.support.podcast_harness import podcast_harness

SERIES = "/api/podcasts/series"
SERIES_GONE = "That series isn't there any more. Open the show again."
NO_SEAT = "That guest has no seat in this format. Pick Panel, or invite them in the host's place."
STANDARD = {
    "format": "one_host",
    "length": "medium",
    "style": "balanced",
    "line_length": "medium",
    "invite_frequency": "sometimes",
    "learner_role": "guest",
}
HOST_DRAFT_KEYS = {"slot", "name", "personality_id", "voice_key", "show_role", "angle"}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _series(harness, format: str = "panel", **body) -> dict:
    return harness.start_series(format, learner_name="Sam", **body)


def _series_id(harness, format: str = "panel", **body) -> int:
    return _series(harness, format, **body)["series"]["series_id"]


def _guest(harness, series_id: int, **body):
    payload = {"language": "es", "slot": "second", "format": "panel", "learner_name": "Sam"}
    return harness.client.post(f"{SERIES}/{series_id}/guest", json={**payload, **body})


# --- DELETE /series/{id}/settings ---------------------------------------------------------


def test_the_reset_returns_the_shows_standard_settings(harness):
    series_id = _series_id(harness, settings={"style": "presented"})

    response = harness.client.delete(f"{SERIES}/{series_id}/settings")

    assert response.status_code == 200
    assert response.json()["usual_settings"] == STANDARD
    assert response.json()["is_standard"] is True


def test_the_reset_leaves_the_count_the_hosts_and_the_memory(harness):
    series_id = _series_id(harness)
    before = harness.client.get(f"{SERIES}/{series_id}").json()

    after = harness.client.delete(f"{SERIES}/{series_id}/settings").json()

    for key in ("episode_count", "hosts", "remembered"):
        assert after[key] == before[key]


def test_resetting_an_unknown_series_is_a_404(harness):
    response = harness.client.delete(f"{SERIES}/999/settings")

    assert (response.status_code, response.json()["detail"]) == (404, SERIES_GONE)


def test_resetting_a_series_of_another_language_is_a_422(harness):
    series_id = _series_id(harness)
    harness.client.put("/api/settings", json={"target_language": "de"})

    response = harness.client.delete(f"{SERIES}/{series_id}/settings")

    assert (response.status_code, response.json()["detail"]) == (422, LANGUAGE_CHANGED)


# --- POST /series/{id}/guest --------------------------------------------------------------


def test_a_guest_is_a_host_draft_named_unlike_the_series_hosts(harness):
    episode = _series(harness)

    response = _guest(harness, episode["series"]["series_id"], personality_id="joker")

    assert response.status_code == 200
    guest = response.json()
    assert set(guest) == HOST_DRAFT_KEYS
    assert (guest["slot"], guest["personality_id"]) == ("second", "joker")
    assert guest["name"] not in {host["name"] for host in episode["hosts"]}


def test_a_one_host_series_second_seat_guest_is_the_shows_expert(harness):
    series_id = _series_id(harness, "one_host")

    assert _guest(harness, series_id).json()["personality_id"] == "expert"


def test_another_guest_avoids_the_names_already_drawn(harness):
    series_id = _series_id(harness, "one_host")
    first = _guest(harness, series_id).json()["name"]

    assert _guest(harness, series_id, avoid_names=[first]).json()["name"] != first


def test_casting_a_guest_stores_nothing(harness):
    series_id = _series_id(harness, "one_host")
    before = harness.client.get(f"{SERIES}/{series_id}").json()

    _guest(harness, series_id)

    assert harness.client.get(f"{SERIES}/{series_id}").json() == before


def test_a_guest_for_an_unknown_series_is_a_404(harness):
    assert _guest(harness, 999).status_code == 404


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"slot": "third"}, None),
        ({"personality_id": "pirate"}, "That personality isn't in the list."),
        ({"format": "one_host"}, NO_SEAT),
    ],
    ids=["unknown-slot", "unknown-personality", "no-seat"],
)
def test_a_bad_guest_request_is_a_422(harness, body, message):
    series_id = _series_id(harness)

    response = _guest(harness, series_id, **body)

    assert response.status_code == 422
    if message is not None:
        assert response.json()["detail"].startswith(message)


def test_a_guest_with_the_present_hosts_personality_is_refused_plainly(harness):
    lead = _series(harness)["hosts"][0]
    series_id = harness.listing()["series"]["series_id"]

    response = _guest(harness, series_id, personality_id=lead["personality_id"])

    assert response.status_code == 422
    assert response.json()["detail"] == (
        f"{lead['name']} already has that personality. Pick another one."
    )
