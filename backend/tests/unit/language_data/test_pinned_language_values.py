"""T006: today's Spanish and German values, frozen literally before they move to data files.

Written against the Python literals in `practice_languages/catalog.py` and `services/tts/voices.py`
and kept unchanged through the move (FR-021, SC-009). It never asserts that only these two
languages exist, so a language added by data alone leaves it green.
"""

import pytest

from app.practice_languages import PRACTICE_LANGUAGES
from app.services.tts.voices import AVAILABLE_VOICES, VoiceInfo, voices_for

SPANISH_HOSTS = {
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
GERMAN_HOSTS = {
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
PINNED_LANGUAGES = {
    "es": {
        "code": "es",
        "name": "Spanish",
        "default_voice": "es_ES-davefx-medium",
        "host_names": SPANISH_HOSTS,
        "guest_labels": ("Invitado", "Invitada", "Oyente", "Presentador", "Presentadora"),
        "sample_line": "Hola, soy {name}. ¡Bienvenidos al programa!",
    },
    "de": {
        "code": "de",
        "name": "German",
        "default_voice": "de_DE-thorsten-medium",
        "host_names": GERMAN_HOSTS,
        "guest_labels": ("Gast", "Zuhörer", "Zuhörerin", "Anrufer", "Anruferin", "Moderator"),
        "sample_line": "Hallo, ich bin {name}. Willkommen zur Sendung!",
    },
}
DAVEFX = VoiceInfo("es_ES-davefx-medium", "David (Spain)", "male", "es_ES", "medium", "natural")
DANIELA = VoiceInfo("es_AR-daniela-high", "Daniela (Argentina)", "female", "es_AR", "high", "fast")
THORSTEN = VoiceInfo(
    "de_DE-thorsten-medium", "Thorsten (Germany)", "male", "de_DE", "medium", "natural"
)
KERSTIN = VoiceInfo("de_DE-kerstin-low", "Kerstin (Germany)", "female", "de_DE", "low", "natural")
PINNED_VOICES = (DAVEFX, DANIELA, THORSTEN, KERSTIN)


def _as_plain(language) -> dict:
    return {
        "code": language.code,
        "name": language.name,
        "default_voice": language.default_voice,
        "host_names": dict(language.host_names),
        "guest_labels": language.guest_labels,
        "sample_line": language.sample_line,
    }


def test_spanish_then_german_lead_the_catalogue():
    assert list(PRACTICE_LANGUAGES)[:2] == ["es", "de"]


@pytest.mark.parametrize("code", ["es", "de"])
def test_every_field_of_the_language_is_unchanged(code):
    assert _as_plain(PRACTICE_LANGUAGES[code]) == PINNED_LANGUAGES[code]


@pytest.mark.parametrize("code", ["es", "de"])
def test_host_name_genders_keep_their_order(code):
    assert list(PRACTICE_LANGUAGES[code].host_names) == ["female", "male"]


def test_the_four_voices_are_unchanged_and_in_order():
    pinned_keys = {voice.key for voice in PINNED_VOICES}

    assert tuple(voice for voice in AVAILABLE_VOICES if voice.key in pinned_keys) == PINNED_VOICES


def test_spanish_voices_are_davefx_then_daniela():
    assert voices_for("es") == (DAVEFX, DANIELA)


def test_german_voices_are_thorsten_then_kerstin():
    assert voices_for("de") == (THORSTEN, KERSTIN)
