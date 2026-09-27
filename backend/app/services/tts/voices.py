from dataclasses import dataclass


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


AVAILABLE_VOICES: tuple[VoiceInfo, ...] = (
    VoiceInfo(
        key="es_ES-davefx-medium",
        display_name="David (Spain)",
        gender="male",
        locale="es_ES",
        quality="medium",
        speaking_rate="natural",
    ),
    VoiceInfo(
        key="es_AR-daniela-high",
        display_name="Daniela (Argentina)",
        gender="female",
        locale="es_AR",
        quality="high",
        speaking_rate="fast",
    ),
    VoiceInfo(
        key="de_DE-thorsten-medium",
        display_name="Thorsten (Germany)",
        gender="male",
        locale="de_DE",
        quality="medium",
        speaking_rate="natural",
    ),
    VoiceInfo(
        key="de_DE-kerstin-low",
        display_name="Kerstin (Germany)",
        gender="female",
        locale="de_DE",
        quality="low",
        speaking_rate="natural",
    ),
)
"""Every voice, grouped by language in practice-language order. Keys must match run.sh."""


def voices_for(language_code: str) -> tuple[VoiceInfo, ...]:
    return tuple(voice for voice in AVAILABLE_VOICES if voice.language == language_code)
