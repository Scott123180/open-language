"""Shared speech test double: fake voice files, real voice resolution.

`override_speech` replaces only what touches disk or Piper — the installation check and the
provider builder. Voice resolution (`voice_for`) and the unavailable message are the production
functions, so every test through it keeps them under test.
"""

import struct
import wave
from collections.abc import Mapping
from functools import partial
from pathlib import Path

from fastapi import Depends, FastAPI

from app.practice_languages import voice_for, voice_unavailable_message
from app.services.factory import get_app_settings, get_speech_for_language, get_voice_installation
from app.services.storage.base import AppSettingsRecord
from app.services.tts.base import TTSProvider, VoiceInstallation
from app.services.tts.selection import SpeechForLanguage

_SAMPLE_RATE = 22050
_SILENT_FRAMES = 100


class FakeVoiceInstallation(VoiceInstallation):
    """Every voice is installed when `installed` is None; otherwise only the listed keys."""

    def __init__(self, installed: set[str] | None = None) -> None:
        self._installed = installed

    def is_installed(self, voice_key: str) -> bool:
        return self._installed is None or voice_key in self._installed


class _RecordingProvider(TTSProvider):
    def __init__(self, voice_key: str, builder: "RecordingTtsBuilder") -> None:
        self._voice_key = voice_key
        self._builder = builder

    @property
    def voice_name(self) -> str:
        return self._voice_key

    def synthesize(self, text: str, output_path: Path) -> None:
        self._builder.synthesized.append((self._voice_key, text, output_path))
        write_silent_wav(output_path)


class RecordingTtsBuilder:
    """Builds providers that record `(voice_key, text, output_path)` and write a valid WAV."""

    def __init__(self) -> None:
        self.synthesized: list[tuple[str, str, Path]] = []

    def __call__(self, voice_key: str) -> TTSProvider:
        return _RecordingProvider(voice_key, self)

    @property
    def voice_keys(self) -> list[str]:
        return [voice_key for voice_key, _text, _path in self.synthesized]


def override_speech(
    app: FastAPI,
    *,
    voice_choices: Mapping[str, str] | None = None,
    installed: set[str] | None = None,
) -> RecordingTtsBuilder:
    """Route the app's speech through fakes. `voice_choices=None` reads the stored settings."""
    builder = RecordingTtsBuilder()
    installation = FakeVoiceInstallation(installed)

    def speech(
        app_settings: AppSettingsRecord = Depends(get_app_settings),
        installation: VoiceInstallation = Depends(get_voice_installation),
    ) -> SpeechForLanguage:
        choices = app_settings.voice_choices if voice_choices is None else voice_choices
        resolve = partial(voice_for, voice_choices=choices)
        return SpeechForLanguage(resolve, installation, builder, voice_unavailable_message)

    app.dependency_overrides[get_voice_installation] = lambda: installation
    app.dependency_overrides[get_speech_for_language] = speech
    return builder


def write_silent_wav(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(_SAMPLE_RATE)
        wav_file.writeframes(struct.pack(f"<{_SILENT_FRAMES}h", *[0] * _SILENT_FRAMES))
