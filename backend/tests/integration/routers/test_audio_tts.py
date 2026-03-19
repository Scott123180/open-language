"""Integration tests for GET /api/audio/tts/{message_id}."""
import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_app_settings, get_storage, get_tts
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from app.services.tts.base import TTSProvider
from tests.integration.conftest import make_test_session

import datetime

_DEFAULT_SETTINGS = AppSettingsRecord(
    llm_model="llama3.1",
    target_language="es",
    native_language="en",
    tts_voice="es_ES-mls-medium",
    suggestion_count=3,
    updated_at=datetime.datetime.now(datetime.timezone.utc),
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


class StubTTSProvider(TTSProvider):
    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path
        self.synthesize_calls: list[tuple[str, Path]] = []

    @property
    def voice_name(self) -> str:
        return "stub-voice"

    def synthesize(self, text: str, output_path: Path) -> None:
        self.synthesize_calls.append((text, output_path))
        _write_minimal_wav(output_path)


@pytest.fixture
def setup(tmp_path: Path):
    db_file = tmp_path / "test.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)
    stub_tts = StubTTSProvider(tmp_path=tmp_path)

    app.dependency_overrides[get_storage] = lambda: storage_instance
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS
    app.dependency_overrides[get_tts] = lambda: stub_tts

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
    assert len(stub_tts.synthesize_calls) == 1
    assert stub_tts.synthesize_calls[0][0] == "Hola, ¿cómo puedo ayudarte?"


def test_get_tts_synthesizes_when_path_set_but_file_missing(setup, tmp_path: Path) -> None:
    client, storage, stub_tts, tmp_path = setup
    missing_path = tmp_path / "missing.wav"
    # Do NOT create the file
    msg_id = _create_message_with_tts(storage, str(missing_path))

    response = client.get(f"/api/audio/tts/{msg_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(stub_tts.synthesize_calls) == 1


def test_get_tts_returns_404_for_unknown_message(setup) -> None:
    client, _storage, _tts, _tmp = setup
    response = client.get("/api/audio/tts/99999")
    assert response.status_code == 404
    assert "detail" in response.json()
