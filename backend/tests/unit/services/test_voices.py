"""Unit tests for the voice catalog."""

from app.services.tts.voices import AVAILABLE_VOICES


def test_available_voices_has_exactly_two_entries() -> None:
    assert len(AVAILABLE_VOICES) == 2


def test_each_voice_has_non_empty_key() -> None:
    for voice in AVAILABLE_VOICES:
        assert voice.key, f"Voice key must not be empty, got: {voice!r}"


def test_each_voice_has_non_empty_display_name() -> None:
    for voice in AVAILABLE_VOICES:
        assert voice.display_name, f"Voice display_name must not be empty, got: {voice!r}"


def test_each_voice_has_non_empty_gender() -> None:
    for voice in AVAILABLE_VOICES:
        assert voice.gender, f"Voice gender must not be empty, got: {voice!r}"


def test_each_voice_has_non_empty_locale() -> None:
    for voice in AVAILABLE_VOICES:
        assert voice.locale, f"Voice locale must not be empty, got: {voice!r}"


def test_all_voice_keys_are_unique() -> None:
    keys = [v.key for v in AVAILABLE_VOICES]
    assert len(keys) == len(set(keys)), "Duplicate voice keys detected"


def test_davefx_is_the_first_voice() -> None:
    assert AVAILABLE_VOICES[0].key == "es_ES-davefx-medium"


def test_at_least_one_female_voice_exists() -> None:
    female_voices = [v for v in AVAILABLE_VOICES if v.gender == "female"]
    assert len(female_voices) >= 1, "Expected at least one female voice"


def test_each_voice_has_valid_speaking_rate() -> None:
    valid_rates = {"slow", "natural", "fast"}
    for voice in AVAILABLE_VOICES:
        assert (
            voice.speaking_rate in valid_rates
        ), f"Invalid speaking_rate '{voice.speaking_rate}' for {voice.key}"
