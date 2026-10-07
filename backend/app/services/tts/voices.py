from dataclasses import dataclass

from app.language_data import VoiceRecord, load_language_records


@dataclass(frozen=True)
class VoiceInfo:
    key: str
    display_name: str
    gender: str
    locale: str
    quality: str
    speaking_rate: str

    @property
    def language(self) -> str:
        """The language code this voice speaks: the locale before "_" (`de_DE` → `de`)."""
        return self.locale.split("_")[0]


def _voice_info(record: VoiceRecord) -> VoiceInfo:
    return VoiceInfo(
        key=record.key,
        display_name=record.display_name,
        gender=record.gender,
        locale=record.locale,
        quality=record.quality,
        speaking_rate=record.speaking_rate,
    )


AVAILABLE_VOICES: tuple[VoiceInfo, ...] = tuple(
    _voice_info(voice) for language in load_language_records() for voice in language.voices
)
"""Every voice, grouped by language in practice-language order. The voices come from the
language data files in `app/language_data/languages/`."""


def voices_for(language_code: str) -> tuple[VoiceInfo, ...]:
    return tuple(voice for voice in AVAILABLE_VOICES if voice.language == language_code)
