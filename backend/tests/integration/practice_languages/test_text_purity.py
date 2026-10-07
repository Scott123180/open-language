"""T067/T083: the purity check on fixed strings, for any target language. Runs in CI."""

from tests.integration.practice_languages.text_purity import (
    foreign_words,
    loanwords,
    other_languages,
)

GERMAN = "de"
ITALIAN = "it"
GERMAN_OTHERS = ("en", "es")


def test_plain_german_with_a_loanword_has_no_flags():
    assert foreign_words("Ich möchte ein Hotel.", GERMAN, GERMAN_OTHERS) == []


def test_an_english_word_is_flagged():
    assert "the" in foreign_words("Ich möchte the menu.", GERMAN, GERMAN_OTHERS)


def test_a_spanish_word_is_flagged():
    assert "quiero" in foreign_words("Quiero un café, bitte.", GERMAN, GERMAN_OTHERS)


def test_capitalised_nouns_and_names_mid_sentence_are_not_flagged():
    text = "Wir fahren mit Maria nach Berlin ins Hotel Paradise."

    assert foreign_words(text, GERMAN, GERMAN_OTHERS) == []


def test_a_sentence_start_is_checked_in_lower_case():
    assert foreign_words("Ja. Please warten Sie.", GERMAN, GERMAN_OTHERS) == ["please"]


def test_common_german_words_shared_with_english_are_not_flagged():
    assert foreign_words("Also, was man so sagt, ist in Ordnung.", GERMAN, GERMAN_OTHERS) == []


def test_the_target_language_is_a_parameter():
    assert foreign_words("Vorrei un caffè, please.", ITALIAN, ("en",)) == ["please"]


def test_italian_words_are_flagged_in_german_when_italian_is_another_language():
    assert "vorrei" in foreign_words("Vorrei ein Wasser.", GERMAN, ("en", "es", "it"))


def test_other_languages_are_english_and_the_other_catalogued_languages():
    others = other_languages(GERMAN)

    assert others[0] == "en"
    assert "es" in others and GERMAN not in others


def test_loanwords_come_from_the_targets_evaluation_set():
    assert loanwords(GERMAN) == {"hotel", "ok", "taxi", "ticket"}


def test_a_language_without_an_evaluation_set_has_no_loanwords():
    assert loanwords("xx") == frozenset()
