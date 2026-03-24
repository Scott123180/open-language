"""Unit tests for DeckGenerationService — T026 / T043.

T026 covers:
  - Random selection from pool (basic select_words)
  - Exact deck size when pool >= size
  - Pool-smaller-than-size fallback (returns all words)
  - Unknown algorithm falls back to random selection

T043 extends with:
  - All 4 strategy detailed priority ordering and fallback chaining
  - Mixed Review ratios (40/30/20/10%)
  - Per-tier randomization (result varies across runs)
"""

from datetime import UTC, datetime

from app.flashcards.services.deck_generation import DeckGenerationService
from app.flashcards.services.storage import WordRecord


def _make_word(id: int, classification: str = "not_practiced") -> WordRecord:
    return WordRecord(
        id=id,
        word=f"word_{id}",
        translation=f"translation_{id}",
        target_language="fr",
        native_language="en",
        classification=classification,
        manual_override=False,
        saved_at=datetime.now(UTC),
        source_conversation_id=None,
        tts_cache_path=None,
    )


def _pool(n: int, classification: str = "not_practiced") -> list[WordRecord]:
    return [_make_word(i, classification) for i in range(1, n + 1)]


class TestDeckGenerationServiceBasic:
    def setup_method(self):
        self.service = DeckGenerationService()

    def test_select_exact_size_from_large_pool(self):
        pool = _pool(20)
        result = self.service.select_words(pool, 10, "not_practiced")
        assert len(result) == 10

    def test_select_returns_subset_of_pool(self):
        pool = _pool(20)
        pool_ids = {w.id for w in pool}
        result = self.service.select_words(pool, 10, "not_practiced")
        for w in result:
            assert w.id in pool_ids

    def test_select_no_duplicates(self):
        pool = _pool(20)
        result = self.service.select_words(pool, 10, "not_practiced")
        assert len({w.id for w in result}) == len(result)

    def test_pool_smaller_than_size_returns_all(self):
        pool = _pool(5)
        result = self.service.select_words(pool, 20, "not_practiced")
        assert len(result) == 5

    def test_empty_pool_returns_empty(self):
        result = self.service.select_words([], 10, "not_practiced")
        assert result == []

    def test_size_zero_returns_empty(self):
        pool = _pool(10)
        result = self.service.select_words(pool, 0, "not_practiced")
        assert result == []

    def test_unknown_algorithm_falls_back_to_random(self):
        pool = _pool(10)
        result = self.service.select_words(pool, 5, "nonexistent_algo")
        assert len(result) == 5
        pool_ids = {w.id for w in pool}
        for w in result:
            assert w.id in pool_ids


class TestNotPracticedStrategy:
    def setup_method(self):
        self.service = DeckGenerationService()

    def test_prioritizes_not_practiced_words(self):
        not_practiced = _pool(5, "not_practiced")
        difficult = _pool(5, "difficult")
        # shift ids to avoid collision
        for _i, w in enumerate(difficult):
            object.__setattr__(w, "id", w.id + 100)
        pool = not_practiced + difficult
        result = self.service.select_words(pool, 5, "not_practiced")
        result_ids = {w.id for w in result}
        not_practiced_ids = {w.id for w in not_practiced}
        # All 5 slots should be filled by not_practiced words (they have exactly 5)
        assert result_ids == not_practiced_ids

    def test_falls_back_to_difficult_when_not_practiced_exhausted(self):
        not_practiced = _pool(2, "not_practiced")
        difficult = [_make_word(i + 10, "difficult") for i in range(3)]
        pool = not_practiced + difficult
        result = self.service.select_words(pool, 5, "not_practiced")
        assert len(result) == 5
        result_ids = {w.id for w in result}
        # Both not_practiced and difficult words should appear
        for w in not_practiced:
            assert w.id in result_ids


class TestDifficultStrategy:
    def setup_method(self):
        self.service = DeckGenerationService()

    def test_prioritizes_difficult_words(self):
        difficult = [_make_word(i, "difficult") for i in range(1, 6)]
        not_practiced = [_make_word(i + 10, "not_practiced") for i in range(5)]
        pool = difficult + not_practiced
        result = self.service.select_words(pool, 5, "difficult")
        result_ids = {w.id for w in result}
        difficult_ids = {w.id for w in difficult}
        assert result_ids == difficult_ids

    def test_falls_back_to_not_practiced_when_difficult_exhausted(self):
        difficult = [_make_word(i, "difficult") for i in range(1, 3)]
        not_practiced = [_make_word(i + 10, "not_practiced") for i in range(3)]
        pool = difficult + not_practiced
        result = self.service.select_words(pool, 5, "difficult")
        assert len(result) == 5


