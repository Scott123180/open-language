import struct
import wave
from pathlib import Path

import pytest

from app.services.tts.base import TTSError, TTSProvider


class StubTTSProvider(TTSProvider):
    @property
    def voice_name(self) -> str:
        return "stub-voice"

    def synthesize(self, text: str, output_path: Path) -> None:
        if not text.strip():
            raise TTSError("Empty text")
        with wave.open(str(output_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(22050)
            f.writeframes(struct.pack("<100h", *[0] * 100))


def test_synthesize_creates_wav(tmp_path):
    p = StubTTSProvider()
    out = tmp_path / "out.wav"
    p.synthesize("hola", out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_synthesize_raises_on_empty_text(tmp_path):
    p = StubTTSProvider()
    with pytest.raises(TTSError):
        p.synthesize("", tmp_path / "out.wav")


def test_voice_name_is_string():
    assert isinstance(StubTTSProvider().voice_name, str)
