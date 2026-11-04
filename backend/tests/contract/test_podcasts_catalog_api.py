"""T040: GET /api/podcasts/catalog (contracts §1)."""

import pytest

from app.podcasts.catalog import PERSONALITIES, SHOW_TEMPLATES
from app.practice_languages import host_names_for
from app.services.tts.voices import AVAILABLE_VOICES
from tests.support.podcast_harness import podcast_harness

FORMAT_KEYS = {
    "format_id",
    "label",
    "host_count",
    "is_learner_speaking",
    "description",
    "has_jump_in",
    "has_pass",
}
LENGTH_KEYS = {"length_id", "label", "target_host_lines", "is_default"}
PERSONALITY_KEYS = {"personality_id", "label", "description"}
DRAFT_KEYS_007 = {
    "source",
    "show_id",
    "title",
    "premise",
    "topic",
    "learner_role",
    "language",
    "hosts",
}
LISTING_KEYS = {"saved_show_id", "is_favourite", "series"}
SHOW_KEYS = DRAFT_KEYS_007 | LISTING_KEYS
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


# --- 010: listings (contracts §1) ---------------------------------------------------------


def test_every_show_is_a_listing_with_no_learner_state_on_a_fresh_database(catalog):
    assert all(
        (show["saved_show_id"], show["is_favourite"], show["series"]) == (None, False, None)
        for show in catalog["shows"]
    )


def test_my_shows_is_empty_on_a_fresh_database(catalog):
    assert catalog["my_shows"] == []


def test_the_ready_made_shows_come_in_catalogue_order_on_every_call(harness, catalog):
    again = harness.client.get("/api/podcasts/catalog").json()

    assert [show["show_id"] for show in catalog["shows"]] == list(SHOW_TEMPLATES)
    assert again["shows"] == catalog["shows"]


def test_each_format_says_whether_the_learner_can_jump_in_and_pass(catalog):
    """011 T024 (research R15): Jump in in One host and Panel, Pass in Panel only."""
    flags = {f["format_id"]: (f["has_jump_in"], f["has_pass"]) for f in catalog["formats"]}

    assert flags == {"one_host": (True, False), "panel": (True, True), "listen": (False, False)}


def test_the_catalogue_offers_the_episode_settings(catalog):
    """011 T068 (contracts §1)."""
    options = catalog["episode_options"]

    assert options["styles"] == [
        {
            "style_id": "conversation",
            "label": "Conversation",
            "description": "Lots of back-and-forth.",
            "is_default": False,
        },
        {
            "style_id": "balanced",
            "label": "Balanced",
            "description": "Some talk, some explaining.",
            "is_default": True,
        },
        {
            "style_id": "presented",
            "label": "Presented",
            "description": "The hosts mostly explain and tell stories, like a radio show.",
            "is_default": False,
        },
    ]
    assert options["line_lengths"] == [
        {"line_length_id": "short", "label": "Short", "is_default": False},
        {"line_length_id": "medium", "label": "Medium", "is_default": True},
        {"line_length_id": "long", "label": "Long", "is_default": False},
    ]
    assert options["invite_frequencies"] == [
        {"invite_frequency_id": "often", "label": "Often", "is_default": False},
        {"invite_frequency_id": "sometimes", "label": "Sometimes", "is_default": True},
        {"invite_frequency_id": "rarely", "label": "Rarely", "is_default": False},
    ]
    assert options["learner_roles"] == [
        {"learner_role": "guest", "label": "Guest"},
        {"learner_role": "co_host", "label": "Co-host"},
        {"learner_role": "caller", "label": "Caller"},
    ]
    assert options["today_subject_max_length"] == 120
