"""011 T094: a series' usual settings across episodes (FR-014–FR-019, SC-006)."""

import pytest

from tests.support.podcast_harness import EPISODES, podcast_harness

SERIES = "/api/podcasts/series"
PRESENTED = {"style": "presented", "line_length": "long", "invite_frequency": "rarely"}
TOPIC = {"topic": {"conversation_language": "el sueño", "english": "Sleep"}, "about_learner": []}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _usual(harness, series_id: int) -> dict:
    return harness.client.get(f"{SERIES}/{series_id}").json()["usual_settings"]


def _start(harness, format: str = "one_host", length: str = "short", **body) -> dict:
    payload = {"show": harness.listing(), "format": format, "length": length, **body}
    response = harness.client.post(EPISODES, json={**payload, "kind": "series"})
    assert response.status_code == 201, response.text
    return response.json()


def _first(harness, **body) -> int:
    return _start(harness, **body)["series"]["series_id"]


def test_episode_1_sets_the_usual_settings(harness):
    series_id = _first(harness, format="panel", length="long", settings={"style": "presented"})

    usual = _usual(harness, series_id)

    assert (usual["format"], usual["length"], usual["style"]) == ("panel", "long", "presented")


def test_a_just_this_episode_change_leaves_the_usual_settings(harness):
    series_id = _first(harness)

    episode = _start(harness, settings={"style": "presented"})

    assert episode["settings"]["style"] == "presented"
    assert _usual(harness, series_id)["style"] == "balanced"
    assert _start(harness)["settings"]["style"] == "balanced"


def test_a_from_now_on_change_reaches_the_next_two_setups(harness):
    series_id = _first(harness)

    _start(harness, settings={"style": "presented"}, from_now_on=["style"])

    assert _usual(harness, series_id)["style"] == "presented"
    _start(harness, settings={"style": "presented"})
    assert _usual(harness, series_id)["style"] == "presented"


def test_one_start_can_mix_both_scopes(harness):
    series_id = _first(harness)

    _start(harness, format="panel", settings=PRESENTED, from_now_on=["line_length"])

    usual = _usual(harness, series_id)
    assert (usual["format"], usual["style"], usual["line_length"]) == (
        "one_host",
        "balanced",
        "long",
    )


def test_an_abandoned_just_this_episode_episode_leaves_the_usual_settings(harness):
    series_id = _first(harness)
    episode = _start(harness, settings=PRESENTED)

    harness.stream(episode["conversation_id"], "next")

    assert _usual(harness, series_id)["style"] == "balanced"


def test_a_setup_left_without_starting_changes_nothing(harness):
    series_id = _first(harness)
    before = harness.client.get(f"{SERIES}/{series_id}").json()

    harness.client.post(f"{SERIES}/{series_id}/memory")

    assert harness.client.get(f"{SERIES}/{series_id}").json()["usual_settings"] == (
        before["usual_settings"]
    )


def test_scoped_episodes_count_and_remember_as_any_series_episode(harness):
    """FR-018: the count, the numbers and the memory are untouched by the scopes."""
    first = _start(harness, learner_name="Sam")
    harness.stream(first["conversation_id"], "next")
    harness.say(first["conversation_id"], "Odio las mañanas.")
    harness.memory.queue(TOPIC)
    series_id = first["series"]["series_id"]
    harness.client.post(f"{SERIES}/{series_id}/memory")

    second = _start(harness, settings=PRESENTED, from_now_on=["style"])
    third = _start(harness, format="panel")

    assert [second["series"]["episode_number"], third["series"]["episode_number"]] == [2, 3]
    stored = harness.podcasts.get_episode(third["conversation_id"]).series.snapshot
    assert [line.text for line in stored.topics_covered] == ["el sueño"]


def test_the_reset_returns_standard_settings_and_leaves_past_episodes(harness):
    series_id = _first(harness, settings=PRESENTED)
    past = _start(harness, settings=PRESENTED, from_now_on=["style"])

    harness.client.delete(f"{SERIES}/{series_id}/settings")

    assert _usual(harness, series_id)["style"] == "balanced"
    assert harness.episode(past["conversation_id"])["settings"]["style"] == "presented"


def test_each_language_keeps_its_own_series_settings(harness):
    spanish = _first(harness, settings={"style": "presented"})
    harness.client.put("/api/settings", json={"target_language": "de"})

    german = _first(harness, settings={"style": "conversation"})

    assert spanish != german
    assert _usual(harness, german)["style"] == "conversation"
    harness.client.put("/api/settings", json={"target_language": "es"})
    assert _usual(harness, spanish)["style"] == "presented"
