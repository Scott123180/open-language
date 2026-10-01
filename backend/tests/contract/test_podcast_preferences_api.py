"""T041: GET and PUT /api/podcasts/preferences (contracts §2)."""

import pytest

from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from tests.support.podcast_harness import podcast_harness

PREFERENCES = "/api/podcasts/preferences"
DEFAULTS = {
    "last_format": "one_host",
    "is_show_text_on": False,
    "interests": [],
    "learner_name": None,
}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def test_the_defaults_are_served_first(harness):
    assert harness.client.get(PREFERENCES).json() == DEFAULTS


def test_the_learner_name_is_stored(harness):
    response = harness.client.put(PREFERENCES, json={"learner_name": "  Sam "})

    assert response.status_code == 200
    assert response.json()["learner_name"] == "Sam"
    assert harness.client.get(PREFERENCES).json()["learner_name"] == "Sam"


def test_an_empty_learner_name_clears_it(harness):
    harness.client.put(PREFERENCES, json={"learner_name": "Sam"})

    response = harness.client.put(PREFERENCES, json={"learner_name": ""})

    assert response.json()["learner_name"] is None


def test_a_name_over_forty_characters_is_refused(harness):
    response = harness.client.put(PREFERENCES, json={"learner_name": "x" * 41})

    assert response.status_code == 422


def test_the_last_format_is_read_only(harness):
    response = harness.client.put(PREFERENCES, json={"last_format": "panel"})

    assert response.status_code == 200
    assert response.json()["last_format"] == "one_host"


def test_a_field_left_out_is_unchanged(harness):
    harness.client.put(PREFERENCES, json={"learner_name": "Sam"})

    harness.client.put(PREFERENCES, json={"is_show_text_on": True})

    assert harness.client.get(PREFERENCES).json()["learner_name"] == "Sam"


def test_values_persist_across_a_new_session(harness):
    harness.client.put(PREFERENCES, json={"learner_name": "Sam"})

    stored = SQLitePodcastStorage(harness.session()).get_preferences()

    assert stored.learner_name == "Sam"


def test_interests_are_trimmed_and_deduplicated_ignoring_case(harness):
    body = {"interests": [" football ", "Cooking", "FOOTBALL", "", "cooking "]}

    response = harness.client.put(PREFERENCES, json=body)

    assert response.status_code == 200
    assert response.json()["interests"] == ["football", "Cooking"]


def test_more_than_ten_interests_are_refused_naming_the_limit(harness):
    body = {"interests": [f"topic {n}" for n in range(11)]}

    response = harness.client.put(PREFERENCES, json=body)

    assert response.status_code == 422
    assert "10" in str(response.json()["detail"])


def test_ten_interests_are_accepted(harness):
    body = {"interests": [f"topic {n}" for n in range(10)]}

    assert harness.client.put(PREFERENCES, json=body).status_code == 200


def test_an_interest_over_forty_characters_is_refused_naming_it(harness):
    long_interest = "x" * 41

    response = harness.client.put(PREFERENCES, json={"interests": [long_interest]})

    assert response.status_code == 422
    assert long_interest in str(response.json()["detail"])


def test_an_empty_list_clears_the_interests(harness):
    harness.client.put(PREFERENCES, json={"interests": ["football"]})

    response = harness.client.put(PREFERENCES, json={"interests": []})

    assert response.json()["interests"] == []
