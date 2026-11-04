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


# --- 011 T118: a guest in a regular host's place (FR-020–FR-023, R10, R11) ----------------

TOPIC = {
    "topic": {"conversation_language": "las tostadas", "english": "Toast"},
    "about_learner": [],
}


def _guest_for(harness, series_id: int, slot: str, format: str) -> dict:
    body = {"language": "es", "slot": slot, "format": format, "learner_name": "Sam"}
    response = harness.client.post(f"{SERIES}/{series_id}/guest", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _start_with_guest(harness, guest: dict, format: str = "panel") -> dict:
    payload = {"show": harness.listing(), "format": format, "length": "short", "kind": "series"}
    response = harness.client.post(
        EPISODES, json={**payload, "guest": guest, "learner_name": "Sam"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _panel_series(harness) -> tuple[int, dict]:
    first = harness.start_series("panel", learner_name="Sam")
    second = next(host for host in first["hosts"] if host["slot"] == "second")
    return first["series"]["series_id"], second


def _remember_topic(harness, episode: dict) -> None:
    harness.stream(episode["conversation_id"], "next")
    harness.say(episode["conversation_id"], "Me encantan las tostadas.")
    harness.memory.queue(TOPIC)
    harness.client.post(f"{SERIES}/{episode['series']['series_id']}/memory")


def test_a_panel_guest_is_introduced_for_today_and_the_regular_host_is_away(harness):
    series_id, regular = _panel_series(harness)
    guest = _guest_for(harness, series_id, "second", "panel")
    episode = _start_with_guest(harness, guest)

    harness.stream(episode["conversation_id"], "next")

    standing, turns = harness.writer.received[-1]
    assert f"- {guest['name']} is today's guest" in standing
    assert f"- {regular['name']} is away today and back next time." in standing
    assert f"in for {regular['name']}, who is away today" in turns[-1].content
    assert episode["away_host_name"] == regular["name"]


def test_the_next_episode_has_the_regular_host_back_with_the_guest_episode_marked(harness):
    series_id, regular = _panel_series(harness)
    guest_episode = _start_with_guest(harness, _guest_for(harness, series_id, "second", "panel"))
    _remember_topic(harness, guest_episode)

    after = harness.start_series("panel")

    back = next(host for host in after["hosts"] if host["slot"] == "second")
    assert {k: back[k] for k in ("name", "personality_id", "voice_key")} == {
        k: regular[k] for k in ("name", "personality_id", "voice_key")
    }
    assert not any(host["is_guest"] for host in after["hosts"])
    snapshot = harness.podcasts.get_episode(after["conversation_id"]).series.snapshot
    assert [(line.text, line.missed_by) for line in snapshot.topics_covered] == [
        ("las tostadas", ("second",))
    ]


def test_the_count_and_the_memory_include_the_guest_episode(harness):
    series_id, _regular = _panel_series(harness)
    guest_episode = _start_with_guest(harness, _guest_for(harness, series_id, "second", "panel"))
    _remember_topic(harness, guest_episode)

    detail = harness.client.get(f"{SERIES}/{series_id}").json()

    assert detail["episode_count"] == 2
    assert [point["text"] for point in detail["remembered"]["topics"]] == ["Toast"]


def test_a_one_host_series_lead_guest_stands_in_for_the_one_host(harness):
    first = _one_host_series(harness)
    lead = first["hosts"][0]
    guest = _guest_for(harness, first["series"]["series_id"], "lead", "one_host")

    episode = _start_with_guest(harness, guest, format="one_host")

    assert [(host["name"], host["is_guest"]) for host in episode["hosts"]] == [
        (guest["name"], True)
    ]
    assert episode["away_host_name"] == lead["name"]
    harness.stream(episode["conversation_id"], "next")
    assert f"standing in for {lead['name']}" in harness.writer.received[-1][1][-1].content


def test_a_guest_whose_voice_is_missing_speaks_as_text_only(tmp_path):
    with podcast_harness(tmp_path, installed={"es_ES-davefx-medium"}) as harness:
        series_id, _regular = _panel_series(harness)
        guest = {
            **_guest_for(harness, series_id, "second", "panel"),
            "voice_key": "es_AR-daniela-high",
        }

        episode = _start_with_guest(harness, guest)

    seated = next(host for host in episode["hosts"] if host["is_guest"])
    assert seated["is_voice_available"] is False
    assert seated["voice_unavailable_message"]
