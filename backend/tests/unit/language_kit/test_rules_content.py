"""T023: rules about a language's content: host names, scripted turns, dictation, voice spread."""

import pytest

from language_kit.findings import Severity
from language_kit.language_files import LanguageData
from language_kit.rules import (
    CoversEveryScenario,
    EachContainsSpecialLetter,
    NamesForEveryVoiceGender,
    PreferBothGenders,
    PreferTwoVoices,
)
from tests.unit.language_kit.conftest import SCENARIO_IDS, fake_context

FEMALE = ["Ana", "Bea", "Cora", "Dina", "Eva", "Fay", "Gia", "Hana", "Ines", "Jana"]
MALE = ["Abel", "Bruno", "Ciro", "Dario", "Elio", "Fabio", "Gino", "Hugo", "Ivo", "Jacopo"]
BOTH_GENDERS = LanguageData(
    "it", {"voices": [{"key": "a", "gender": "female"}, {"key": "b", "gender": "male"}]}
)


def _check(rule, value, language=BOTH_GENDERS, path="podcast.host_names", **context):
    return rule.check(value, fake_context(code="it", path=path, language=language, **context))


def _names(**changes) -> dict[str, list[str]]:
    return {"female": list(FEMALE), "male": list(MALE)} | changes


def test_names_pass_ten_unique_names_for_each_voice_gender():
    assert _check(NamesForEveryVoiceGender(10), _names()) == []


def test_names_report_how_many_more_are_needed_for_a_gender():
    (finding,) = _check(NamesForEveryVoiceGender(10), _names(female=FEMALE[:8]))

    assert finding.path == "podcast.host_names.female"
    assert "found 8" in finding.detail.lower() and "Add 2 more female names" in finding.detail


def test_names_need_a_key_for_every_voice_gender():
    (finding,) = _check(NamesForEveryVoiceGender(10), {"female": FEMALE})

    assert "male" in finding.detail


def test_names_refuse_a_gender_no_voice_has():
    one_gender = LanguageData("it", {"voices": [{"key": "a", "gender": "female"}]})

    (finding,) = _check(NamesForEveryVoiceGender(10), _names(), language=one_gender)

    assert finding.path == "podcast.host_names.male"


def test_names_skip_gender_coverage_while_a_voice_gender_is_invalid():
    odd = LanguageData("it", {"voices": [{"key": "a", "gender": "robot"}]})

    assert _check(NamesForEveryVoiceGender(10), _names(), language=odd) == []


def test_names_are_unique_across_genders_ignoring_case():
    findings = _check(NamesForEveryVoiceGender(10), _names(male=[*MALE[:9], "ana"]))

    assert any('"ana"' in finding.detail for finding in findings)


@pytest.mark.parametrize("bad", ["", "A" * 21, "R2D2"])
def test_each_name_has_one_to_twenty_characters_and_no_digits(bad):
    assert _check(NamesForEveryVoiceGender(10), _names(female=[*FEMALE[:9], bad])) != []


@pytest.mark.parametrize("value", [None, "x", ["x"], {"female": "Ana"}, {"female": [1]}])
def test_names_never_raise_for_a_wrong_shape(value):
    assert _check(NamesForEveryVoiceGender(10), value) != []


def _turns(**changes) -> dict[str, list[str]]:
    return {scenario: [f"Turn {n}." for n in range(5)] for scenario in SCENARIO_IDS} | changes


def test_turns_pass_five_turns_for_every_scenario():
    assert _check(CoversEveryScenario(5), _turns(), path="evaluation.turns") == []


def test_turns_name_a_missing_scenario():
    turns = _turns()
    del turns["rent-a-car"]

    (finding,) = _check(CoversEveryScenario(5), turns, path="evaluation.turns")

    assert finding.path == "evaluation.turns.rent-a-car"


def test_turns_refuse_a_scenario_that_does_not_exist():
    (finding,) = _check(
        CoversEveryScenario(5), _turns(**{"fly-a-kite": ["x"] * 5}), path="evaluation.turns"
    )

    assert finding.path == "evaluation.turns.fly-a-kite"


@pytest.mark.parametrize("turns", [["a"] * 4, ["a"] * 6, ["a", "b", "c", "d", " "]])
def test_turns_need_exactly_five_non_empty_turns(turns):
    findings = _check(
        CoversEveryScenario(5), _turns(**{"rent-a-car": turns}), path="evaluation.turns"
    )

    assert [finding.path for finding in findings] == ["evaluation.turns.rent-a-car"]


@pytest.mark.parametrize("value", [None, [], "x", {"rent-a-car": "x"}])
def test_turns_never_raise_for_a_wrong_shape(value):
    assert _check(CoversEveryScenario(5), value, path="evaluation.turns") != []


def _with_letters(letters) -> LanguageData:
    return LanguageData("it", {"evaluation": {"special_letters": letters}})


def test_each_dictation_sentence_needs_a_special_letter():
    findings = _check(
        EachContainsSpecialLetter(),
        ["Perché no?", "Come stai?"],
        language=_with_letters("àèéìòù"),
        path="evaluation.dictation",
    )

    assert len(findings) == 1 and '"Come stai?"' in findings[0].detail


@pytest.mark.parametrize("letters", ["", None, "TODO", "àà"])
def test_dictation_passes_when_special_letters_are_empty_or_invalid(letters):
    findings = _check(
        EachContainsSpecialLetter(), ["Come stai?"], language=_with_letters(letters), path="x"
    )

    assert findings == []


def test_prefer_two_voices_warns_about_a_single_voice():
    (finding,) = _check(PreferTwoVoices(), [{"key": "a", "gender": "female"}], path="voices")

    assert finding.severity is Severity.WARNING


def test_prefer_two_voices_passes_two():
    assert _check(PreferTwoVoices(), [{"key": "a"}, {"key": "b"}], path="voices") == []


def test_prefer_both_genders_says_podcasts_will_cast_one_gender():
    voices = [{"key": "a", "gender": "female"}, {"key": "b", "gender": "female"}]

    (finding,) = _check(PreferBothGenders(), voices, path="voices")

    assert finding.severity is Severity.WARNING
    assert "one gender" in finding.detail


def test_prefer_both_genders_passes_both():
    voices = [{"key": "a", "gender": "female"}, {"key": "b", "gender": "male"}]

    assert _check(PreferBothGenders(), voices, path="voices") == []
