"""T020: every language-model dependency is served by the provider registry."""

from datetime import UTC, datetime

import pytest

from app.services import factory
from app.services.llm.selection_types import LLMSelection
from app.services.storage.base import AppSettingsRecord

_RECORD = AppSettingsRecord(
    llm_model="haiku",
    target_language="es",
    native_language="en",
    suggestion_count=1,
    whisper_model="base",
    updated_at=datetime.now(UTC),
    llm_provider="claude",
    llm_effort="medium",
)


@pytest.fixture()
def registry_calls(monkeypatch) -> list[tuple]:
    calls: list[tuple] = []
    built = object()

    def fake_build(selection, settings, effort):
        calls.append((selection, settings, effort))
        return built

    monkeypatch.setattr(factory, "build_llm_provider", fake_build)
    return calls


@pytest.mark.parametrize("dependency", ["get_llm", "get_structured_llm", "get_session_provider"])
def test_dependency_delegates_to_the_registry(registry_calls, dependency):
    getattr(factory, dependency)(_RECORD)

    [(selection, settings, effort)] = registry_calls
    assert selection == LLMSelection("claude", "haiku")
    assert effort == "medium"
    assert settings is factory.get_settings()


# --- 006: speech for a language (T033) ------------------------------------------------


def test_speech_for_language_resolves_the_remembered_german_voice():
    from dataclasses import replace

    from tests.support.fake_speech import FakeVoiceInstallation

    record = replace(_RECORD, voice_choices={"de": "de_DE-kerstin-low"})

    speech = factory.get_speech_for_language(record, FakeVoiceInstallation())

    assert speech.voice_key("de") == "de_DE-kerstin-low"
    assert speech.voice_key("es") == "es_ES-davefx-medium"


def test_speech_for_language_builds_piper_for_the_resolved_voice():
    from tests.support.fake_speech import FakeVoiceInstallation

    provider = factory.get_speech_for_language(_RECORD, FakeVoiceInstallation()).provider_for("de")

    assert provider.voice_name == "de_DE-thorsten-medium"


def test_voice_installation_looks_in_the_configured_voice_directory():
    from app.services.tts.piper import PiperVoiceInstallation

    installation = factory.get_voice_installation()

    assert isinstance(installation, PiperVoiceInstallation)
    assert installation.voice_dir == factory.get_settings().voice_dir


# --- 007: podcast wiring (T030, T036) --------------------------------------------------


def test_podcast_storage_is_the_sqlite_storage(tmp_path):
    from app.podcasts.services.storage import PodcastStorage
    from tests.support.scratch_database import make_session

    storage = factory.get_podcast_storage(make_session(tmp_path / "factory.db"))

    assert isinstance(storage, PodcastStorage)


def test_message_voices_are_the_podcast_host_voices(tmp_path):
    from app.podcasts import PodcastMessageVoices
    from app.services.storage.sqlite import SQLiteStorageProvider
    from app.services.tts.base import MessageVoiceLookup
    from tests.support.scratch_database import make_session

    session = make_session(tmp_path / "voices.db")
    storage = factory.get_podcast_storage(session)

    voices = factory.get_message_voices(storage, SQLiteStorageProvider(session))

    assert isinstance(voices, MessageVoiceLookup)
    assert isinstance(voices, PodcastMessageVoices)


def test_episode_locks_are_one_per_process():
    from app.podcasts.services.episode_lock import EpisodeLocks

    assert isinstance(factory.get_episode_locks(), EpisodeLocks)
    assert factory.get_episode_locks() is factory.get_episode_locks()


def test_the_host_caster_casts_from_the_installed_voices():
    from app.podcasts.services.casting import HostCaster
    from tests.support.fake_speech import FakeVoiceInstallation

    assert isinstance(factory.get_host_caster(FakeVoiceInstallation()), HostCaster)
