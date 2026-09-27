"""T006: language names for prompts (data-model §2, research R2)."""

from dataclasses import FrozenInstanceError

import pytest

from app.practice_languages import ConversationLanguages, UnknownLanguage, language_name


@pytest.mark.parametrize(("code", "name"), [("de", "German"), ("es", "Spanish"), ("en", "English")])
def test_language_name_names_practice_and_native_languages(code, name):
    assert language_name(code) == name


@pytest.mark.parametrize("code", ["fr", ""])
def test_an_unknown_code_raises_unknown_language(code):
    with pytest.raises(UnknownLanguage):
        language_name(code)


def test_unknown_language_is_a_value_error_naming_the_code():
    with pytest.raises(ValueError, match="'fr'"):
        language_name("fr")


def test_conversation_languages_names_both_sides():
    languages = ConversationLanguages.of("de", "en")

    assert (languages.target_code, languages.target_name, languages.native_name) == (
        "de",
        "German",
        "English",
    )


@pytest.mark.parametrize(("target", "native"), [("xx", "en"), ("de", "xx")])
def test_conversation_languages_rejects_an_unknown_code(target, native):
    with pytest.raises(UnknownLanguage):
        ConversationLanguages.of(target, native)


def test_the_native_language_cannot_be_the_target():
    with pytest.raises(UnknownLanguage):
        ConversationLanguages.of("en", "en")


def test_conversation_languages_is_frozen():
    languages = ConversationLanguages.of("de", "en")

    with pytest.raises(FrozenInstanceError):
        languages.target_name = "Deutsch"  # type: ignore[misc]
