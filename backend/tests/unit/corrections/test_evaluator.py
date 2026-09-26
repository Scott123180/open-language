"""Unit tests for LlmCorrectionEvaluator (contracts/api.md §3.2)."""

import json

from app.corrections.config import MAX_CORRECTIONS_PER_MESSAGE
from app.corrections.services.evaluator import (
    CorrectionEvaluator,
    EvaluationRequest,
    LlmCorrectionEvaluator,
)
from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider


class ScriptedStructuredLLM(StructuredLLMProvider):
    def __init__(self, response: str) -> None:
        self._response = response
        self.calls: list[list[ChatMessage]] = []

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        self.calls.append(messages)
        return self._response


class FailingStructuredLLM(StructuredLLMProvider):
    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        raise LLMError("ollama is down")


def _payload(corrections: list[dict], verdict: str = "has_mistakes") -> dict:
    return {"verdict": verdict, "corrections": corrections}


def _finding(fragment: str = "Yo tener") -> dict:
    return {
        "category": "conjugation",
        "error_fragment": fragment,
        "corrected_text": "Yo tengo veinte años",
        "explanation": "Tener must be conjugated as tengo with yo.",
    }


def _request(text: str = "Yo tener veinte años") -> EvaluationRequest:
    return EvaluationRequest(
        learner_text=text,
        target_language="Spanish",
        native_language="English",
        preceding_character_line="¿Cuántos años tienes?",
    )


def _evaluator(response: str) -> tuple[LlmCorrectionEvaluator, ScriptedStructuredLLM]:
    llm = ScriptedStructuredLLM(response)
    return LlmCorrectionEvaluator(llm), llm


class TestParsing:
    def test_implements_the_abstraction(self) -> None:
        evaluator, _ = _evaluator(json.dumps(_payload([], verdict="correct")))

        assert isinstance(evaluator, CorrectionEvaluator)

    def test_parses_valid_json(self) -> None:
        evaluator, _ = _evaluator(json.dumps(_payload([_finding()])))

        findings = evaluator.evaluate(_request())

        assert len(findings) == 1
        assert findings[0].category == "conjugation"
        assert findings[0].error_fragment == "Yo tener"
        assert findings[0].corrected_text == "Yo tengo veinte años"

    def test_assigns_rank_by_position(self) -> None:
        payload = _payload([_finding("first"), _finding("second")])
        evaluator, _ = _evaluator(json.dumps(payload))

        findings = evaluator.evaluate(_request())

        assert [f.rank for f in findings] == [0, 1]

    def test_strips_code_fences(self) -> None:
        fenced = "```json\n" + json.dumps(_payload([_finding()])) + "\n```"
        evaluator, _ = _evaluator(fenced)

        assert len(evaluator.evaluate(_request())) == 1

    def test_extracts_the_object_from_surrounding_prose(self) -> None:
        noisy = "Sure! " + json.dumps(_payload([_finding()])) + " Hope that helps."
        evaluator, _ = _evaluator(noisy)

        assert len(evaluator.evaluate(_request())) == 1

    def test_truncates_to_the_cap(self) -> None:
        payload = _payload([_finding(f"e{i}") for i in range(5)])
        evaluator, _ = _evaluator(json.dumps(payload))

        assert len(evaluator.evaluate(_request())) == MAX_CORRECTIONS_PER_MESSAGE


class TestFailingOpen:
    def test_returns_empty_on_malformed_json(self) -> None:
        evaluator, _ = _evaluator("this is not json at all")

        assert evaluator.evaluate(_request()) == ()

    def test_returns_empty_when_corrections_is_not_a_list(self) -> None:
        evaluator, _ = _evaluator(json.dumps(_payload("none")))

        assert evaluator.evaluate(_request()) == ()

    def test_returns_empty_on_llm_error(self) -> None:
        evaluator = LlmCorrectionEvaluator(FailingStructuredLLM())

        assert evaluator.evaluate(_request()) == ()

    def test_skips_findings_missing_a_required_field(self) -> None:
        incomplete = {"category": "conjugation", "explanation": "…"}
        evaluator, _ = _evaluator(json.dumps(_payload([incomplete, _finding()])))

        findings = evaluator.evaluate(_request())

        assert len(findings) == 1
        assert findings[0].error_fragment == "Yo tener"

    def test_skips_a_finding_with_an_unknown_category(self) -> None:
        rogue = {**_finding(), "category": "vibes"}
        evaluator, _ = _evaluator(json.dumps(_payload([rogue])))

        assert evaluator.evaluate(_request()) == ()

    def test_returns_empty_on_a_json_object_that_will_not_parse(self) -> None:
        evaluator, _ = _evaluator("{corrections: [unquoted, broken]}")

        assert evaluator.evaluate(_request()) == ()

    def test_returns_empty_when_the_json_is_not_an_object(self) -> None:
        evaluator, _ = _evaluator('{"verdict": "correct", "corrections": []} extra')

        # A bare array is not the documented shape; the parser must not guess.
        evaluator_for_array, _ = _evaluator("[1, 2, 3]")
        assert evaluator_for_array.evaluate(_request()) == ()

    def test_skips_a_non_object_entry_in_the_corrections_list(self) -> None:
        evaluator, _ = _evaluator(json.dumps(_payload(["just a string", _finding()])))

        findings = evaluator.evaluate(_request())

        assert len(findings) == 1

    def test_skips_a_finding_whose_explanation_is_blank(self) -> None:
        blank = {**_finding(), "explanation": "   "}
        evaluator, _ = _evaluator(json.dumps(_payload([blank])))

        assert evaluator.evaluate(_request()) == ()


class TestPreFilters:
    def test_returns_empty_for_input_under_the_word_minimum(self) -> None:
        evaluator, llm = _evaluator(json.dumps(_payload([_finding()])))

        assert evaluator.evaluate(_request("sí")) == ()

    def test_spends_no_llm_call_on_input_under_the_word_minimum(self) -> None:
        evaluator, llm = _evaluator(json.dumps(_payload([_finding()])))

        evaluator.evaluate(_request("gracias!"))

        assert llm.calls == []

    def test_punctuation_does_not_count_as_a_word(self) -> None:
        evaluator, llm = _evaluator(json.dumps(_payload([_finding()])))

        evaluator.evaluate(_request("¿Sí? ..."))

        assert llm.calls == []

    def test_evaluates_a_two_word_message(self) -> None:
        evaluator, llm = _evaluator(json.dumps(_payload([_finding()])))

        evaluator.evaluate(_request("Yo tener"))

        assert len(llm.calls) == 1


class TestVerdictGate:
    """A "correct" verdict discards whatever the model still put in the list."""

    def test_a_correct_verdict_yields_no_findings(self) -> None:
        evaluator, _ = _evaluator(json.dumps(_payload([_finding()], verdict="correct")))

        assert evaluator.evaluate(_request()) == ()

    def test_a_has_mistakes_verdict_yields_the_findings(self) -> None:
        evaluator, _ = _evaluator(json.dumps(_payload([_finding()], verdict="has_mistakes")))

        assert len(evaluator.evaluate(_request())) == 1

    def test_a_missing_verdict_is_treated_as_correct(self) -> None:
        """Fail closed on the restraint side: no verdict, no correction."""
        evaluator, _ = _evaluator(json.dumps({"corrections": [_finding()]}))

        assert evaluator.evaluate(_request()) == ()

    def test_an_unknown_verdict_is_treated_as_correct(self) -> None:
        evaluator, _ = _evaluator(json.dumps(_payload([_finding()], verdict="maybe")))

        assert evaluator.evaluate(_request()) == ()
