"""T032: the shared speech test double keeps production voice resolution under test."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.services.factory import get_speech_for_language, get_voice_installation
from app.services.storage.base import AppSettingsRecord
from app.services.tts.base import VoiceUnavailable
from tests.support.fake_speech import FakeVoiceInstallation, RecordingTtsBuilder, override_speech


def _settings(voice_choices: dict[str, str]) -> AppSettingsRecord:
    return AppSettingsRecord(
        llm_model="llama3.1:8b",
        target_language="es",
        native_language="en",
        suggestion_count=1,
        whisper_model="base",
        updated_at=datetime.now(UTC),
        voice_choices=voice_choices,
    )


def _speech(app: FastAPI, stored_choices: dict[str, str] | None = None):
    installation = app.dependency_overrides[get_voice_installation]()
    return app.dependency_overrides[get_speech_for_language](
        app_settings=_settings(stored_choices or {}), installation=installation
    )


def test_every_voice_is_installed_by_default():
    assert FakeVoiceInstallation().is_installed("anything") is True


def test_only_the_listed_voices_are_installed():
    installation = FakeVoiceInstallation({"de_DE-kerstin-low"})

    assert installation.is_installed("de_DE-kerstin-low") is True
    assert installation.is_installed("de_DE-thorsten-medium") is False


def test_the_override_resolves_the_german_default():
    app = FastAPI()
    override_speech(app)

    assert _speech(app).voice_key("de") == "de_DE-thorsten-medium"


def test_the_override_uses_the_given_voice_choices():
    app = FastAPI()
    override_speech(app, voice_choices={"de": "de_DE-kerstin-low"})

    assert _speech(app).voice_key("de") == "de_DE-kerstin-low"


def test_without_voice_choices_the_override_reads_the_stored_settings():
    app = FastAPI()
    override_speech(app)

    assert _speech(app, {"de": "de_DE-kerstin-low"}).voice_key("de") == "de_DE-kerstin-low"


def test_the_override_records_each_synthesis(tmp_path: Path):
    app = FastAPI()
    builder = override_speech(app)
    output = tmp_path / "out.wav"

    _speech(app).provider_for("de").synthesize("Guten Tag", output)

    assert builder.synthesized == [("de_DE-thorsten-medium", "Guten Tag", output)]
    assert builder.voice_keys == ["de_DE-thorsten-medium"]
    assert output.read_bytes().startswith(b"RIFF")


def test_a_voice_left_out_of_installed_is_unavailable():
    app = FastAPI()
    override_speech(app, installed={"es_ES-davefx-medium"})

    with pytest.raises(VoiceUnavailable, match="German voice isn't installed"):
        _speech(app).provider_for("de")


def test_the_builder_is_a_recording_tts_builder():
    assert isinstance(override_speech(FastAPI()), RecordingTtsBuilder)
