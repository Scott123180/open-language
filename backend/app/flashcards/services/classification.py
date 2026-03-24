"""ClassificationEngine — pure function service, no I/O.

Receives a list of rating strings (most recent first, max 5) and
returns the updated word classification according to priority rules
defined in FR-009 and clarified in spec.md § Clarifications.

Priority order (highest wins):
  1. 3+ consecutive KNEW_IT at the top of the list → LEARNED
  2. Currently LEARNED and top rating is DIDNT_KNOW → DIFFICULT (regression)
  3. 2+ DIDNT_KNOW in the last 5 → DIFFICULT
  4. ≥3 of last 5 are GUESSED or KNEW_IT, ≥1 GUESSED, no 3+ consecutive KNEW_IT → ALMOST_LEARNED
  5. Otherwise → NOT_PRACTICED (default / insufficient history)
"""

from __future__ import annotations

KNEW_IT = "knew_it"
GUESSED = "guessed"
DIDNT_KNOW = "didnt_know"

NOT_PRACTICED = "not_practiced"
DIFFICULT = "difficult"
ALMOST_LEARNED = "almost_learned"
LEARNED = "learned"


def _has_consecutive_knew_it(ratings: list[str], required: int = 3) -> bool:
    """Return True if the first `required` entries are all KNEW_IT."""
    if len(ratings) < required:
        return False
    return all(r == KNEW_IT for r in ratings[:required])


def recalculate(ratings: list[str], current_classification: str = NOT_PRACTICED) -> str:
    """Return the new classification given the rolling rating history.

    Args:
        ratings: Most-recent-first list of rating strings; maximum 5 entries.
        current_classification: The word's classification before this recalculation.

    Returns:
        The new classification string.
    """
    if not ratings:
        return current_classification

    # Rule 1 — 3+ consecutive KNEW_IT → LEARNED (highest priority)
    if _has_consecutive_knew_it(ratings):
        return LEARNED

    # Rule 2 — Regression: was LEARNED, most recent is DIDNT_KNOW → DIFFICULT
    if current_classification == LEARNED and ratings[0] == DIDNT_KNOW:
        return DIFFICULT

    # Rule 3 — 2+ DIDNT_KNOW in last 5 → DIFFICULT
    didnt_know_count = ratings.count(DIDNT_KNOW)
    if didnt_know_count >= 2:
        return DIFFICULT

    # Rule 4 — Almost Learned threshold:
    # ≥3 of last 5 are GUESSED or KNEW_IT, at least 1 GUESSED, no 3+ consecutive KNEW_IT
    positive_count = sum(1 for r in ratings if r in (GUESSED, KNEW_IT))
    guessed_count = ratings.count(GUESSED)
    if positive_count >= 3 and guessed_count >= 1:
        return ALMOST_LEARNED

    # Rule 5 — Default: not enough history or no pattern matched
    return current_classification if current_classification != LEARNED else NOT_PRACTICED
