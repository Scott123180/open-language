"""Integration tests for POST /api/audio/transcribe."""
import io
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_stt
from app.services.stt.base import STTProvider, TranscriptionResult


class StubSTTProvider(STTProvider):
    def transcribe(self, audio_path: Path, language_hint: str | None = None) -> TranscriptionResult:
        return TranscriptionResult(text="hola mundo", detected_language="es")


def _minimal_wav_bytes() -> bytes:
    """Return minimal valid WAV file bytes (44-byte header, no audio data)."""
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36))  # chunk size
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))   # PCM
    buf.write(struct.pack("<H", 1))   # mono
    buf.write(struct.pack("<I", 16000))
    buf.write(struct.pack("<I", 32000))
    buf.write(struct.pack("<H", 2))
    buf.write(struct.pack("<H", 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", 0))
    return buf.getvalue()


@pytest.fixture
def client_with_stub_stt():
    stub_stt = StubSTTProvider()
    app.dependency_overrides[get_stt] = lambda: stub_stt

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_transcribe_valid_wav_returns_200(client_with_stub_stt: TestClient):
    wav_bytes = _minimal_wav_bytes()

    # Patch convert_webm_to_wav to avoid needing ffmpeg
    fake_wav_path = Path("/tmp/fake_test_audio.wav")
    fake_wav_path.write_bytes(wav_bytes)

    try:
        with patch(
            "app.routers.audio.convert_webm_to_wav",
            return_value=fake_wav_path,
        ):
            response = client_with_stub_stt.post(
                "/api/audio/transcribe",
                files={"file": ("audio.webm", wav_bytes, "audio/webm")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "hola mundo"
        assert data["detected_language"] == "es"
    finally:
        fake_wav_path.unlink(missing_ok=True)


def test_transcribe_empty_bytes_returns_400(client_with_stub_stt: TestClient):
    response = client_with_stub_stt.post(
        "/api/audio/transcribe",
        files={"file": ("audio.webm", b"", "audio/webm")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_transcribe_response_has_text_field(client_with_stub_stt: TestClient):
    wav_bytes = _minimal_wav_bytes()
    fake_wav_path = Path("/tmp/fake_test_audio2.wav")
    fake_wav_path.write_bytes(wav_bytes)

    try:
        with patch(
            "app.routers.audio.convert_webm_to_wav",
            return_value=fake_wav_path,
        ):
            response = client_with_stub_stt.post(
                "/api/audio/transcribe",
                files={"file": ("audio.webm", wav_bytes, "audio/webm")},
            )

        assert "text" in response.json()
        assert "detected_language" in response.json()
    finally:
        fake_wav_path.unlink(missing_ok=True)


def test_transcribe_stt_error_returns_422(client_with_stub_stt: TestClient):
    from app.services.stt.base import STTError

    class FailingSTTProvider(STTProvider):
        def transcribe(self, audio_path: Path, language_hint: str | None = None) -> TranscriptionResult:
            raise STTError("Model failed to load")

    app.dependency_overrides[get_stt] = lambda: FailingSTTProvider()

    wav_bytes = _minimal_wav_bytes()
    fake_wav_path = Path("/tmp/fake_test_audio3.wav")
    fake_wav_path.write_bytes(wav_bytes)

    try:
        with patch(
            "app.routers.audio.convert_webm_to_wav",
            return_value=fake_wav_path,
        ):
            response = client_with_stub_stt.post(
                "/api/audio/transcribe",
                files={"file": ("audio.webm", wav_bytes, "audio/webm")},
            )

        assert response.status_code == 422
        assert "Model failed to load" in response.json()["detail"]
    finally:
        fake_wav_path.unlink(missing_ok=True)
        app.dependency_overrides[get_stt] = lambda: StubSTTProvider()
