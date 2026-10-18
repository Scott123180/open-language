"""010 T040: a series across episodes, formats, languages and settings (SC-001, US1, edge cases)."""

import pytest

from app.models.conversation import Conversation
from app.podcasts.catalog import LEAD_SLOT, PODCAST_FORMATS
from app.practice_languages import host_names_for
from app.services.tts.voices import AVAILABLE_VOICES
from tests.support.fake_speech import override_speech
from tests.support.podcast_harness import podcast_harness

FORMATS = [
    "one_host",
    "panel",
    "listen",
    "one_host",
    "panel",
    "one_host",
    "listen",
    "panel",
    "one_host",
    "panel",
]
GENDER = {voice.key: voice.gender for voice in AVAILABLE_VOICES}
SPANISH_VOICES = {voice.key for voice in AVAILABLE_VOICES if voice.language == "es"}


@pytest.fixture
def harness(tmp_path):
    with podcast_harness(tmp_path) as podcast:
        yield podcast


def _stored_hosts(harness, conversation_id: int) -> list[tuple]:
    hosts = harness.podcasts.get_hosts(conversation_id)
    return [(h.slot, h.name, h.personality_id, h.voice_key) for h in hosts]


def _series_hosts(harness, series_id: int) -> list[tuple]:
    series = harness.series_storage.get(series_id)
    return [(h.slot, h.name, h.personality_id, h.voice_key) for h in series.hosts]


def _set(harness, **settings) -> None:
    harness.conversations.update_settings(**settings)


def test_every_episode_of_ten_uses_the_series_hosts_for_its_format(harness):
    numbers, series_id = [], None
    for format in FORMATS:
        episode = harness.start_series(format)
        series_id = episode["series"]["series_id"]
        numbers.append(episode["series"]["episode_number"])
        count = PODCAST_FORMATS[format].host_count
        expected = _series_hosts(harness, series_id)[:count]
        assert _stored_hosts(harness, episode["conversation_id"]) == expected

    assert numbers == list(range(1, 11))
    assert [slot for slot, *_rest in _series_hosts(harness, series_id)] == [LEAD_SLOT, "second"]


def test_the_same_show_in_german_is_its_own_series(harness):
    spanish = harness.start_series("panel")
    spanish_hosts = _series_hosts(harness, spanish["series"]["series_id"])

    _set(harness, target_language="de")
    german = harness.start_series("panel")

    assert german["series"]["episode_number"] == 1
    assert german["series"]["series_id"] != spanish["series"]["series_id"]
    for _slot, name, _personality, voice in _series_hosts(harness, german["series"]["series_id"]):
        assert name in host_names_for("de", GENDER[voice])
    assert _series_hosts(harness, spanish["series"]["series_id"]) == spanish_hosts


def test_an_unfinished_episode_stays_resumable_while_the_next_one_counts(harness):
    first = harness.start_series()

    assert (
        harness.listing()["series"]["unfinished_episode"]["conversation_id"]
        == first["conversation_id"]
    )
    second = harness.start_series()

    assert second["series"]["episode_number"] == 2
    assert harness.episode(first["conversation_id"])["status"] == "active"
    assert harness.listing()["series"]["episode_count"] == 2


def test_an_abandoned_episode_with_two_lines_counts(harness):
    first = harness.start_series(learner_name="Sam")
    harness.stream(first["conversation_id"], "next")
    harness.say(first["conversation_id"], "Hola, Hugo.")

    assert harness.start_series()["series"]["episode_number"] == 2


def test_switching_the_provider_keeps_hosts_numbers_and_memory(harness):
    first = harness.start_series("panel", learner_name="Sam")
    harness.stream(first["conversation_id"], "next")
    harness.say(first["conversation_id"], "Odio las mañanas.")
    harness.memory.queue(
        {
            "topic": None,
            "about_learner": [
                {"conversation_language": "Odia las mañanas.", "english": "You hate mornings."}
            ],
        }
    )
    harness.client.post(f"/api/podcasts/series/{first['series']['series_id']}/memory")

    _set(harness, llm_provider="claude", llm_model="sonnet")
    second = harness.start_series("panel")

    assert second["series"]["episode_number"] == 2
    assert _stored_hosts(harness, second["conversation_id"]) == _stored_hosts(
        harness, first["conversation_id"]
    )
    detail = harness.client.get(f"/api/podcasts/series/{first['series']['series_id']}").json()
    assert [p["text"] for p in detail["remembered"]["about_learner"]] == ["You hate mornings."]


def test_deleting_an_episode_lowers_the_count_and_forgets_its_points(harness):
    first = harness.start_series(learner_name="Sam")
    harness.stream(first["conversation_id"], "next")
    harness.say(first["conversation_id"], "Odio las mañanas.")
    harness.memory.queue(
        {"topic": {"conversation_language": "el sueño", "english": "Sleep"}, "about_learner": []}
    )
    series_id = first["series"]["series_id"]
    harness.client.post(f"/api/podcasts/series/{series_id}/memory")
    harness.start_series()

    session = harness.session()
    session.query(Conversation).filter(Conversation.id == first["conversation_id"]).delete()
    session.commit()

    detail = harness.client.get(f"/api/podcasts/series/{series_id}").json()
    assert detail["episode_count"] == 1
    assert detail["remembered"]["topics"] == []


def test_a_host_whose_voice_went_missing_keeps_their_identity_and_runs_as_text(harness):
    first = harness.start_series("panel")
    lead_voice = first["hosts"][0]["voice_key"]
    override_speech(harness.client.app, installed=SPANISH_VOICES - {lead_voice})

    second = harness.start_series("panel")
    harness.stream(second["conversation_id"], "next")

    lead = next(
        h for h in harness.episode(second["conversation_id"])["hosts"] if h["slot"] == LEAD_SLOT
    )
    assert (lead["name"], lead["voice_key"]) == (first["hosts"][0]["name"], lead_voice)
    assert lead["is_voice_available"] is False
    assert lead["voice_unavailable_message"]


def test_a_series_cast_with_one_voice_starts_again_once_a_second_is_installed(tmp_path):
    with podcast_harness(tmp_path, installed={"es_ES-davefx-medium"}) as harness:
        first = harness.start_series("panel")
        assert len({host["voice_key"] for host in first["hosts"]}) == 1
        override_speech(harness.client.app, installed=None)

        second = harness.start_series("panel")

    assert second["series"]["episode_number"] == 2
    assert {host["voice_key"] for host in second["hosts"]} == {"es_ES-davefx-medium"}


def test_a_new_learner_name_reaches_the_next_episode(harness):
    harness.start_series(learner_name="Sam")

    second = harness.start_series(learner_name="Alex")
    harness.stream(second["conversation_id"], "next")

    standing_prompt, pending = harness.writer.received[-1]
    assert "Address the learner as Alex." in standing_prompt
    assert "Alex" in pending[-1].content and "Sam" not in pending[-1].content