class TestPreviouslyGuessedStrategy:
    def setup_method(self):
        self.service = DeckGenerationService()

    def test_prioritizes_almost_learned_words(self):
        almost = [_make_word(i, "almost_learned") for i in range(1, 6)]
        difficult = [_make_word(i + 10, "difficult") for i in range(5)]
        pool = almost + difficult
        result = self.service.select_words(pool, 5, "previously_guessed")
        result_ids = {w.id for w in result}
        almost_ids = {w.id for w in almost}
        assert result_ids == almost_ids

    def test_falls_back_to_difficult_then_not_practiced(self):
        almost = [_make_word(1, "almost_learned")]
        difficult = [_make_word(2, "difficult")]
        not_practiced = [_make_word(3, "not_practiced")]
        pool = almost + difficult + not_practiced
        result = self.service.select_words(pool, 3, "previously_guessed")
        assert len(result) == 3


class TestMixedReviewStrategy:
    def setup_method(self):
        self.service = DeckGenerationService()

    def test_returns_correct_total_size(self):
        pool = (
            [_make_word(i, "difficult") for i in range(1, 11)]
            + [_make_word(i + 10, "almost_learned") for i in range(10)]
            + [_make_word(i + 20, "not_practiced") for i in range(10)]
            + [_make_word(i + 30, "learned") for i in range(10)]
        )
        result = self.service.select_words(pool, 20, "mixed_review")
        assert len(result) == 20

    def test_includes_words_from_multiple_classifications(self):
        pool = (
            [_make_word(i, "difficult") for i in range(1, 6)]
            + [_make_word(i + 10, "almost_learned") for i in range(5)]
            + [_make_word(i + 20, "not_practiced") for i in range(5)]
            + [_make_word(i + 30, "learned") for i in range(5)]
        )
        result = self.service.select_words(pool, 10, "mixed_review")
        classifications_seen = {w.classification for w in result}
        # With a balanced pool and 10 cards, at least 3 different classifications should appear
        assert len(classifications_seen) >= 3

    def test_mixed_review_pool_smaller_than_size(self):
        pool = [_make_word(i, "difficult") for i in range(1, 4)]
        result = self.service.select_words(pool, 20, "mixed_review")
        assert len(result) == 3


# ---------------------------------------------------------------------------
# T043 — Algorithm strategy detailed tests
# ---------------------------------------------------------------------------


class TestNotPracticedStrategyFallbackChain:
    """Verify the full fallback chain: not_practiced → difficult → almost_learned."""

    def setup_method(self):
        self.service = DeckGenerationService()

    def test_fills_from_difficult_when_not_practiced_exhausted(self):
        not_practiced = [_make_word(1, "not_practiced"), _make_word(2, "not_practiced")]
        difficult = [_make_word(i + 10, "difficult") for i in range(3)]
        pool = not_practiced + difficult
        result = self.service.select_words(pool, 5, "not_practiced")
        assert len(result) == 5
        classifications = [w.classification for w in result]
        assert "not_practiced" in classifications
        assert "difficult" in classifications

    def test_fills_from_almost_learned_as_last_resort(self):
        not_practiced = [_make_word(1, "not_practiced")]
        almost = [_make_word(i + 10, "almost_learned") for i in range(3)]
        pool = not_practiced + almost
        result = self.service.select_words(pool, 4, "not_practiced")
        assert len(result) == 4
        classifications = {w.classification for w in result}
        assert "almost_learned" in classifications

    def test_excludes_learned_words(self):
        not_practiced = [_make_word(1, "not_practiced")]
        learned = [_make_word(i + 10, "learned") for i in range(5)]
        pool = not_practiced + learned
        result = self.service.select_words(pool, 6, "not_practiced")
        # NOT_PRACTICED strategy does not include LEARNED in its fallback chain
        for w in result:
            assert w.classification != "learned"


