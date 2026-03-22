from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceInfo:
    key: str
    display_name: str
    gender: str
    locale: str
    quality: str
    speaking_rate: str


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
)
