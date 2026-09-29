"""T040: GET /api/podcasts/catalog (contracts §1)."""

import pytest

from app.podcasts.catalog import PERSONALITIES
from app.practice_languages import host_names_for
from app.services.tts.voices import AVAILABLE_VOICES
from tests.support.podcast_harness import podcast_harness

FORMAT_KEYS = {"format_id", "label", "host_count", "is_learner_speaking", "description"}
LENGTH_KEYS = {"length_id", "label", "target_host_lines", "is_default"}
PERSONALITY_KEYS = {"personality_id", "label", "description"}
SHOW_KEYS = {"source", "show_id", "title", "premise", "topic", "learner_role", "language", "hosts"}
HOST_KEYS = {"slot", "name", "personality_id", "voice_key", "show_role", "angle"}
GENDER = {voice.key: voice.gender for voice in AVAILABLE_VOICES}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


@pytest.fixture
def catalog(harness) -> dict:
    response = harness.client.get("/api/podcasts/catalog")
    assert response.status_code == 200
    return response.json()


def test_the_catalogue_is_for_the_current_practice_language(catalog):
    assert (catalog["language"], catalog["language_name"]) == ("es", "Spanish")


def test_the_formats_come_in_catalogue_order_with_their_fields(catalog):
    assert [f["format_id"] for f in catalog["formats"]] == ["one_host", "panel", "listen"]
    assert all(set(f) == FORMAT_KEYS for f in catalog["formats"])


def test_the_lengths_come_in_order_with_medium_the_default(catalog):
    assert [(length["length_id"], length["is_default"]) for length in catalog["lengths"]] == [
        ("short", False),
        ("medium", True),
        ("long", False),
    ]
    assert all(set(length) == LENGTH_KEYS for length in catalog["lengths"])


def test_the_personalities_come_in_catalogue_order(catalog):
    assert [p["personality_id"] for p in catalog["personalities"]] == list(PERSONALITIES)
    assert all(set(p) == PERSONALITY_KEYS for p in catalog["personalities"])


def test_there_are_at_least_six_ready_made_shows(catalog):
    assert len(catalog["shows"]) >= 6
    assert all(set(show) == SHOW_KEYS for show in catalog["shows"])
    assert all(show["source"] == "ready_made" for show in catalog["shows"])


def test_every_show_has_two_distinct_hosts_in_the_practice_language(catalog):
    for show in catalog["shows"]:
        lead, second = show["hosts"]
        assert show["language"] == "es"
        assert set(lead) == set(second) == HOST_KEYS
        assert (lead["slot"], second["slot"]) == ("lead", "second")
        assert lead["name"] != second["name"]
        assert lead["personality_id"] != second["personality_id"]
        assert lead["voice_key"] != second["voice_key"]


def test_the_voices_are_described(catalog):
    assert catalog["voices"]["installed_count"] == 2


def test_german_practice_gives_german_names(harness):
    harness.client.put("/api/settings", json={"target_language": "de"})

    catalog = harness.client.get("/api/podcasts/catalog").json()

    assert catalog["language"] == "de"
    for host in (host for show in catalog["shows"] for host in show["hosts"]):
        assert host["name"] in host_names_for("de", GENDER[host["voice_key"]])
