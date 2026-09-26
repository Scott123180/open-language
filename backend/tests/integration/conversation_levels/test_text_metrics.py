"""T034: the benchmark's measures are right before any model output is judged by them."""

import pytest

from tests.integration.conversation_levels.text_metrics import (
    mean_words_per_sentence,
    meets_length_limits,
    native_language_words,
    share_outside,
    split_sentences,
    words,
    words_per_sentence,
)


class TestSplitSentences:
    @pytest.mark.parametrize(
        ("text", "count"),
        [
            ("Hola.", 1),
            ("Hola. ¿Qué tal?", 2),
            ("¡Bienvenido! Siéntese aquí. ¿Qué quiere tomar?", 3),
            ("Bueno… vale.", 2),
            ("Hola.¿Qué tal?", 2),
            ("Sin punto final", 1),
            ("", 0),
            ("  …  ", 0),
        ],
    )
    def test_counts_sentences(self, text, count):
        assert len(split_sentences(text)) == count

    def test_keeps_inverted_question_marks_with_their_sentence(self):
        assert split_sentences("Hola. ¿Quiere café?") == ["Hola.", "¿Quiere café?"]

    def test_keeps_inverted_exclamation_marks_with_their_sentence(self):
        assert split_sentences("¡Qué bien! Gracias.") == ["¡Qué bien!", "Gracias."]


class TestWords:
    def test_counts_unicode_letters_only(self):
        assert words("¿Quiere un café, señora? Son 3 euros.") == [
            "Quiere",
            "un",
            "café",
            "señora",
            "Son",
            "euros",
        ]

    def test_words_per_sentence(self):
        assert words_per_sentence("Hola. ¿Quiere un café con leche?") == [1, 5]

    def test_mean_words_per_sentence_spans_every_reply(self):
        assert mean_words_per_sentence(["Hola.", "Un café con leche."]) == 2.5

    def test_mean_of_nothing_is_zero(self):
        assert mean_words_per_sentence([]) == 0.0


class TestLengthLimits:
    def test_a_reply_within_both_limits_passes(self):
        assert meets_length_limits("Hola. ¿Quiere café?", 2, 8)

    def test_too_many_sentences_fails(self):
        assert not meets_length_limits("Hola. Bien. ¿Café?", 2, 8)

    def test_a_long_sentence_fails(self):
        assert not meets_length_limits("Hoy tenemos una sopa muy rica de tomate con pan.", 2, 8)


class TestShareOutside:
    def test_counts_words_missing_from_the_common_set(self):
        assert share_outside(["El café", "El té"], frozenset({"el", "café"})) == 0.25

    def test_empty_text_has_no_share(self):
        assert share_outside([""], frozenset()) == 0.0


class TestNativeLanguageWords:
    def test_flags_english_function_words(self):
        assert native_language_words("Claro, the menu is aquí.") == ["the", "is"]

    @pytest.mark.parametrize("text", ["No, me gusta a la playa.", "¿Quiere un café con leche?"])
    def test_ignores_words_shared_with_spanish(self, text):
        assert native_language_words(text) == []
