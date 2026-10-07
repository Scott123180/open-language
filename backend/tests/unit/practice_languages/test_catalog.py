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
    "NATIVE_LANGUAGE_NAMES",
    "UnknownLanguage",
    "language_name",
    "ConversationLanguages",
    "voice_for",
    "voice_unavailable_message",
    "host_names_for",
    "guest_labels_for",
    "voice_sample_line",
}


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


def test_run_sh_downloads_the_voices_listed_by_the_language_data():
    script = RUN_SCRIPT.read_text()

    assert "-m app.language_data voice-keys" in script
    assert not re.search(r"PIPER_VOICES=\(\s*\"", script), "run.sh must not hard-code voice keys"


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


# --- 007: host names, guest labels and the voice sample (data-model §1.5, P6–P7) --------


def _genders(code: str) -> set[str]:
    return {voice.gender for voice in AVAILABLE_VOICES if voice.language == code}


@pytest.mark.parametrize("code", list(PRACTICE_LANGUAGES))
def test_p6_every_voice_gender_has_at_least_eight_distinct_names(code):
    for gender in _genders(code):
        names = practice_languages.host_names_for(code, gender)

        assert len(names) >= 8, (code, gender)
        assert len(set(names)) == len(names), (code, gender)


@pytest.mark.parametrize("code", list(PRACTICE_LANGUAGES))
def test_every_language_has_guest_labels(code):
    assert practice_languages.guest_labels_for(code)


@pytest.mark.parametrize("code", list(PRACTICE_LANGUAGES))
def test_fr030_every_language_has_at_least_two_different_voices(code):
    keys = {voice.key for voice in AVAILABLE_VOICES if voice.language == code}

    assert len(keys) >= 2


@pytest.mark.parametrize("language", list(PRACTICE_LANGUAGES.values()), ids=lambda lang: lang.code)
def test_p7_every_sample_line_has_exactly_one_name_placeholder(language):
    assert language.sample_line.count("{name}") == 1


@pytest.mark.parametrize("code", list(PRACTICE_LANGUAGES))
def test_the_voice_sample_line_speaks_the_hosts_name(code):
    assert "Lena" in practice_languages.voice_sample_line(code, "Lena")


@pytest.mark.parametrize(
    "lookup",
    [
        lambda: practice_languages.host_names_for("fr", "female"),
        lambda: practice_languages.guest_labels_for("fr"),
        lambda: practice_languages.voice_sample_line("fr", "Lena"),
    ],
)
def test_an_unknown_language_has_no_host_data(lookup):
    with pytest.raises(practice_languages.UnknownLanguage):
        lookup()
