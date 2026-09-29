"""The languages a learner can practise. The one place a language code is defined."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class PracticeLanguage:
    code: str
    name: str
    default_voice: str
    host_names: Mapping[str, tuple[str, ...]]
    """Podcast host names that suit the language, keyed by the gender of the host's voice."""
    guest_labels: tuple[str, ...]
    """The language's own words for a show's guest, cut from host lines like any label."""
    sample_line: str
    """What a host says in a voice sample. Holds exactly one `{name}`."""


PRACTICE_LANGUAGES: Mapping[str, PracticeLanguage] = MappingProxyType(
    {
        "es": PracticeLanguage(
            code="es",
            name="Spanish",
            default_voice="es_ES-davefx-medium",
            host_names=MappingProxyType(
                {
                    "female": (
                        "Lucía",
                        "Carmen",
                        "Sofía",
                        "Elena",
                        "Isabel",
                        "Marta",
                        "Paula",
                        "Inés",
                        "Julia",
                        "Rocío",
                    ),
                    "male": (
                        "Marco",
                        "Javier",
                        "Diego",
                        "Pablo",
                        "Andrés",
                        "Mateo",
                        "Carlos",
                        "Hugo",
                        "Álvaro",
                        "Luis",
                    ),
                }
            ),
            guest_labels=("Invitado", "Invitada", "Oyente", "Presentador", "Presentadora"),
            sample_line="Hola, soy {name}. ¡Bienvenidos al programa!",
        ),
        "de": PracticeLanguage(
            code="de",
            name="German",
            default_voice="de_DE-thorsten-medium",
            host_names=MappingProxyType(
                {
                    "female": (
                        "Lena",
                        "Anna",
                        "Sophie",
                        "Hannah",
                        "Clara",
                        "Emma",
                        "Marie",
                        "Katrin",
                        "Johanna",
                        "Greta",
                    ),
                    "male": (
                        "Jonas",
                        "Felix",
                        "Lukas",
                        "Paul",
                        "Leon",
                        "Moritz",
                        "Tobias",
                        "Niklas",
                        "Florian",
                        "Jan",
                    ),
                }
            ),
            guest_labels=("Gast", "Zuhörer", "Zuhörerin", "Anrufer", "Anruferin", "Moderator"),
            sample_line="Hallo, ich bin {name}. Willkommen zur Sendung!",
        ),
    }
)
"""Every practice language, in display order."""

DEFAULT_PRACTICE_LANGUAGE = "es"

NATIVE_LANGUAGE_NAMES: Mapping[str, str] = MappingProxyType({"en": "English"})
"""Languages explanations are written in. Not selectable, but prompts need their names."""
