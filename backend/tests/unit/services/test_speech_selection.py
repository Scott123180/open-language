"""T009: SpeechForLanguage speaks a language with its own voice, or not at all (FR-018)."""

from pathlib import Path

import pytest

from app.services.tts.base import TTSError, TTSProvider, VoiceInstallation, VoiceUnavailable
from app.services.tts.selection import SpeechForLanguage

GERMAN_VOICE = "de_DE-kerstin-low"
UNAVAILABLE = "German can't be read aloud."


class FakeInstallation(VoiceInstallation):
    def __init__(self, installed: set[str]) -> None:
        self._installed = installed

    def is_installed(self, voice_key: str) -> bool:
        return voice_key in self._installed


class SilentProvider(TTSProvider):
    def __init__(self, voice_key: str) -> None:
        self._voice_key = voice_key

    @property
    def voice_name(self) -> str:
        return self._voice_key

    def synthesize(self, text: str, output_path: Path) -> None:
        output_path.write_bytes(b"")


class RecordingBuilder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, voice_key: str) -> TTSProvider:
        self.calls.append(voice_key)
        return SilentProvider(voice_key)


def _speech(installed: set[str], builder: RecordingBuilder) -> SpeechForLanguage:
    return SpeechForLanguage(
        resolve_voice=lambda code: GERMAN_VOICE if code == "de" else "es_ES-davefx-medium",
        installation=FakeInstallation(installed),
        build=builder,
        unavailable_message=lambda code: f"{code}: {UNAVAILABLE}",
    )


def test_voice_key_is_what_the_resolver_returns():
    assert _speech(set(), RecordingBuilder()).voice_key("de") == GERMAN_VOICE


@pytest.mark.parametrize(("installed", "expected"), [({GERMAN_VOICE}, True), (set(), False)])
def test_is_available_asks_the_installation_about_the_resolved_voice(installed, expected):
    assert _speech(installed, RecordingBuilder()).is_available("de") is expected


def test_provider_for_builds_the_resolved_voice_once():
    builder = RecordingBuilder()

    provider = _speech({GERMAN_VOICE}, builder).provider_for("de")

    assert builder.calls == [GERMAN_VOICE]
    assert provider.voice_name == GERMAN_VOICE


def test_provider_for_an_uninstalled_voice_raises_with_the_message():
    with pytest.raises(VoiceUnavailable) as raised:
        _speech(set(), RecordingBuilder()).provider_for("de")

    assert raised.value.user_message == f"de: {UNAVAILABLE}"


def test_provider_for_an_uninstalled_voice_never_builds_another_voice():
    builder = RecordingBuilder()

    with pytest.raises(VoiceUnavailable):
        _speech({"es_ES-davefx-medium"}, builder).provider_for("de")

    assert builder.calls == []


def test_voice_unavailable_is_a_tts_error():
    assert issubclass(VoiceUnavailable, TTSError)
