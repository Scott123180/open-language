"""Speak a language with that language's voice, or say plainly that it cannot (FR-018)."""

from collections.abc import Callable

from app.services.tts.base import TTSProvider, VoiceInstallation, VoiceUnavailable
from app.services.tts.voices import AVAILABLE_VOICES

_VOICE_LANGUAGES = {voice.key: voice.language for voice in AVAILABLE_VOICES}


class SpeechForLanguage:
    """Chooses the TTS provider for a text by the language it is written in.

    A missing voice raises `VoiceUnavailable`; another language's voice is never used instead.
    """

    def __init__(
        self,
        resolve_voice: Callable[[str], str],
        installation: VoiceInstallation,
        build: Callable[[str], TTSProvider],
        unavailable_message: Callable[[str], str],
    ) -> None:
        self._resolve_voice = resolve_voice
        self._installation = installation
        self._build = build
        self._unavailable_message = unavailable_message

    def voice_key(self, language_code: str) -> str:
        return self._resolve_voice(language_code)

    def is_available(self, language_code: str) -> bool:
        return self._installation.is_installed(self.voice_key(language_code))

    def provider_for(self, language_code: str) -> TTSProvider:
        voice_key = self.voice_key(language_code)
        if not self._installation.is_installed(voice_key):
            raise VoiceUnavailable(self._unavailable_message(language_code))
        return self._build(voice_key)

    def provider_for_voice(
        self, language_code: str, voice_key: str, unavailable_message: str
    ) -> TTSProvider:
        """Speak with one given voice of the language, or raise. Never another voice (FR-031)."""
        speaks_language = _VOICE_LANGUAGES.get(voice_key) == language_code
        if not speaks_language or not self._installation.is_installed(voice_key):
            raise VoiceUnavailable(unavailable_message)
        return self._build(voice_key)
