"""Unit tests for ClassificationEngine.recalculate() — T025 / T058.

T025 covers all 5 transition rules with priority ordering:
  Rule 1: 3+ consecutive KNEW_IT → LEARNED (highest priority)
  Rule 2: Regression — was LEARNED, most recent = DIDNT_KNOW → DIFFICULT
  Rule 3: 2+ DIDNT_KNOW in last 5 → DIFFICULT
  Rule 4: ≥3 positive (GUESSED/KNEW_IT), ≥1 GUESSED, no 3-streak → ALMOST_LEARNED
  Rule 5: Default — keep current or NOT_PRACTICED

T058 extends with priority conflict edge cases and threshold boundaries.
"""

from app.flashcards.services.classification import recalculate

# ---------------------------------------------------------------------------
# Rule 1 — 3+ consecutive KNEW_IT → LEARNED
# ---------------------------------------------------------------------------


def test_three_consecutive_knew_it_returns_learned():
    assert recalculate(["knew_it", "knew_it", "knew_it"]) == "learned"


def test_four_consecutive_knew_it_returns_learned():
    assert recalculate(["knew_it", "knew_it", "knew_it", "knew_it"]) == "learned"


def test_knew_it_then_guessed_not_learned():
    # First two are knew_it but 3rd is guessed — rule 1 does NOT apply
    result = recalculate(["knew_it", "knew_it", "guessed"])
    assert result != "learned"


# ---------------------------------------------------------------------------
# Rule 1 priority over Rule 2 — 3 consecutive KNEW_IT wins even if currently LEARNED
# ---------------------------------------------------------------------------


def test_rule1_takes_priority_over_rule2():
    # Was DIFFICULT, 3 consecutive KNEW_IT — rule 1 should give LEARNED
    result = recalculate(["knew_it", "knew_it", "knew_it"], current_classification="difficult")
    assert result == "learned"


# ---------------------------------------------------------------------------
# Rule 2 — Regression: LEARNED + DIDNT_KNOW at top → DIFFICULT
# ---------------------------------------------------------------------------


def test_regression_from_learned_to_difficult():
    result = recalculate(["didnt_know"], current_classification="learned")
    assert result == "difficult"


def test_regression_fires_even_with_prior_knew_it():
    # Most recent is DIDNT_KNOW, current is LEARNED — regression applies
    result = recalculate(["didnt_know", "knew_it", "knew_it"], current_classification="learned")
    assert result == "difficult"


def test_no_regression_if_not_currently_learned():
    # Only one DIDNT_KNOW, not currently LEARNED — rule 2 should not fire
    result = recalculate(["didnt_know"], current_classification="difficult")
    assert result == "difficult"  # rule 3 fires for 1 count (only if >=2, so keep current)


# ---------------------------------------------------------------------------
# Rule 3 — 2+ DIDNT_KNOW in last 5 → DIFFICULT
# ---------------------------------------------------------------------------


def test_two_didnt_know_returns_difficult():
    result = recalculate(["guessed", "didnt_know", "didnt_know"])
    assert result == "difficult"


def test_two_didnt_know_mixed_with_guessed():
    result = recalculate(["guessed", "didnt_know", "guessed", "didnt_know", "guessed"])
    assert result == "difficult"


def test_one_didnt_know_does_not_trigger_rule3():
    # Only 1 DIDNT_KNOW — should not be DIFFICULT by rule 3
    result = recalculate(["guessed", "guessed", "guessed", "didnt_know"])
    # Rule 4 applies: 3 positive (guessed), 3 guessed → almost_learned
    assert result == "almost_learned"


# ---------------------------------------------------------------------------
# Rule 4 — ≥3 of last 5 positive, ≥1 GUESSED, no 3-consecutive-KNEW_IT → ALMOST_LEARNED
# ---------------------------------------------------------------------------


def test_almost_learned_with_mixed_positive():
    result = recalculate(["guessed", "knew_it", "guessed"])
    assert result == "almost_learned"


def test_almost_learned_requires_at_least_one_guessed():
    # 3 KNEW_IT would be rule 1 → LEARNED; test 2 KNEW_IT + 1 guessed = ALMOST_LEARNED
    result = recalculate(["knew_it", "knew_it", "guessed"])
    assert result == "almost_learned"


def test_three_guessed_returns_almost_learned():
    result = recalculate(["guessed", "guessed", "guessed"])
    assert result == "almost_learned"


def test_almost_learned_not_triggered_without_guessed():
    # 3+ positive but zero GUESSED — rule 4 requires ≥1 GUESSED
    # With 3 KNEW_IT that's rule 1 → LEARNED; test edge with 2 KNEW_IT only
    result = recalculate(["knew_it", "knew_it"])
    # Not enough consecutive KNEW_IT (rule 1 needs 3), no guessed — keep current
    assert result == "not_practiced"  # default


# ---------------------------------------------------------------------------
# Rule 5 — Default: keep current classification
# ---------------------------------------------------------------------------


def test_empty_ratings_keeps_current():
    result = recalculate([], current_classification="almost_learned")
    assert result == "almost_learned"


def test_single_guessed_keeps_current():
    result = recalculate(["guessed"], current_classification="not_practiced")
    assert result == "not_practiced"


def test_default_returns_not_practiced_when_learned_and_no_rule_matches():
    # Currently LEARNED, no DIDNT_KNOW at top (rule 2), no 2+ DIDNT_KNOW (rule 3)
    # No 3+ consecutive KNEW_IT (rule 1), not enough positive (rule 4)
    # Rule 5 fall-through: was LEARNED, no rule matched → NOT_PRACTICED
    result = recalculate(["guessed"], current_classification="learned")
    assert result == "not_practiced"


# ---------------------------------------------------------------------------
# Priority ordering — Rule 1 wins over all
# ---------------------------------------------------------------------------


def test_rule1_overrides_rule3():
    # 3 consecutive KNEW_IT, but also 2 DIDNT_KNOW elsewhere — rule 1 still wins
    result = recalculate(["knew_it", "knew_it", "knew_it", "didnt_know", "didnt_know"])
    assert result == "learned"


# ---------------------------------------------------------------------------
# T058 — Priority conflict and boundary edge cases
# ---------------------------------------------------------------------------


def test_three_consecutive_knew_overrides_two_didnt_know():
    """Rule 1 (3 consecutive KNEW_IT) overrides Rule 3 (2 DIDNT_KNOW in last 5)."""
    result = recalculate(["knew_it", "knew_it", "knew_it", "didnt_know", "didnt_know"])
    assert result == "learned"


def test_regression_learned_to_difficult_on_single_didnt_know():
    """Rule 2: one DIDNT_KNOW as most recent rating when already Learned → DIFFICULT."""
    result = recalculate(["didnt_know"], current_classification="learned")
    assert result == "difficult"


def test_almost_learned_boundary_exactly_three_positives_one_guessed():
    """Rule 4: exactly 3 positives with at least 1 GUESSED → ALMOST_LEARNED."""
    result = recalculate(["knew_it", "knew_it", "guessed"])
    assert result == "almost_learned"


def test_almost_learned_not_triggered_with_only_two_positives():
    """Rule 4 requires at least 3 positives — 2 positives is insufficient."""
    result = recalculate(["knew_it", "guessed"])
    assert result not in ("almost_learned", "learned")


def test_priority_rule1_beats_rule2_for_current_learned():
    """3 consecutive KNEW_IT (rule 1) wins even if current classification is LEARNED."""
    result = recalculate(["knew_it", "knew_it", "knew_it"], current_classification="learned")
    assert result == "learned"  # Rule 1 fires (and result stays learned)
