"""DeckGenerationService + AlgorithmStrategy implementations.

Uses the Strategy pattern (OCP): adding a new algorithm requires registering
a new strategy — no modification to existing code.

Algorithms:
  not_practiced       — prioritize NOT_PRACTICED → DIFFICULT → ALMOST_LEARNED
  difficult           — prioritize DIFFICULT → NOT_PRACTICED → ALMOST_LEARNED
  previously_guessed  — prioritize ALMOST_LEARNED → DIFFICULT → NOT_PRACTICED
  mixed_review        — 40% DIFFICULT, 30% ALMOST_LEARNED, 20% NOT_PRACTICED, 10% LEARNED
"""

from __future__ import annotations

import random
from typing import Protocol

from app.flashcards.services.storage import WordRecord

_CLASSIFICATION_ORDER = {
    "not_practiced": 0,
    "difficult": 1,
    "almost_learned": 2,
    "learned": 3,
}


class AlgorithmStrategy(Protocol):
    def select(self, pool: list[WordRecord], size: int) -> list[WordRecord]:
        """Return up to `size` words selected according to this algorithm."""
        ...


def _pick_random(words: list[WordRecord], n: int) -> list[WordRecord]:
    return random.sample(words, min(n, len(words)))


def _tier_fill(tiers: list[list[WordRecord]], size: int) -> list[WordRecord]:
    """Fill `size` slots from tiers in order; each tier is randomly sampled."""
    result: list[WordRecord] = []
    remaining = size
    for tier in tiers:
        if remaining <= 0:
            break
        picked = _pick_random(tier, remaining)
        result.extend(picked)
        remaining -= len(picked)
    return result


class _NotPracticedStrategy:
    def select(self, pool: list[WordRecord], size: int) -> list[WordRecord]:
        by_classification: dict[str, list[WordRecord]] = {
            "not_practiced": [],
            "difficult": [],
            "almost_learned": [],
            "learned": [],
        }
        for w in pool:
            bucket = by_classification.get(w.classification)
            if bucket is not None:
                bucket.append(w)
        return _tier_fill(
            [
                by_classification["not_practiced"],
                by_classification["difficult"],
                by_classification["almost_learned"],
            ],
            size,
        )


class _DifficultStrategy:
    def select(self, pool: list[WordRecord], size: int) -> list[WordRecord]:
        by_classification: dict[str, list[WordRecord]] = {
            "not_practiced": [],
            "difficult": [],
            "almost_learned": [],
            "learned": [],
        }
        for w in pool:
            bucket = by_classification.get(w.classification)
            if bucket is not None:
                bucket.append(w)
        return _tier_fill(
            [
                by_classification["difficult"],
                by_classification["not_practiced"],
                by_classification["almost_learned"],
            ],
            size,
        )


class _PreviouslyGuessedStrategy:
    def select(self, pool: list[WordRecord], size: int) -> list[WordRecord]:
        by_classification: dict[str, list[WordRecord]] = {
            "not_practiced": [],
            "difficult": [],
            "almost_learned": [],
            "learned": [],
        }
        for w in pool:
            bucket = by_classification.get(w.classification)
            if bucket is not None:
                bucket.append(w)
        return _tier_fill(
            [
                by_classification["almost_learned"],
                by_classification["difficult"],
                by_classification["not_practiced"],
            ],
            size,
        )


class _MixedReviewStrategy:
    """40% difficult, 30% almost_learned, 20% not_practiced, 10% learned.

    Ratios are applied to requested size; remainder distributed to non-empty tiers.
    """

    _RATIOS = {
        "difficult": 0.40,
        "almost_learned": 0.30,
        "not_practiced": 0.20,
        "learned": 0.10,
    }

    def select(self, pool: list[WordRecord], size: int) -> list[WordRecord]:
        by_classification: dict[str, list[WordRecord]] = {
            "not_practiced": [],
            "difficult": [],
            "almost_learned": [],
            "learned": [],
        }
        for w in pool:
            bucket = by_classification.get(w.classification)
            if bucket is not None:
                bucket.append(w)

        result: list[WordRecord] = []
        quotas = {cls: max(1, round(size * ratio)) for cls, ratio in self._RATIOS.items()}
        leftover: list[WordRecord] = []

        for cls, quota in quotas.items():
            available = by_classification[cls]
            picked = _pick_random(available, quota)
            result.extend(picked)
            leftover.extend(w for w in available if w not in picked)

        # Fill remaining slots from leftovers if under target size
        if len(result) < size:
            extra = _pick_random(leftover, size - len(result))
            result.extend(extra)

        return result[:size]


_STRATEGIES: dict[str, AlgorithmStrategy] = {
    "not_practiced": _NotPracticedStrategy(),
    "difficult": _DifficultStrategy(),
    "previously_guessed": _PreviouslyGuessedStrategy(),
    "mixed_review": _MixedReviewStrategy(),
}


class DeckGenerationService:
    """Select words from a pool using a named algorithm strategy."""

    def select_words(
        self,
        pool: list[WordRecord],
        size: int,
        algorithm: str,
    ) -> list[WordRecord]:
        """Return up to `size` words selected by `algorithm`.

        Falls back to random selection if the algorithm name is unknown.
        """
        strategy = _STRATEGIES.get(algorithm)
        if strategy is None:
            return _pick_random(pool, size)
        return strategy.select(pool, size)
