"""Integration tests for GET /api/audio/tts/{message_id}."""

import datetime
import struct
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_app_settings, get_storage
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session
from tests.support.fake_speech import override_speech

_DEFAULT_SETTINGS = AppSettingsRecord(
    llm_model="llama3.1",
    target_language="es",
    native_language="en",
    suggestion_count=3,
    whisper_model="base",
    updated_at=datetime.datetime.now(datetime.UTC),
)


def _write_minimal_wav(path: Path) -> None:
    """Write a minimal valid WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<I", 16000))
        f.write(struct.pack("<I", 32000))
        f.write(struct.pack("<H", 2))
        f.write(struct.pack("<H", 16))
        f.write(b"data")
        f.write(struct.pack("<I", 0))


@pytest.fixture
def setup(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "test.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)

    app.dependency_overrides[get_storage] = lambda: storage_instance
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS
    stub_tts = override_speech(app)

    with TestClient(app) as client:
        yield client, storage_instance, stub_tts, tmp_path

    app.dependency_overrides.clear()
    session.close()


def _create_message_with_tts(storage: SQLiteStorageProvider, audio_path: str | None) -> int:
    conv = storage.create_conversation(
        scenario_id="buy-train-ticket",
        scenario_title="Buy a Train Ticket",
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
    )
    msg = storage.save_message(conv.id, "assistant", "Hola, ¿cómo puedo ayudarte?")
    if audio_path is not None:
        storage.set_tts_path(msg.id, audio_path)
        return msg.id
    return msg.id


def test_get_tts_returns_wav_when_path_is_set(setup, tmp_path: Path) -> None:
    client, storage, _tts, tmp_path = setup
    wav_path = tmp_path / "existing.wav"
    _write_minimal_wav(wav_path)

    msg_id = _create_message_with_tts(storage, str(wav_path))

    response = client.get(f"/api/audio/tts/{msg_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_get_tts_synthesizes_when_no_path_set(setup, tmp_path: Path) -> None:
    client, storage, stub_tts, tmp_path = setup
    msg_id = _create_message_with_tts(storage, audio_path=None)

    response = client.get(f"/api/audio/tts/{msg_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0
    # TTS should have been called
    assert len(stub_tts.synthesized) == 1
    assert stub_tts.synthesized[0][1] == "Hola, ¿cómo puedo ayudarte?"


def test_get_tts_synthesizes_when_path_set_but_file_missing(setup, tmp_path: Path) -> None:
    client, storage, stub_tts, tmp_path = setup
    missing_path = tmp_path / "missing.wav"
    # Do NOT create the file
    msg_id = _create_message_with_tts(storage, str(missing_path))

    response = client.get(f"/api/audio/tts/{msg_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(stub_tts.synthesized) == 1


def test_get_tts_returns_404_for_unknown_message(setup) -> None:
    client, _storage, _tts, _tmp = setup
    response = client.get("/api/audio/tts/99999")
    assert response.status_code == 404
    assert "detail" in response.json()


# --- 006: speech in the conversation's own language (T045) ------------------------------

GERMAN_VOICE_MISSING = {"es_ES-davefx-medium", "es_AR-daniela-high"}


@pytest.fixture
def speech_setup(tmp_path: Path, monkeypatch):
    """Returns a builder: `speech_setup(voice_choices=…, installed=…)` → (client, storage, tts)."""
    session, _engine = make_test_session(str(tmp_path / "speech.db"))
    storage_instance = SQLiteStorageProvider(session)
    app.dependency_overrides[get_storage] = lambda: storage_instance
    clients: list[TestClient] = []

    def build(target_language: str = "es", voice_choices=None, installed=None):
        settings = replace(_DEFAULT_SETTINGS, target_language=target_language)
        app.dependency_overrides[get_app_settings] = lambda: settings
        builder = override_speech(app, voice_choices=voice_choices, installed=installed)
        clients.append(TestClient(app))
        return clients[-1].__enter__(), storage_instance, builder

    yield build
    for client in clients:
        client.__exit__(None, None, None)
    app.dependency_overrides.clear()
    session.close()


def _message_in(storage: SQLiteStorageProvider, language: str, text: str) -> int:
    conversation = storage.create_conversation("s", "S", language, "en", "llama3.1")
    return storage.save_message(conversation.id, "assistant", text).id


def _assert_voices_speak_their_text(builder, language: str) -> None:
    """FR-018: no text is ever spoken with another language's voice."""
    assert builder.voice_keys, "nothing was synthesised"
    assert all(voice.split("_")[0] == language for voice in builder.voice_keys)


def test_a_german_message_is_spoken_in_german_while_spanish_is_selected(speech_setup) -> None:
    client, storage, builder = speech_setup(target_language="es")
    message_id = _message_in(storage, "de", "Guten Tag, was darf es sein?")

    response = client.get(f"/api/audio/tts/{message_id}")

    assert response.status_code == 200
    assert builder.synthesized[0][:2] == ("de_DE-thorsten-medium", "Guten Tag, was darf es sein?")
    _assert_voices_speak_their_text(builder, "de")


