"""build_correction_strategy is the only place a mode string becomes behaviour."""

from app.corrections import build_correction_strategy
from app.corrections.services.strategies import (
    GentleCorrectionStrategy,
    OffCorrectionStrategy,
    StrictCorrectionStrategy,
)
from tests.unit.corrections.test_pause_tracker import InMemoryPauseStorage
from tests.unit.corrections.test_strategies import ScriptedEvaluator


def _build(mode: str):
    return build_correction_strategy(
        mode, evaluator=ScriptedEvaluator(()), storage=InMemoryPauseStorage()
    )


def test_off_builds_the_null_strategy() -> None:
    assert isinstance(_build("off"), OffCorrectionStrategy)


def test_gentle_builds_the_gentle_strategy() -> None:
    assert isinstance(_build("gentle"), GentleCorrectionStrategy)


def test_strict_builds_the_strict_strategy() -> None:
    assert isinstance(_build("strict"), StrictCorrectionStrategy)


def test_an_unrecognised_mode_falls_back_to_off() -> None:
    """A bad stored value must never stop a conversation working."""
    assert isinstance(_build("enthusiastic"), OffCorrectionStrategy)


def test_an_empty_mode_falls_back_to_off() -> None:
    assert isinstance(_build(""), OffCorrectionStrategy)
