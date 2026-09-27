"""The languages a learner can practise. The one place a language code is defined."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class PracticeLanguage:
    code: str
    name: str
    default_voice: str


PRACTICE_LANGUAGES: Mapping[str, PracticeLanguage] = MappingProxyType(
    {
        "es": PracticeLanguage(code="es", name="Spanish", default_voice="es_ES-davefx-medium"),
        "de": PracticeLanguage(code="de", name="German", default_voice="de_DE-thorsten-medium"),
    }
)
"""Every practice language, in display order."""

DEFAULT_PRACTICE_LANGUAGE = "es"

NATIVE_LANGUAGE_NAMES: Mapping[str, str] = MappingProxyType({"en": "English"})
"""Languages explanations are written in. Not selectable, but prompts need their names."""