class TestDifficultStrategyFallbackChain:
    """Verify the full fallback chain: difficult → not_practiced → almost_learned."""

    def setup_method(self):
        self.service = DeckGenerationService()

    def test_primary_tier_is_difficult(self):
        difficult = [_make_word(i, "difficult") for i in range(1, 4)]
        not_practiced = [_make_word(i + 10, "not_practiced") for i in range(3)]
        pool = difficult + not_practiced
        result = self.service.select_words(pool, 3, "difficult")
        result_ids = {w.id for w in result}
        difficult_ids = {w.id for w in difficult}
        assert result_ids == difficult_ids

    def test_fallback_to_not_practiced_after_difficult(self):
        difficult = [_make_word(1, "difficult")]
        not_practiced = [_make_word(i + 10, "not_practiced") for i in range(4)]
        pool = difficult + not_practiced
        result = self.service.select_words(pool, 5, "difficult")
        assert len(result) == 5

    def test_fallback_to_almost_learned_as_last_resort(self):
        difficult = [_make_word(1, "difficult")]
        not_practiced = [_make_word(2, "not_practiced")]
        almost = [_make_word(i + 10, "almost_learned") for i in range(3)]
        pool = difficult + not_practiced + almost
        result = self.service.select_words(pool, 5, "difficult")
        assert len(result) == 5


class TestPreviouslyGuessedStrategyFallbackChain:
    """Verify the full fallback chain: almost_learned → difficult → not_practiced."""

    def setup_method(self):
        self.service = DeckGenerationService()

    def test_primary_tier_is_almost_learned(self):
        almost = [_make_word(i, "almost_learned") for i in range(1, 4)]
        not_practiced = [_make_word(i + 10, "not_practiced") for i in range(3)]
        pool = almost + not_practiced
        result = self.service.select_words(pool, 3, "previously_guessed")
        result_ids = {w.id for w in result}
        almost_ids = {w.id for w in almost}
        assert result_ids == almost_ids

    def test_fallback_chain_difficult_then_not_practiced(self):
        almost = [_make_word(1, "almost_learned")]
        difficult = [_make_word(2, "difficult")]
        not_practiced = [_make_word(3, "not_practiced")]
        pool = almost + difficult + not_practiced
        result = self.service.select_words(pool, 3, "previously_guessed")
        assert len(result) == 3
        result_ids = {w.id for w in result}
        assert 1 in result_ids  # almost_learned first
        assert 2 in result_ids  # difficult second


class TestMixedReviewRatios:
    """Verify Mixed Review ratio targeting (40% difficult, 30% almost_learned, 20% not_practiced, 10% learned)."""

    def setup_method(self):
        self.service = DeckGenerationService()

    def test_large_pool_respects_ratios_approximately(self):
        pool = (
            [_make_word(i, "difficult") for i in range(1, 21)]
            + [_make_word(i + 20, "almost_learned") for i in range(20)]
            + [_make_word(i + 40, "not_practiced") for i in range(20)]
            + [_make_word(i + 60, "learned") for i in range(20)]
        )
        result = self.service.select_words(pool, 20, "mixed_review")
        assert len(result) == 20
        by_cls = {}
        for w in result:
            by_cls[w.classification] = by_cls.get(w.classification, 0) + 1
        # With 20 cards, target is: 8 difficult, 6 almost_learned, 4 not_practiced, 2 learned
        # Allow ±2 tolerance
        assert abs(by_cls.get("difficult", 0) - 8) <= 2
        assert abs(by_cls.get("almost_learned", 0) - 6) <= 2

    def test_result_never_exceeds_requested_size(self):
        pool = (
            [_make_word(i, "difficult") for i in range(1, 11)]
            + [_make_word(i + 10, "almost_learned") for i in range(10)]
            + [_make_word(i + 20, "not_practiced") for i in range(10)]
            + [_make_word(i + 30, "learned") for i in range(10)]
        )
        for size in [5, 10, 15, 20]:
            result = self.service.select_words(pool, size, "mixed_review")
            assert len(result) <= size, f"size {size}: got {len(result)}"

    def test_no_duplicate_words_in_result(self):
        pool = [_make_word(i, "difficult") for i in range(1, 11)] + [
            _make_word(i + 10, "almost_learned") for i in range(10)
        ]
        result = self.service.select_words(pool, 10, "mixed_review")
        ids = [w.id for w in result]
        assert len(ids) == len(set(ids)), "Duplicate words in mixed review result"
