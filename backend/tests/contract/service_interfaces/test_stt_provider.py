from pathlib import Path
from app.services.stt.base import STTProvider, TranscriptionResult, STTError
import pytest
import wave
import struct


class StubSTTProvider(STTProvider):
    def transcribe(self, audio_path: Path, language_hint=None) -> TranscriptionResult:
        if not audio_path.exists():
            raise STTError("File not found")
        return TranscriptionResult(text="hola mundo", detected_language="es")


def make_wav(path: Path):
    with wave.open(str(path), 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        data = struct.pack('<1000h', *[0] * 1000)
        f.writeframes(data)


def test_transcribe_returns_result(tmp_path):
    wav = tmp_path / "test.wav"
    make_wav(wav)
    provider = StubSTTProvider()
    result = provider.transcribe(wav)
    assert isinstance(result, TranscriptionResult)
    assert len(result.text) > 0


def test_transcribe_raises_on_missing_file(tmp_path):
    provider = StubSTTProvider()
    with pytest.raises(STTError):
        provider.transcribe(tmp_path / "nonexistent.wav")
