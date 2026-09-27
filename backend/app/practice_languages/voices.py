"""Which voice speaks a practice language, and what to say when it cannot (FR-016, FR-018)."""

from collections.abc import Mapping

from app.practice_languages.catalog import PRACTICE_LANGUAGES
from app.practice_languages.naming import UnknownLanguage, practice_language_name
from app.services.tts.voices import AVAILABLE_VOICES

_VOICE_LANGUAGES = {voice.key: voice.language for voice in AVAILABLE_VOICES}


def voice_for(code: str, voice_choices: Mapping[str, str]) -> str:
    """The learner's voice for a language, or its default. Never another language's voice."""
    if code not in PRACTICE_LANGUAGES:
        raise UnknownLanguage(code)
    chosen = voice_choices.get(code)
    if chosen is not None and _VOICE_LANGUAGES.get(chosen) == code:
        return chosen
    return PRACTICE_LANGUAGES[code].default_voice


def voice_unavailable_message(code: str) -> str:
    name = practice_language_name(code)
    return (
        f"The {name} voice isn't installed, so {name} can't be read aloud. "
        "Run ./run.sh --setup to download it. You can keep practising in text."
    )
