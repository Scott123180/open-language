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


# --- 006: voice installation contract (T014) -----------------------------------------


def test_voice_installation_is_an_abc_with_only_is_installed():
    from abc import ABC

    from app.services.tts.base import VoiceInstallation

    assert issubclass(VoiceInstallation, ABC)
    assert VoiceInstallation.__abstractmethods__ == frozenset({"is_installed"})


def test_piper_voice_installation_implements_the_contract(tmp_path):
    from app.services.tts.base import VoiceInstallation
    from app.services.tts.piper import PiperVoiceInstallation

    installation = PiperVoiceInstallation(tmp_path)

    assert isinstance(installation, VoiceInstallation)
    assert installation.is_installed("any-voice") is False


# --- 007: the voice of one message (T013, contracts §11) -------------------------------


def test_message_voice_lookup_is_an_abc_with_only_voice_for_message():
    import inspect
    from abc import ABC

    from app.services.tts.base import MessageVoiceLookup

    assert issubclass(MessageVoiceLookup, ABC)
    assert MessageVoiceLookup.__abstractmethods__ == frozenset({"voice_for_message"})
    parameters = inspect.signature(MessageVoiceLookup.voice_for_message).parameters
    assert list(parameters) == ["self", "message_id"]


def test_message_voice_lookup_names_what_to_say_when_a_voice_is_missing():
    from app.services.tts.base import MessageVoiceLookup

    class NoVoices(MessageVoiceLookup):
        def voice_for_message(self, message_id: int) -> str | None:
            return None

    assert NoVoices().unavailable_message(7).strip()
