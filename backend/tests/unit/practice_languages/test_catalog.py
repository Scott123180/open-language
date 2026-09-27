"""T005: the practice-language catalogue and its invariants (data-model §1, I1–I6)."""

import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import app.practice_languages as practice_languages
from app.practice_languages import DEFAULT_PRACTICE_LANGUAGE, PRACTICE_LANGUAGES
from app.practice_languages.catalog import NATIVE_LANGUAGE_NAMES
from app.services.tts.voices import AVAILABLE_VOICES

RUN_SCRIPT = Path(__file__).resolve().parents[4] / "run.sh"
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2}$")
PUBLIC_NAMES = {
    "PracticeLanguage",
    "PRACTICE_LANGUAGES",
    "DEFAULT_PRACTICE_LANGUAGE",
    "UnknownLanguage",
    "language_name",
    "ConversationLanguages",
    "voice_for",
    "voice_unavailable_message",
}


def _run_script_voice_keys() -> set[str]:
    array = re.search(r"PIPER_VOICES=\((.*?)\)", RUN_SCRIPT.read_text(), re.DOTALL)
    assert array, "run.sh must declare a PIPER_VOICES=( … ) array"
    return set(re.findall(r'"([^"]+)"', array.group(1)))


def _voices_by_key():
    return {voice.key: voice for voice in AVAILABLE_VOICES}


def test_languages_are_spanish_then_german():
    assert list(PRACTICE_LANGUAGES) == ["es", "de"]


def test_languages_are_named_spanish_and_german():
    assert [language.name for language in PRACTICE_LANGUAGES.values()] == ["Spanish", "German"]


def test_default_voices_are_davefx_and_thorsten():
    assert [language.default_voice for language in PRACTICE_LANGUAGES.values()] == [
        "es_ES-davefx-medium",
        "de_DE-thorsten-medium",
    ]


def test_the_default_language_is_spanish_and_in_the_catalogue():
    assert DEFAULT_PRACTICE_LANGUAGE == "es"
    assert DEFAULT_PRACTICE_LANGUAGE in PRACTICE_LANGUAGES


@pytest.mark.parametrize("code", list(PRACTICE_LANGUAGES))
def test_every_language_has_at_least_one_voice(code):
    assert any(voice.language == code for voice in AVAILABLE_VOICES)


@pytest.mark.parametrize("language", list(PRACTICE_LANGUAGES.values()), ids=lambda lang: lang.code)
def test_every_default_voice_exists_and_speaks_its_own_language(language):
    voice = _voices_by_key().get(language.default_voice)

    assert voice is not None
    assert voice.language == language.code


def test_every_catalogue_voice_is_downloaded_by_run_sh():
    missing = {voice.key for voice in AVAILABLE_VOICES} - _run_script_voice_keys()

    assert not missing, f"Add these voices to PIPER_VOICES in run.sh: {sorted(missing)}"


def test_no_code_is_both_a_practice_and_a_native_language():
    assert not set(PRACTICE_LANGUAGES) & set(NATIVE_LANGUAGE_NAMES)


@pytest.mark.parametrize("code", [*PRACTICE_LANGUAGES, *NATIVE_LANGUAGE_NAMES])
def test_every_code_is_lowercase_iso_639_1(code):
    assert LANGUAGE_CODE_PATTERN.match(code)


def test_every_entry_is_keyed_by_its_own_code():
    assert all(code == language.code for code, language in PRACTICE_LANGUAGES.items())


def test_a_practice_language_is_frozen():
    language = PRACTICE_LANGUAGES["de"]

    with pytest.raises(FrozenInstanceError):
        language.name = "Deutsch"  # type: ignore[misc]


def test_the_catalogue_cannot_be_modified():
    with pytest.raises(TypeError):
        PRACTICE_LANGUAGES["fr"] = PRACTICE_LANGUAGES["de"]  # type: ignore[index]


def test_the_package_exports_exactly_its_public_interface():
    assert set(practice_languages.__all__) == PUBLIC_NAMES
