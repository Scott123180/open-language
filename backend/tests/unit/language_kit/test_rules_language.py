"""T022: rules about the language itself and its voices."""

import pytest

from language_kit.findings import Severity
from language_kit.language_files import LanguageData
from language_kit.rules import (
    DefaultVoiceAmongVoices,
    NotCatalogued,
    NotExplanationLanguage,
    SupportedScript,
    VoicesInCatalogue,
    WhisperSupports,
)
from tests.unit.language_kit.conftest import fake_context
from tests.unit.language_kit.fakes import FakeVoiceCatalogue, candidate


def _details(rule, value, **context) -> list[str]:
    return [finding.detail for finding in rule.check(value, fake_context(path="code", **context))]


def test_not_catalogued_refuses_a_catalogued_code_and_points_to_check_and_backfill():
    (detail,) = _details(NotCatalogued(), "de")

    assert "kit.sh check" in detail and "kit.sh backfill" in detail


def test_not_catalogued_passes_a_new_code():
    assert _details(NotCatalogued(), "it") == []


def test_not_catalogued_is_an_onboarding_only_rule():
    assert NotCatalogued().onboarding_only
    assert not NotExplanationLanguage().onboarding_only


def test_not_explanation_language_refuses_english():
    assert len(_details(NotExplanationLanguage(), "en")) == 1
    assert _details(NotExplanationLanguage(), "it") == []


@pytest.mark.parametrize("code", ["ar", "he", "fa", "ur", "yi", "ps", "sd", "ug", "dv"])
def test_supported_script_refuses_right_to_left_languages(code):
    (detail,) = _details(SupportedScript(), code)

    assert "right to left" in detail


@pytest.mark.parametrize("code", ["zh", "ja", "th", "lo", "km", "my", "bo"])
def test_supported_script_refuses_languages_without_spaces(code):
    (detail,) = _details(SupportedScript(), code)

    assert "spaces" in detail


def test_supported_script_passes_a_spaced_left_to_right_language():
    assert _details(SupportedScript(), "it") == []


def test_whisper_supports_refuses_an_unknown_code():
    assert len(_details(WhisperSupports(), "xx")) == 1
    assert _details(WhisperSupports(), "it") == []


VOICES = [{"key": "it_IT-paola-medium", "gender": "female"}]
CATALOGUE = FakeVoiceCatalogue(
    [candidate("it_IT-paola-medium"), candidate("de_DE-thorsten-medium")]
)


def test_voices_in_catalogue_passes_a_single_speaker_voice_of_the_language():
    assert _details(VoicesInCatalogue(), VOICES, code="it", voice_catalogue=CATALOGUE) == []


def test_voices_in_catalogue_refuses_another_languages_voice():
    voices = [{"key": "de_DE-thorsten-medium"}]

    (detail,) = _details(VoicesInCatalogue(), voices, code="it", voice_catalogue=CATALOGUE)

    assert "de_DE-thorsten-medium" in detail


def test_voices_in_catalogue_refuses_an_unknown_or_multi_speaker_voice():
    voices = [{"key": "de_DE-mls-medium"}]

    assert len(_details(VoicesInCatalogue(), voices, code="de", voice_catalogue=CATALOGUE)) == 1


def test_voices_in_catalogue_reports_nothing_without_a_catalogue():
    assert _details(VoicesInCatalogue(), [{"key": "xx"}], code="it") == []


def _with_voices(*keys: str) -> LanguageData:
    return LanguageData("it", {"voices": [{"key": key} for key in keys]})


def test_default_voice_among_voices_passes_one_of_the_voices():
    language = _with_voices("it_IT-paola-medium")

    assert _details(DefaultVoiceAmongVoices(), "it_IT-paola-medium", language=language) == []


def test_default_voice_among_voices_names_the_voices():
    language = _with_voices("it_IT-paola-medium")

    (detail,) = _details(DefaultVoiceAmongVoices(), "it_IT-serena-high", language=language)

    assert "it_IT-paola-medium" in detail


def test_default_voice_among_voices_is_silent_when_voices_are_missing():
    assert _details(DefaultVoiceAmongVoices(), "x", language=LanguageData("it", {})) == []


def test_language_rules_are_errors():
    assert SupportedScript().severity is Severity.ERROR
