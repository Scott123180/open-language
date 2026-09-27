"""T007: which voice speaks a language (data-model §4, FR-016, FR-018)."""

import pytest

from app.practice_languages import UnknownLanguage, voice_for, voice_unavailable_message


def test_no_choice_resolves_to_the_default_voice():
    assert voice_for("de", {}) == "de_DE-thorsten-medium"


def test_a_choice_for_the_language_is_used():
    assert voice_for("de", {"de": "de_DE-kerstin-low"}) == "de_DE-kerstin-low"


def test_a_choice_in_another_language_is_never_returned():
    assert voice_for("de", {"de": "es_ES-davefx-medium"}) == "de_DE-thorsten-medium"


def test_an_unknown_stored_voice_falls_back_to_the_default():
    assert voice_for("de", {"de": "xx_XX-gone-low"}) == "de_DE-thorsten-medium"


def test_a_choice_for_another_language_does_not_leak():
    assert voice_for("es", {"de": "de_DE-kerstin-low"}) == "es_ES-davefx-medium"


def test_an_unknown_language_raises():
    with pytest.raises(UnknownLanguage):
        voice_for("fr", {})


def test_the_unavailable_message_says_what_happened_and_what_to_do():
    message = voice_unavailable_message("de")

    assert "German voice isn't installed" in message
    assert "./run.sh --setup" in message
    assert "keep practising in text" in message


def test_the_unavailable_message_names_no_voice_key():
    assert "thorsten" not in voice_unavailable_message("de").lower()


def test_the_unavailable_message_rejects_an_unknown_language():
    with pytest.raises(UnknownLanguage):
        voice_unavailable_message("fr")
