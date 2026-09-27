"""One strategy per correction mode (contracts/api.md §3.3).

The chat router receives a TurnPlan and acts on it identically whichever
strategy produced it, so no consumer branches on a mode string.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.corrections.config import MAX_CORRECTIONS_PER_MESSAGE
from app.corrections.prompts import build_recast_instruction, build_repeat_request
from app.corrections.services.evaluator import (
    CorrectionEvaluator,
    CorrectionFinding,
    EvaluationRequest,
)
from app.corrections.services.pause_tracker import CorrectionPauseTracker
from app.corrections.services.storage import FeedbackDraft


@dataclass(frozen=True)
class TurnContext:
    """Everything a mode needs to decide what to do with one learner message.

    Its language fields are display names ("German"), used only in prompt text.
    """

    conversation_id: int
    learner_text: str
    target_language: str
    native_language: str
    preceding_character_line: str | None
    is_low_confidence: bool = False


@dataclass(frozen=True)
class TurnPlan:
    """One mode's decision for one turn."""

    feedback: tuple[FeedbackDraft, ...] = field(default_factory=tuple)
    generate_reply: bool = True
    reply_prompt_suffix: str | None = None


NULL_TURN_PLAN = TurnPlan(feedback=(), generate_reply=True, reply_prompt_suffix=None)


class CorrectionStrategy(ABC):
    @abstractmethod
    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        """Decide what this mode does with this learner message."""
        ...


class OffCorrectionStrategy(CorrectionStrategy):
    """A null object: no LLM call, no query, no row, no extra frame (R10)."""

    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        return NULL_TURN_PLAN


def _to_draft(finding: CorrectionFinding, mode: str) -> FeedbackDraft:
    return FeedbackDraft(
        kind="correction",
        category=finding.category,
        error_fragment=finding.error_fragment,
        corrected_text=finding.corrected_text,
        explanation=finding.explanation,
        mode=mode,
        rank=finding.rank,
    )


def _drafts(findings: tuple[CorrectionFinding, ...], mode: str) -> tuple[FeedbackDraft, ...]:
    """FR-008 holds here as well as in the parser, whatever the evaluator returns."""
    return tuple(_to_draft(f, mode) for f in findings[:MAX_CORRECTIONS_PER_MESSAGE])


def _evaluation_request(context: TurnContext) -> EvaluationRequest:
    return EvaluationRequest(
        learner_text=context.learner_text,
        target_language=context.target_language,
        native_language=context.native_language,
        preceding_character_line=context.preceding_character_line,
    )


async def _evaluate(
    evaluator: CorrectionEvaluator, context: TurnContext
) -> tuple[CorrectionFinding, ...]:
    """Run the blocking evaluator off the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, evaluator.evaluate, _evaluation_request(context))


def _repeat_request_draft(target_language: str) -> FeedbackDraft:
    return FeedbackDraft(
        kind="repeat_request",
        category=None,
        error_fragment=None,
        corrected_text=None,
        explanation=build_repeat_request(target_language),
        mode="strict",
        rank=0,
    )


class StrictCorrectionStrategy(CorrectionStrategy):
    """The correction is the turn's only output; no reply is generated (FR-016)."""

    def __init__(self, evaluator: CorrectionEvaluator, pause_tracker: CorrectionPauseTracker):
        self._evaluator = evaluator
        self._pause_tracker = pause_tracker

    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        if context.is_low_confidence:
            return self._handle_unclear_speech(context)

        self._pause_tracker.clear_clarification(context.conversation_id)
        if not self._pause_tracker.should_evaluate(context.conversation_id):
            self._pause_tracker.release_pause(context.conversation_id)
            return NULL_TURN_PLAN

        findings = await _evaluate(self._evaluator, context)
        if not findings:
            self._pause_tracker.record_clean_message(context.conversation_id)
            return NULL_TURN_PLAN

        self._pause_tracker.record_correction(context.conversation_id)
        return TurnPlan(
            feedback=_drafts(findings, mode="strict"),
            generate_reply=False,
            reply_prompt_suffix=None,
        )

    def _handle_unclear_speech(self, context: TurnContext) -> TurnPlan:
        """Never correct words the learner may not have said (FR-010a)."""
        if not self._pause_tracker.may_request_repeat(context.conversation_id):
            # They have already been asked once; answer rather than stall (FR-027).
            self._pause_tracker.clear_clarification(context.conversation_id)
            return NULL_TURN_PLAN

        self._pause_tracker.record_repeat_request(context.conversation_id)
        return TurnPlan(
            feedback=(_repeat_request_draft(context.target_language),),
            generate_reply=False,
            reply_prompt_suffix=None,
        )


class GentleCorrectionStrategy(CorrectionStrategy):
    """The correction is the character's own words; the conversation never stops."""

    def __init__(self, evaluator: CorrectionEvaluator) -> None:
        self._evaluator = evaluator

    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        # A mishearing must never become a recast (FR-010a). Gentle still replies.
        if context.is_low_confidence:
            return NULL_TURN_PLAN

        findings = await _evaluate(self._evaluator, context)
        if not findings:
            return NULL_TURN_PLAN

        return TurnPlan(
            feedback=_drafts(findings, mode="gentle"),
            generate_reply=True,
            # One reply can only restate one correction naturally, so recast the
            # finding that hurts comprehension most and let the rest go.
            reply_prompt_suffix=build_recast_instruction(
                findings[0].corrected_text, context.target_language
            ),
        )
