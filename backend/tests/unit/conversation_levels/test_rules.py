"""The two rule renderers: Natural is byte-identical, other levels append a block (data-model §4)."""

import pytest

from app.conversation_levels import (
    LEVEL_CATALOG,
    ConversationLevel,
    with_learner_text_rules,
    with_partner_speech_rules,
)

PROMPT = "You are a waiter in Madrid.\nCRITICAL LANGUAGE RULE: reply only in Spanish."
LIMITED_LEVELS = (
    ConversationLevel.BEGINNER,
    ConversationLevel.ELEMENTARY,
    ConversationLevel.INTERMEDIATE,
)
RENDERERS = (with_partner_speech_rules, with_learner_text_rules)
PRECEDENCE_LINE = "These rules about how you speak override anything above."


def _block(render, level: ConversationLevel) -> str:
    rendered = render(PROMPT, level)
    assert rendered.startswith(PROMPT + "\n\n")
    return rendered.removeprefix(PROMPT + "\n\n")


def _limits(level: ConversationLevel):
    limits = LEVEL_CATALOG[level].limits
    assert limits is not None
    return limits


class TestNaturalIsUnchanged:
    @pytest.mark.parametrize("render", RENDERERS)
    def test_returns_the_prompt_byte_for_byte(self, render):
        assert render(PROMPT, ConversationLevel.NATURAL) == PROMPT

    @pytest.mark.parametrize("render", RENDERERS)
    def test_an_empty_prompt_stays_empty(self, render):
        assert render("", ConversationLevel.NATURAL) == ""


class TestBothRenderersAppendABlock:
    @pytest.mark.parametrize("render", RENDERERS)
    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_prompt_comes_first_and_the_block_last(self, render, level):
        block = _block(render, level)

        assert block.strip()
        assert PROMPT not in block

    @pytest.mark.parametrize("render", RENDERERS)
    def test_blocks_differ_between_levels(self, render):
        blocks = {_block(render, level) for level in LIMITED_LEVELS}

        assert len(blocks) == len(LIMITED_LEVELS)

    @pytest.mark.parametrize("render", RENDERERS)
    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    @pytest.mark.parametrize("forbidden", ["native", "english"])
    def test_never_mentions_the_native_language(self, render, level, forbidden):
        assert forbidden not in _block(render, level).lower()

    @pytest.mark.parametrize("render", RENDERERS)
    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    @pytest.mark.parametrize("native_language", ["en", "fr", "de"])
    def test_carries_no_native_language_value(self, render, level, native_language):
        words = _block(render, level).lower().replace(".", " ").replace(",", " ").split()

        assert native_language not in words


class TestPartnerSpeechBlock:
    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_opens_with_the_precedence_line(self, level):
        block = _block(with_partner_speech_rules, level)

        assert block.splitlines()[0] == PRECEDENCE_LINE

    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_states_the_numeric_limits_from_the_catalogue(self, level):
        block = _block(with_partner_speech_rules, level)
        limits = _limits(level)

        assert f"at most {limits.max_sentences_per_reply} sentences" in block
        assert f"at most {limits.max_words_per_sentence} words" in block
        assert f"{limits.vocabulary_rank} most common words" in block

    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    @pytest.mark.parametrize("field", ["sentence_joining", "tenses", "idioms", "questions"])
    def test_states_each_descriptive_limit(self, level, field):
        assert getattr(_limits(level), field) in _block(with_partner_speech_rules, level)

    @pytest.mark.parametrize(
        "phrase",
        [
            "more simply",  # FR-005, the ceiling rule
            "never more complexly",
            "essential to the scenario",  # FR-012 (a)
            "the learner has just used",  # FR-012 (b)
            "answer what the learner said",  # FR-013
            "even simpler",  # FR-014
        ],
    )
    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_carries_the_ceiling_exception_and_behaviour_rules(self, level, phrase):
        assert phrase in _block(with_partner_speech_rules, level)


class TestLearnerTextBlock:
    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_limits_the_words_the_learner_will_say_or_read(self, level):
        block = _block(with_learner_text_rules, level)

        assert "the target-language words the learner will say or read" in block

    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_states_sentence_length_tenses_vocabulary_and_idioms(self, level):
        block = _block(with_learner_text_rules, level)
        limits = _limits(level)

        assert f"at most {limits.max_words_per_sentence} words" in block
        assert f"{limits.vocabulary_rank} most common words" in block
        assert limits.sentence_joining in block
        assert limits.tenses in block
        assert limits.idioms in block

    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_leaves_out_reply_length_and_question_rules(self, level):
        block = _block(with_learner_text_rules, level)
        limits = _limits(level)

        assert "per reply" not in block
        assert "sentences per" not in block
        assert limits.questions not in block
        assert "question" not in block.lower()

    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_says_explanations_in_other_languages_are_not_limited(self, level):
        block = _block(with_learner_text_rules, level)

        assert "Explanations in any other language are not limited" in block
