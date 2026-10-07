"""T021: the generic rules. Each returns findings, never raises, for any value (LSP)."""

import pytest

from language_kit.findings import Severity
from language_kit.rules import (
    AtLeast,
    DistinctLetters,
    EachWordCount,
    ExactCount,
    ExactlyOnePlaceholder,
    LowercaseWords,
    MatchesPattern,
    MinCount,
    OneOf,
    Present,
    Required,
    UniqueCasefold,
)
from tests.unit.language_kit.conftest import fake_context

CONTEXT = fake_context(code="de", path="podcast.guest_labels")
ODD_VALUES = (None, 3, 2.5, True, {"a": 1}, ["x", 1], [None], "", "TODO", [], {})
ALL_RULES = (
    Required(),
    Present(),
    MinCount(2),
    ExactCount(2),
    UniqueCasefold(),
    MatchesPattern(r"^[a-z]{2}$", "two lowercase letters"),
    OneOf(("female", "male")),
    ExactlyOnePlaceholder("{name}"),
    AtLeast(1),
    DistinctLetters(),
    EachWordCount(3, 15),
    LowercaseWords(),
)


def _errors(rule, value) -> list[str]:
    return [finding.detail for finding in rule.check(value, CONTEXT)]


@pytest.mark.parametrize("value", ["Gast", ["Gast"], 0, False])
def test_required_passes_a_value(value):
    assert _errors(Required(), value) == []


@pytest.mark.parametrize("value", [None, "", "   ", "TODO", [], {}])
def test_required_fails_a_missing_empty_or_todo_value(value):
    assert len(_errors(Required(), value)) == 1


@pytest.mark.parametrize("value", ["", [], "äöü"])
def test_present_allows_an_empty_value(value):
    assert _errors(Present(), value) == []


@pytest.mark.parametrize("value", [None, "TODO"])
def test_present_fails_a_missing_or_todo_value(value):
    assert len(_errors(Present(), value)) == 1


def test_min_count_reports_how_many_were_found():
    assert _errors(MinCount(2), ["a"]) == ["Found 1; add 1 more."]


def test_min_count_passes_enough_items():
    assert _errors(MinCount(2), ["a", "b", "c"]) == []


def test_exact_count_reports_too_many_and_too_few():
    assert _errors(ExactCount(2), ["a"]) == ["Found 1; add 1 more."]
    assert _errors(ExactCount(2), ["a", "b", "c"]) == ["Found 3; remove 1."]


def test_unique_casefold_names_the_repeated_value():
    (detail,) = _errors(UniqueCasefold(), ["Gast", "gast", "Moderator"])

    assert '"gast"' in detail


def test_unique_casefold_passes_distinct_values():
    assert _errors(UniqueCasefold(), ["Gast", "Moderator"]) == []


def test_matches_pattern_checks_a_string_and_shows_the_value():
    (detail,) = _errors(MatchesPattern(r"^[a-z]{2}$", "two lowercase letters"), "ESP")

    assert '"ESP"' in detail


def test_matches_pattern_checks_every_item_of_a_list():
    rule = MatchesPattern(r"\S", "each non-empty")

    assert len(_errors(rule, ["Gast", " ", ""])) == 2


def test_one_of_lists_the_allowed_values():
    (detail,) = _errors(OneOf(("female", "male")), "robot")

    assert '"robot"' in detail and '"female"' in detail


@pytest.mark.parametrize("line", ["Hallo, ich bin {name}.", "{name}!"])
def test_exactly_one_placeholder_passes_one_name(line):
    assert _errors(ExactlyOnePlaceholder("{name}"), line) == []


@pytest.mark.parametrize(
    "line", ["Hallo.", "{name} und {name}", "Hallo {name} {x}", "Hallo {name} }", "{nme}"]
)
def test_exactly_one_placeholder_fails_zero_two_or_other_braces(line):
    assert len(_errors(ExactlyOnePlaceholder("{name}"), line)) == 1


def test_at_least_refuses_a_smaller_number_and_a_boolean():
    assert _errors(AtLeast(1), 3) == []
    assert len(_errors(AtLeast(1), 0)) == 1
    assert len(_errors(AtLeast(1), True)) == 1


@pytest.mark.parametrize("letters", ["", "äöüß", "àèéìòù"])
def test_distinct_letters_passes_letters_or_nothing(letters):
    assert _errors(DistinctLetters(), letters) == []


@pytest.mark.parametrize("letters", ["ää", "ä1", "a b"])
def test_distinct_letters_fails_repeats_digits_and_spaces(letters):
    assert len(_errors(DistinctLetters(), letters)) == 1


def test_each_word_count_names_the_sentence_out_of_range():
    (detail,) = _errors(EachWordCount(3, 15), ["Ich bin hier.", "Hallo."])

    assert '"Hallo."' in detail and "1 word" in detail


def test_lowercase_words_refuses_capitals_and_several_words():
    assert _errors(LowercaseWords(), ["hotel", "café"]) == []
    assert len(_errors(LowercaseWords(), ["Hotel", "two words"])) == 2


@pytest.mark.parametrize("rule", ALL_RULES, ids=lambda rule: type(rule).__name__)
@pytest.mark.parametrize("value", ODD_VALUES, ids=repr)
def test_no_rule_raises_for_an_odd_value(rule, value):
    findings = rule.check(value, CONTEXT)

    assert all(finding.path.startswith("podcast.guest_labels") for finding in findings)


@pytest.mark.parametrize("rule", ALL_RULES, ids=lambda rule: type(rule).__name__)
def test_every_rule_describes_itself_in_a_short_sentence(rule):
    assert 0 < len(rule.describe()) <= 80


@pytest.mark.parametrize("rule", ALL_RULES, ids=lambda rule: type(rule).__name__)
def test_a_findings_names_the_rule_language_and_severity(rule):
    for finding in rule.check(None, CONTEXT):
        assert (finding.language, finding.severity) == ("de", Severity.ERROR)
        assert finding.rule
