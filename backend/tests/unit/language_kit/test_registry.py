"""T024: the requirement registry (data-model.md § Requirement)."""

import pytest

from language_kit.registry import REQUIREMENTS, Destination, Producer, requirement
from language_kit.rules import (
    AtLeast,
    CoversEveryScenario,
    DistinctLetters,
    EachContainsSpecialLetter,
    EachWordCount,
    ExactCount,
    ExactlyOnePlaceholder,
    LowercaseWords,
    MatchesPattern,
    MinCount,
    NamesForEveryVoiceGender,
    OneOf,
    Present,
    Required,
    UniqueAcrossLanguages,
    UniqueCasefold,
)

R, E = Destination.RUNTIME, Destination.EVALUATION
A, C, D = Producer.AGENT, Producer.CHOSEN, Producer.DERIVED
EXPECTED = (
    ("code", R, D, "006"),
    ("name", R, A, "006"),
    ("order", R, D, "008"),
    ("voices", R, C, "006"),
    ("voices[].gender", R, A, "007"),
    ("voices[].speaking_rate", R, A, "006"),
    ("default_voice", R, C, "006"),
    ("podcast.host_names", R, A, "007"),
    ("podcast.guest_labels", R, A, "007"),
    ("podcast.sample_line", R, A, "007"),
    ("evaluation.special_letters", E, A, "006"),
    ("evaluation.turns", E, A, "006"),
    ("evaluation.dictation", E, A, "006"),
    ("evaluation.loanwords", E, A, "006"),
)


def _rule(path: str, kind: type):
    return next(rule for rule in requirement(path).rules if isinstance(rule, kind))


def test_the_registry_holds_the_fourteen_requirements_in_order():
    actual = tuple((r.path, r.destination, r.producer, r.needed_by) for r in REQUIREMENTS)

    assert actual == EXPECTED


@pytest.mark.parametrize("item", REQUIREMENTS, ids=lambda item: item.path)
def test_every_requirement_has_a_description_and_a_rule(item):
    assert item.description.strip()
    assert item.rules


def test_no_requirement_is_onboarding_only_so_check_runs_them_all():
    assert not any(item.onboarding_only for item in REQUIREMENTS)


def test_code_is_two_lowercase_letters():
    assert _rule("code", MatchesPattern).describe() == "ISO 639-1, two lowercase letters"


def test_name_is_required_and_unique_across_languages():
    assert _rule("name", Required) and _rule("name", UniqueAcrossLanguages)


def test_order_is_at_least_one_and_unique():
    assert _rule("order", AtLeast).minimum == 1
    assert _rule("order", UniqueAcrossLanguages)


def test_voices_are_at_least_one_with_keys_unique_across_languages():
    assert _rule("voices", MinCount).minimum == 1
    assert _rule("voices", UniqueAcrossLanguages).item_key == "key"


def test_voice_gender_is_female_or_male():
    assert _rule("voices[].gender", OneOf).values == ("female", "male")


def test_voice_speaking_rate_is_natural_fast_or_slow():
    assert _rule("voices[].speaking_rate", OneOf).values == ("natural", "fast", "slow")


def test_host_names_need_ten_per_voice_gender():
    assert _rule("podcast.host_names", NamesForEveryVoiceGender).minimum == 10


def test_guest_labels_are_one_or_more_unique_and_non_empty():
    assert _rule("podcast.guest_labels", MinCount).minimum == 1
    assert _rule("podcast.guest_labels", UniqueCasefold)
    assert _rule("podcast.guest_labels", MatchesPattern).describe() == "each non-empty"


def test_the_sample_line_holds_one_name_placeholder():
    assert _rule("podcast.sample_line", ExactlyOnePlaceholder).placeholder == "{name}"


def test_special_letters_may_be_empty_but_are_distinct_letters():
    assert _rule("evaluation.special_letters", Present)
    assert _rule("evaluation.special_letters", DistinctLetters)


def test_turns_cover_every_scenario_with_five_turns():
    assert _rule("evaluation.turns", CoversEveryScenario).turns == 5


def test_dictation_is_twenty_unique_sentences_of_three_to_fifteen_words():
    assert _rule("evaluation.dictation", ExactCount).count == 20
    assert _rule("evaluation.dictation", UniqueCasefold)
    word_count = _rule("evaluation.dictation", EachWordCount)
    assert (word_count.minimum, word_count.maximum) == (3, 15)
    assert _rule("evaluation.dictation", EachContainsSpecialLetter)


def test_loanwords_may_be_empty_but_are_lowercase_single_words():
    assert _rule("evaluation.loanwords", Present)
    assert _rule("evaluation.loanwords", LowercaseWords)


def test_an_unknown_path_is_a_lookup_error():
    with pytest.raises(KeyError):
        requirement("podcast.greeting")
