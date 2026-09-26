"""SC-003 detection benchmark against the real Ollama model.

Deselected by default (`-m "not benchmark"` in pyproject) so CI stays hermetic.
Run it by hand and record the two printed figures:

    backend/.venv/bin/pytest -m benchmark -s \
        tests/integration/corrections/test_correction_benchmark.py

SC-003 asks for at least 8 of 10 deliberate errors detected and 0 of 10 correct
sentences falsely flagged. This is the only test that measures detection quality;
the pipeline test in test_chat_correction_modes.py measures wiring, not accuracy.
"""

import pytest

from app.config import get_settings
from app.corrections.services.evaluator import EvaluationRequest, LlmCorrectionEvaluator
from app.services.llm.ollama import OllamaLLMProvider
from tests.integration.corrections.test_chat_correction_modes import (
    CORRECT_SENTENCES,
    SENTENCES_WITH_AN_ERROR,
)

MINIMUM_DETECTED = 8
MAXIMUM_FALSE_POSITIVES = 0

pytestmark = pytest.mark.benchmark


def _request(sentence: str) -> EvaluationRequest:
    return EvaluationRequest(
        learner_text=sentence,
        target_language="Spanish",
        native_language="English",
        preceding_character_line=None,
    )


def _count_flagged(evaluator: LlmCorrectionEvaluator, sentences: list[str]) -> int:
    return sum(1 for sentence in sentences if evaluator.evaluate(_request(sentence)))


@pytest.fixture()
def real_evaluator() -> LlmCorrectionEvaluator:
    settings = get_settings()
    return LlmCorrectionEvaluator(OllamaLLMProvider(model=settings.ollama_model))


def test_detection_rate_meets_sc_003(real_evaluator, capsys) -> None:
    detected = _count_flagged(real_evaluator, SENTENCES_WITH_AN_ERROR)
    false_positives = _count_flagged(real_evaluator, CORRECT_SENTENCES)

    with capsys.disabled():
        # Printing is the point: these two figures are recorded against SC-003.
        print(f"\nSC-003 detected: {detected}/{len(SENTENCES_WITH_AN_ERROR)}")  # noqa: T201
        print(f"SC-003 false positives: {false_positives}/{len(CORRECT_SENTENCES)}")  # noqa: T201

    assert detected >= MINIMUM_DETECTED
    assert false_positives <= MAXIMUM_FALSE_POSITIVES
