"""Corrective feedback domain module (feature 003).

The public interface of the module. `build_correction_strategy` is the only
place in the codebase where a correction-mode string becomes behaviour; every
consumer downstream of it holds a `CorrectionStrategy` and never sees the mode.
"""

from app.corrections.models import CorrectionMode, ErrorCategory, FeedbackKind
from app.corrections.services.evaluator import CorrectionEvaluator
from app.corrections.services.pause_tracker import CorrectionPauseTracker
from app.corrections.services.storage import (
    CorrectionStorageProvider,
    FeedbackDraft,
    FeedbackRecord,
    PauseSnapshot,
)
from app.corrections.services.strategies import (
    CorrectionStrategy,
    GentleCorrectionStrategy,
    OffCorrectionStrategy,
    StrictCorrectionStrategy,
    TurnContext,
    TurnPlan,
)

__all__ = [
    "CorrectionEvaluator",
    "CorrectionMode",
    "CorrectionPauseTracker",
    "CorrectionStorageProvider",
    "CorrectionStrategy",
    "ErrorCategory",
    "FeedbackDraft",
    "GentleCorrectionStrategy",
    "FeedbackKind",
    "FeedbackRecord",
    "PauseSnapshot",
    "StrictCorrectionStrategy",
    "TurnContext",
    "TurnPlan",
    "build_correction_strategy",
]


def build_correction_strategy(
    mode: str,
    evaluator: CorrectionEvaluator,
    storage: CorrectionStorageProvider,
) -> CorrectionStrategy:
    """Turn a stored mode string into the strategy that implements it.

    An unrecognised mode falls back to Off: a bad stored value must never stop
    a conversation working.
    """
    if mode == CorrectionMode.STRICT.value:
        return StrictCorrectionStrategy(evaluator, CorrectionPauseTracker(storage))
    if mode == CorrectionMode.GENTLE.value:
        return GentleCorrectionStrategy(evaluator)
    return OffCorrectionStrategy()