def test_a_spanish_message_uses_the_learners_spanish_choice(speech_setup) -> None:
    client, storage, builder = speech_setup(
        target_language="de", voice_choices={"es": "es_AR-daniela-high"}
    )
    message_id = _message_in(storage, "es", "Hola")

    assert client.get(f"/api/audio/tts/{message_id}").status_code == 200
    assert builder.voice_keys == ["es_AR-daniela-high"]


def test_an_uninstalled_german_voice_is_503_and_nothing_is_spoken(speech_setup) -> None:
    from app.practice_languages import voice_unavailable_message

    client, storage, builder = speech_setup(installed=GERMAN_VOICE_MISSING)
    message_id = _message_in(storage, "de", "Guten Tag")

    response = client.get(f"/api/audio/tts/{message_id}")

    assert (response.status_code, response.json()) == (
        503,
        {"detail": voice_unavailable_message("de")},
    )
    assert builder.synthesized == []


def test_a_cached_wav_is_served_without_a_voice_check(speech_setup, tmp_path: Path) -> None:
    client, storage, builder = speech_setup(installed=set())
    cached = tmp_path / "cached.wav"
    _write_minimal_wav(cached)
    message_id = _message_in(storage, "de", "Guten Tag")
    storage.set_tts_path(message_id, str(cached))

    response = client.get(f"/api/audio/tts/{message_id}")

    assert response.status_code == 200
    assert builder.synthesized == []


# --- 006 US4: the chosen German voice is the one that speaks (T095) ---------------------


@pytest.fixture
def stored_settings_client(tmp_path: Path):
    """Settings read from storage, as in production, so a PUT reaches the next request."""
    from app.database import get_db

    session, _engine = make_test_session(str(tmp_path / "voices.db"))
    app.dependency_overrides[get_db] = lambda: session
    builder = override_speech(app)
    with TestClient(app) as client:
        yield client, SQLiteStorageProvider(session), builder
    app.dependency_overrides.clear()
    session.close()


def test_the_chosen_german_voice_speaks_the_next_message_and_words(stored_settings_client):
    client, storage, builder = stored_settings_client
    saved = client.put(
        "/api/settings", json={"target_language": "de", "tts_voice": "de_DE-kerstin-low"}
    )
    message_id = _message_in(storage, "de", "Guten Tag")
    word_id = storage.save_vocabulary_item("Haus", "house", "de", "en").id

    assert saved.status_code == 200
    assert client.get(f"/api/audio/tts/{message_id}").status_code == 200
    assert client.get(f"/api/flashcards/tts/{word_id}").status_code == 200
    assert builder.voice_keys == ["de_DE-kerstin-low", "de_DE-kerstin-low"]


# --- 007: a host line is spoken in its host's voice (T014, contracts §11) --------------

HOST_VOICE = "es_AR-daniela-high"
HOST_UNAVAILABLE = "Lucía's voice isn't installed."


class FakeMessageVoices:
    """A `MessageVoiceLookup` answering from a fixed {message_id: voice_key} map."""

    def __init__(self, voices: dict[int, str]) -> None:
        self._voices = voices

    def voice_for_message(self, message_id: int) -> str | None:
        return self._voices.get(message_id)

    def unavailable_message(self, message_id: int) -> str:
        return HOST_UNAVAILABLE


@pytest.fixture
def host_voice_setup(speech_setup):
    """(client, storage, builder, voices): `voices` maps a message id to its host's voice."""
    from app.services.factory import get_message_voices

    def build(installed=None):
        voices: dict[int, str] = {}
        app.dependency_overrides[get_message_voices] = lambda: FakeMessageVoices(voices)
        client, storage, builder = speech_setup(installed=installed)
        return client, storage, builder, voices

    return build


def test_a_host_line_is_spoken_in_its_hosts_voice(host_voice_setup) -> None:
    client, storage, builder, voices = host_voice_setup()
    message_id = _message_in(storage, "es", "¡Bienvenidos al programa!")
    voices[message_id] = HOST_VOICE

    response = client.get(f"/api/audio/tts/{message_id}")

    assert response.status_code == 200
    assert builder.voice_keys == [HOST_VOICE]


def test_a_message_without_a_host_keeps_the_conversations_voice(host_voice_setup) -> None:
    client, storage, builder, _voices = host_voice_setup()
    message_id = _message_in(storage, "es", "Hola")

    assert client.get(f"/api/audio/tts/{message_id}").status_code == 200
    assert builder.voice_keys == ["es_ES-davefx-medium"]


def test_a_missing_host_voice_is_503_with_the_hosts_message(host_voice_setup) -> None:
    client, storage, builder, voices = host_voice_setup(installed={"es_ES-davefx-medium"})
    message_id = _message_in(storage, "es", "¡Hola!")
    voices[message_id] = HOST_VOICE

    response = client.get(f"/api/audio/tts/{message_id}")

    assert (response.status_code, response.json()) == (503, {"detail": HOST_UNAVAILABLE})
    assert builder.synthesized == []
