"""The conversation level catalogue: fixed, ordered, and internally consistent (005 data-model §1–3)."""

from dataclasses import FrozenInstanceError, replace

import pytest

import app.conversation_levels
from app.conversation_levels import (
    DEFAULT_CONVERSATION_LEVEL,
    LEVEL_CATALOG,
    ConversationLevel,
)
from app.conversation_levels.catalog import LevelDescriptor, SpeechLimits

LIMITED_LEVELS = (
    ConversationLevel.BEGINNER,
    ConversationLevel.ELEMENTARY,
    ConversationLevel.INTERMEDIATE,
)
INTEGER_FIELDS = ("max_sentences_per_reply", "max_words_per_sentence", "vocabulary_rank")


def _limits(level: ConversationLevel) -> SpeechLimits:
    limits = LEVEL_CATALOG[level].limits
    assert limits is not None
    return limits


class TestConversationLevel:
    def test_is_a_str_enum_with_the_four_values_in_order(self):
        assert [level.value for level in ConversationLevel] == [
            "beginner",
            "elementary",
            "intermediate",
            "natural",
        ]

    def test_values_are_plain_strings(self):
        assert ConversationLevel.BEGINNER == "beginner"

    def test_default_is_natural(self):
        assert DEFAULT_CONVERSATION_LEVEL is ConversationLevel.NATURAL


class TestLevelCatalog:
    def test_keys_iterate_in_declaration_order(self):
        assert list(LEVEL_CATALOG) == list(ConversationLevel)

    def test_labels_are_the_level_names(self):
        labels = [descriptor.label for descriptor in LEVEL_CATALOG.values()]

        assert labels == ["Beginner", "Elementary", "Intermediate", "Natural"]

    def test_cefr_labels_follow_the_scale(self):
        cefr = [descriptor.cefr_label for descriptor in LEVEL_CATALOG.values()]

        assert cefr == ["A1", "A2", "B1", "No limit"]

    @pytest.mark.parametrize("level", list(ConversationLevel))
    def test_each_description_is_one_non_empty_sentence(self, level):
        description = LEVEL_CATALOG[level].description

        assert description.strip()
        assert description.endswith(".")
        assert description.count(".") == 1

    def test_each_descriptor_is_keyed_by_its_own_level(self):
        assert all(level is d.level for level, d in LEVEL_CATALOG.items())

    def test_beginner_description_reads_like_talking_with_a_child(self):
        assert LEVEL_CATALOG[ConversationLevel.BEGINNER].description == (
            "Very short, simple sentences — like talking with a young child."
        )

    def test_the_catalogue_cannot_be_modified(self):
        with pytest.raises(TypeError):
            LEVEL_CATALOG[ConversationLevel.NATURAL] = None  # type: ignore[index]

    def test_natural_has_no_limits(self):
        assert LEVEL_CATALOG[ConversationLevel.NATURAL].limits is None

    @pytest.mark.parametrize(
        ("level", "sentences", "words", "rank"),
        [
            (ConversationLevel.BEGINNER, 2, 8, 500),
            (ConversationLevel.ELEMENTARY, 3, 12, 1500),
            (ConversationLevel.INTERMEDIATE, 4, 20, 3000),
        ],
    )
    def test_numeric_limits_match_the_data_model(self, level, sentences, words, rank):
        limits = _limits(level)

        assert (
            limits.max_sentences_per_reply,
            limits.max_words_per_sentence,
            limits.vocabulary_rank,
        ) == (sentences, words, rank)

    @pytest.mark.parametrize("level", LIMITED_LEVELS)
    def test_every_integer_limit_in_the_catalogue_is_positive(self, level):
        limits = _limits(level)

        assert all(getattr(limits, field) > 0 for field in INTEGER_FIELDS)

    @pytest.mark.parametrize("field", ["max_words_per_sentence", "vocabulary_rank"])
    def test_complexity_limits_strictly_increase_from_beginner_to_intermediate(self, field):
        values = [getattr(_limits(level), field) for level in LIMITED_LEVELS]

        assert values == sorted(values)
        assert len(set(values)) == len(values)

    def test_beginner_text_limits_match_the_data_model(self):
        limits = _limits(ConversationLevel.BEGINNER)

        assert (limits.sentence_joining, limits.tenses, limits.idioms, limits.questions) == (
            "one idea per sentence",
            "present tense only",
            "none",
            "one easy yes/no or either/or question",
        )


class TestSpeechLimitsInvariants:
    @pytest.mark.parametrize("field", INTEGER_FIELDS)
    @pytest.mark.parametrize("bad_value", [0, -1])
    def test_rejects_a_non_positive_integer(self, field, bad_value):
        with pytest.raises(ValueError, match=field):
            replace(_limits(ConversationLevel.BEGINNER), **{field: bad_value})

    def test_is_frozen(self):
        with pytest.raises(FrozenInstanceError):
            _limits(ConversationLevel.BEGINNER).max_words_per_sentence = 99  # type: ignore[misc]


class TestLevelDescriptorInvariants:
    def test_natural_with_limits_is_rejected(self):
        with pytest.raises(ValueError, match="natural"):
            replace(
                LEVEL_CATALOG[ConversationLevel.NATURAL],
                limits=_limits(ConversationLevel.BEGINNER),
            )

    def test_a_limited_level_without_limits_is_rejected(self):
        with pytest.raises(ValueError, match="beginner"):
            replace(LEVEL_CATALOG[ConversationLevel.BEGINNER], limits=None)

    def test_is_frozen(self):
        descriptor: LevelDescriptor = LEVEL_CATALOG[ConversationLevel.BEGINNER]

        with pytest.raises(FrozenInstanceError):
            descriptor.label = "Easy"  # type: ignore[misc]


def test_the_module_exports_exactly_five_public_names():
    assert set(app.conversation_levels.__all__) == {
        "ConversationLevel",
        "DEFAULT_CONVERSATION_LEVEL",
        "LEVEL_CATALOG",
        "with_partner_speech_rules",
        "with_learner_text_rules",
    }
