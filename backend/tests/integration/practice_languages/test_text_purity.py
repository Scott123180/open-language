"""T067: the SC-002 purity check on fixed strings. Runs in CI."""

from tests.integration.practice_languages.text_purity import foreign_words


def test_plain_german_with_a_loanword_has_no_flags():
    assert foreign_words("Ich möchte ein Hotel.") == []


def test_an_english_word_is_flagged():
    assert "the" in foreign_words("Ich möchte the menu.")


def test_a_spanish_word_is_flagged():
    assert "quiero" in foreign_words("Quiero un café, bitte.")


def test_capitalised_nouns_and_names_mid_sentence_are_not_flagged():
    assert foreign_words("Wir fahren mit Maria nach Berlin ins Hotel Paradise.") == []


def test_a_sentence_start_is_checked_in_lower_case():
    assert foreign_words("Ja. Please warten Sie.") == ["please"]


def test_common_german_words_shared_with_english_are_not_flagged():
    assert foreign_words("Also, was man so sagt, ist in Ordnung.") == []
