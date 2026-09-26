"""Error evaluation: one structured LLM call per learner message (research.md R3)."""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.corrections.config import MAX_CORRECTIONS_PER_MESSAGE, MIN_WORDS_FOR_EVALUATION
from app.corrections.prompts import CORRECTION_JSON_SCHEMA, build_evaluation_prompt
from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

logger = logging.getLogger(__name__)

_KNOWN_CATEGORIES = frozenset({"conjugation", "agreement", "word_choice", "word_order"})
_MISTAKES_VERDICT = "has_mistakes"
_REQUIRED_FIELDS = ("category", "error_fragment", "corrected_text", "explanation")
_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class CorrectionFinding:
    """One mistake the evaluator is confident about."""

    category: str
    error_fragment: str
    corrected_text: str
    explanation: str
    rank: int


@dataclass(frozen=True)
class EvaluationRequest:
    """Everything one evaluation needs, bundled to keep the signature to one argument."""

    learner_text: str
    target_language: str
    native_language: str
    preceding_character_line: str | None


class CorrectionEvaluator(ABC):
    @abstractmethod
    def evaluate(self, request: EvaluationRequest) -> tuple[CorrectionFinding, ...]:
        """Return 0..MAX_CORRECTIONS_PER_MESSAGE findings, ordered by impact.

        Never raises: every failure returns an empty tuple (FR-026).
        """
        ...


class LlmCorrectionEvaluator(CorrectionEvaluator):
    def __init__(self, llm: StructuredLLMProvider) -> None:
        self._llm = llm

    def evaluate(self, request: EvaluationRequest) -> tuple[CorrectionFinding, ...]:
        if _word_count(request.learner_text) < MIN_WORDS_FOR_EVALUATION:
            return ()
        raw = self._ask_the_model(request)
        if raw is None:
            return ()
        return _parse_findings(raw)

    def _ask_the_model(self, request: EvaluationRequest) -> str | None:
        prompt = build_evaluation_prompt(
            learner_text=request.learner_text,
            target_language=request.target_language,
            native_language=request.native_language,
            preceding_character_line=request.preceding_character_line,
        )
        try:
            return self._llm.chat_json(
                [ChatMessage(role="user", content=prompt)], CORRECTION_JSON_SCHEMA
            )
        except LLMError as exc:
            logger.warning("Correction evaluation failed, continuing uncorrected: %s", exc)
            return None


def _word_count(text: str) -> int:
    return len(_WORD_PATTERN.findall(text))


def _parse_findings(raw: str) -> tuple[CorrectionFinding, ...]:
    payload = _load_json_object(raw)
    if payload is None:
        return ()
    if payload.get("verdict") != _MISTAKES_VERDICT:
        # No verdict, or a "correct" one: the model has said there is nothing to
        # report, so anything still in the list is discarded (FR-007 restraint).
        return ()
    candidates = payload.get("corrections")
    if not isinstance(candidates, list):
        logger.warning("Correction evaluation returned no corrections list; continuing")
        return ()
    valid = [c for c in candidates if _is_usable(c)]
    return tuple(
        _to_finding(candidate, rank)
        for rank, candidate in enumerate(valid[:MAX_CORRECTIONS_PER_MESSAGE])
    )


def _load_json_object(raw: str) -> dict | None:
    match = _JSON_OBJECT_PATTERN.search(raw)
    if match is None:
        logger.warning("Correction evaluation returned no JSON object; continuing uncorrected")
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        logger.warning("Correction evaluation returned unparseable JSON: %s", exc)
        return None
    return parsed if isinstance(parsed, dict) else None


def _is_usable(candidate: object) -> bool:
    if not isinstance(candidate, dict):
        return False
    if any(not isinstance(candidate.get(field), str) for field in _REQUIRED_FIELDS):
        return False
    if candidate["category"] not in _KNOWN_CATEGORIES:
        return False
    return bool(candidate["explanation"].strip())


def _to_finding(candidate: dict, rank: int) -> CorrectionFinding:
    return CorrectionFinding(
        category=candidate["category"],
        error_fragment=candidate["error_fragment"],
        corrected_text=candidate["corrected_text"],
        explanation=candidate["explanation"].strip(),
        rank=rank,
    )
