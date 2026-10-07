"""Unit tests for the voice catalog."""

from app.services.tts.voices import AVAILABLE_VOICES, VoiceInfo, voices_for


def test_available_voices_start_with_spanish_then_german() -> None:
    assert [v.key for v in AVAILABLE_VOICES][:4] == [
        "es_ES-davefx-medium",
        "es_AR-daniela-high",
        "de_DE-thorsten-medium",
        "de_DE-kerstin-low",
    ]


def _voice(key: str) -> VoiceInfo:
    return next(v for v in AVAILABLE_VOICES if v.key == key)


def test_thorsten_is_a_natural_medium_male_german_voice() -> None:
    assert _voice("de_DE-thorsten-medium") == VoiceInfo(
        key="de_DE-thorsten-medium",
        display_name="Thorsten (Germany)",
        gender="male",
        locale="de_DE",
        quality="medium",
        speaking_rate="natural",
    )


def test_kerstin_is_a_natural_low_female_german_voice() -> None:
    assert _voice("de_DE-kerstin-low") == VoiceInfo(
        key="de_DE-kerstin-low",
        display_name="Kerstin (Germany)",
        gender="female",
        locale="de_DE",
        quality="low",
        speaking_rate="natural",
    )


def test_a_voice_language_is_the_locale_prefix() -> None:
    voice = VoiceInfo(
        key="k",
        display_name="K",
        gender="male",
        locale="de_DE",
        quality="low",
        speaking_rate="natural",
    )

    assert voice.language == "de"


def test_voices_for_german_lists_both_german_voices_in_order() -> None:
    assert [v.key for v in voices_for("de")] == ["de_DE-thorsten-medium", "de_DE-kerstin-low"]


def test_voices_for_an_unknown_language_is_empty() -> None:
    assert voices_for("fr") == ()


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
