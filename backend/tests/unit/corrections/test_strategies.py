"""Unit tests for the correction strategies (contracts/api.md §3.3)."""

import pytest

from app.corrections.services.evaluator import (
    CorrectionEvaluator,
    CorrectionFinding,
    EvaluationRequest,
)
from app.corrections.services.storage import CorrectionStorageProvider, PauseSnapshot
from app.corrections.services.strategies import (
    CorrectionStrategy,
    GentleCorrectionStrategy,
    OffCorrectionStrategy,
    StrictCorrectionStrategy,
    TurnContext,
    TurnPlan,
)


class RecordingEvaluator(CorrectionEvaluator):
    """An evaluator that must never be called."""

    def __init__(self) -> None:
        self.calls: list[EvaluationRequest] = []

    def evaluate(self, request: EvaluationRequest):
        self.calls.append(request)
        return ()


class RecordingStorage(CorrectionStorageProvider):
    """Storage that records every read and write."""

    def __init__(self) -> None:
        self.reads: list[int] = []
        self.writes: list[tuple[int, int, bool]] = []

    def save_feedback(self, message_id, drafts):
        raise AssertionError("strategies never persist feedback themselves")

    def list_feedback(self, conversation_id):
        raise AssertionError("strategies never read the transcript")

    def get_pause_state(self, conversation_id: int) -> PauseSnapshot:
        self.reads.append(conversation_id)
        return PauseSnapshot(
            consecutive_corrected_attempts=0, awaiting_clarification=False, awaiting_retry=False
        )

    def set_pause_state(self, conversation_id, attempts, awaiting_clarification):
        self.writes.append((conversation_id, attempts, awaiting_clarification))
        return PauseSnapshot(
            consecutive_corrected_attempts=attempts,
            awaiting_clarification=awaiting_clarification,
            awaiting_retry=attempts > 0,
        )


def make_context(text: str = "Yo tener veinte años", **overrides) -> TurnContext:
    defaults = {
        "conversation_id": 1,
        "learner_text": text,
        "target_language": "Spanish",
        "native_language": "English",
        "preceding_character_line": "¿Cuántos años tienes?",
        "is_low_confidence": False,
    }
    return TurnContext(**{**defaults, **overrides})


class TestOffCorrectionStrategy:
    def test_implements_the_abstraction(self) -> None:
        assert isinstance(OffCorrectionStrategy(), CorrectionStrategy)

    async def test_returns_the_null_plan(self) -> None:
        plan = await OffCorrectionStrategy().plan_turn(make_context())

        assert plan == TurnPlan(feedback=(), generate_reply=True, reply_prompt_suffix=None)

    async def test_makes_no_evaluator_call(self) -> None:
        evaluator = RecordingEvaluator()

        await OffCorrectionStrategy().plan_turn(make_context())

        assert evaluator.calls == []

    async def test_reads_and_writes_no_correction_state(self) -> None:
        storage = RecordingStorage()

        await OffCorrectionStrategy().plan_turn(make_context())

        assert storage.reads == []
        assert storage.writes == []

    async def test_takes_no_collaborators_at_all(self) -> None:
        """A null object with dependencies is not a null object (R10)."""
        with pytest.raises(TypeError):
            OffCorrectionStrategy(RecordingEvaluator())  # type: ignore[call-arg]


class TestTurnPlan:
    def test_is_immutable(self) -> None:
        plan = TurnPlan(feedback=(), generate_reply=True, reply_prompt_suffix=None)

        with pytest.raises(Exception):  # noqa: B017 — frozen dataclass raises FrozenInstanceError
            plan.generate_reply = False  # type: ignore[misc]


class TestTurnContext:
    def test_is_immutable(self) -> None:
        context = make_context()

        with pytest.raises(Exception):  # noqa: B017
            context.learner_text = "changed"  # type: ignore[misc]

    def test_defaults_to_normal_confidence(self) -> None:
        context = TurnContext(
            conversation_id=1,
            learner_text="Yo tener veinte años",
            target_language="Spanish",
            native_language="English",
            preceding_character_line=None,
        )

        assert context.is_low_confidence is False


def _finding(rank: int = 0, fragment: str = "Yo tener") -> CorrectionFinding:
    return CorrectionFinding(
        category="conjugation",
        error_fragment=fragment,
        corrected_text="Yo tengo veinte años",
        explanation="Tener must be conjugated as tengo with yo.",
        rank=rank,
    )


class ScriptedEvaluator(CorrectionEvaluator):
    def __init__(self, findings: tuple[CorrectionFinding, ...]) -> None:
        self._findings = findings
        self.calls: list[EvaluationRequest] = []

    def evaluate(self, request: EvaluationRequest) -> tuple[CorrectionFinding, ...]:
        self.calls.append(request)
        return self._findings


def _strict(findings=(), attempts: int = 0, awaiting_clarification: bool = False):
    from app.corrections.services.pause_tracker import CorrectionPauseTracker
    from tests.unit.corrections.test_pause_tracker import InMemoryPauseStorage

    storage = InMemoryPauseStorage(attempts, awaiting_clarification)
    evaluator = ScriptedEvaluator(findings)
    strategy = StrictCorrectionStrategy(evaluator, CorrectionPauseTracker(storage))
    return strategy, evaluator, storage


class TestStrictCorrectionStrategy:
    def test_implements_the_abstraction(self) -> None:
        strategy, _, _ = _strict()

        assert isinstance(strategy, CorrectionStrategy)

    async def test_withholds_the_reply_when_a_finding_exists(self) -> None:
        strategy, _, _ = _strict(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context())

        assert plan.generate_reply is False

    async def test_returns_the_finding_as_feedback(self) -> None:
        strategy, _, _ = _strict(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context())

        assert len(plan.feedback) == 1
        draft = plan.feedback[0]
        assert draft.kind == "correction"
        assert draft.mode == "strict"
        assert draft.corrected_text == "Yo tengo veinte años"
        assert draft.rank == 0

    async def test_never_supplies_a_reply_prompt_suffix(self) -> None:
        """A Strict correction is the turn's whole output — it is not woven in."""
        strategy, _, _ = _strict(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context())

        assert plan.reply_prompt_suffix is None

    async def test_replies_normally_when_there_is_no_finding(self) -> None:
        strategy, _, _ = _strict(findings=())

        plan = await strategy.plan_turn(make_context())

        assert plan == TurnPlan(feedback=(), generate_reply=True, reply_prompt_suffix=None)

    async def test_a_finding_increments_the_pause_counter(self) -> None:
        strategy, _, storage = _strict(findings=(_finding(),))

        await strategy.plan_turn(make_context())

        assert storage.attempts == 1

    async def test_a_clean_message_clears_the_pause_counter(self) -> None:
        strategy, _, storage = _strict(findings=(), attempts=1)

        await strategy.plan_turn(make_context())

        assert storage.attempts == 0

    async def test_at_the_cap_the_message_is_answered_without_evaluation(self) -> None:
        from app.corrections.config import MAX_CONSECUTIVE_CORRECTED_ATTEMPTS

        strategy, evaluator, storage = _strict(
            findings=(_finding(),), attempts=MAX_CONSECUTIVE_CORRECTED_ATTEMPTS
        )

        plan = await strategy.plan_turn(make_context())

        assert plan.generate_reply is True
        assert plan.feedback == ()
        assert evaluator.calls == []
        assert storage.attempts == 0

    async def test_carries_both_findings_through(self) -> None:
        strategy, _, _ = _strict(findings=(_finding(0, "a"), _finding(1, "b")))

        plan = await strategy.plan_turn(make_context())

        assert [d.rank for d in plan.feedback] == [0, 1]

    async def test_passes_the_conversation_context_to_the_evaluator(self) -> None:
        strategy, evaluator, _ = _strict(findings=())

        await strategy.plan_turn(make_context("Yo tener veinte años"))

        request = evaluator.calls[0]
        assert request.learner_text == "Yo tener veinte años"
        assert request.target_language == "Spanish"
        assert request.native_language == "English"
        assert request.preceding_character_line == "¿Cuántos años tienes?"


class TestOnlyStrictWithholdsAReply:
    async def test_off_always_generates_a_reply(self) -> None:
        plan = await OffCorrectionStrategy().plan_turn(make_context())

        assert plan.generate_reply is True


def _gentle(findings=(), attempts: int = 0):
    from tests.unit.corrections.test_pause_tracker import InMemoryPauseStorage

    storage = InMemoryPauseStorage(attempts)
    evaluator = ScriptedEvaluator(findings)
    return GentleCorrectionStrategy(evaluator), evaluator, storage


class TestGentleCorrectionStrategy:
    def test_implements_the_abstraction(self) -> None:
        strategy, _, _ = _gentle()

        assert isinstance(strategy, CorrectionStrategy)

    async def test_always_generates_a_reply_when_a_finding_exists(self) -> None:
        strategy, _, _ = _gentle(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context())

        assert plan.generate_reply is True

    async def test_always_generates_a_reply_when_there_is_no_finding(self) -> None:
        strategy, _, _ = _gentle(findings=())

        plan = await strategy.plan_turn(make_context())

        assert plan.generate_reply is True

    async def test_supplies_a_recast_suffix_when_a_finding_exists(self) -> None:
        strategy, _, _ = _gentle(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context())

        assert plan.reply_prompt_suffix is not None
        assert "Yo tengo veinte años" in plan.reply_prompt_suffix

    async def test_supplies_no_suffix_when_there_is_no_finding(self) -> None:
        strategy, _, _ = _gentle(findings=())

        plan = await strategy.plan_turn(make_context())

        assert plan.reply_prompt_suffix is None

    async def test_records_the_correction_with_the_gentle_mode(self) -> None:
        strategy, _, _ = _gentle(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context())

        assert len(plan.feedback) == 1
        assert plan.feedback[0].mode == "gentle"

    async def test_recasts_only_the_highest_ranked_finding(self) -> None:
        """One reply cannot naturally restate two different corrections."""
        strategy, _, _ = _gentle(findings=(_finding(0, "a"), _finding(1, "b")))

        plan = await strategy.plan_turn(make_context())

        assert plan.reply_prompt_suffix is not None
        assert plan.reply_prompt_suffix.count("Yo tengo veinte años") == 1

    async def test_takes_no_pause_tracker_at_all(self) -> None:
        """FR-013: Gentle never pauses, so it has no business holding the state."""
        strategy, _, storage = _gentle(findings=(_finding(),))

        await strategy.plan_turn(make_context())

        assert storage.writes == []

    async def test_never_withholds_a_reply(self) -> None:
        """Only Strict may return generate_reply=False."""
        strategy, _, _ = _gentle(findings=(_finding(0, "a"), _finding(1, "b")))

        plan = await strategy.plan_turn(make_context())

        assert plan.generate_reply is True


class TestLowConfidenceGate:
    """FR-010a: a mishearing must never become a correction."""

    async def test_strict_produces_no_correction_for_a_low_confidence_message(self) -> None:
        strategy, evaluator, _ = _strict(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context(is_low_confidence=True))

        assert all(d.kind != "correction" for d in plan.feedback)
        assert evaluator.calls == []

    async def test_gentle_produces_no_correction_for_a_low_confidence_message(self) -> None:
        strategy, evaluator, _ = _gentle(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context(is_low_confidence=True))

        assert plan.feedback == ()
        assert plan.reply_prompt_suffix is None
        assert evaluator.calls == []

    async def test_gentle_still_replies_to_a_low_confidence_message(self) -> None:
        """FR-028: Gentle never pauses, whatever the confidence."""
        strategy, _, _ = _gentle(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context(is_low_confidence=True))

        assert plan.generate_reply is True

    async def test_a_none_confidence_is_evaluated_normally(self) -> None:
        """Typed input has no confidence and must never be gated."""
        strategy, evaluator, _ = _strict(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context(is_low_confidence=False))

        assert len(evaluator.calls) == 1
        assert plan.generate_reply is False


class TestStrictRepeatRequest:
    """FR-027 / FR-028: a low-confidence message earns one ask-to-repeat."""

    async def test_issues_a_repeat_request(self) -> None:
        strategy, _, _ = _strict(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context(is_low_confidence=True))

        assert len(plan.feedback) == 1
        assert plan.feedback[0].kind == "repeat_request"
        assert plan.feedback[0].mode == "strict"

    async def test_the_repeat_request_carries_no_correction_fields(self) -> None:
        strategy, _, _ = _strict(findings=(_finding(),))

        plan = await strategy.plan_turn(make_context(is_low_confidence=True))

        draft = plan.feedback[0]
        assert draft.category is None
        assert draft.error_fragment is None
        assert draft.corrected_text is None
        assert draft.explanation.strip() != ""

    async def test_withholds_the_reply_while_asking(self) -> None:
        strategy, _, _ = _strict(findings=())

        plan = await strategy.plan_turn(make_context(is_low_confidence=True))

        assert plan.generate_reply is False

    async def test_marks_the_conversation_as_awaiting_clarification(self) -> None:
        strategy, _, storage = _strict(findings=())

        await strategy.plan_turn(make_context(is_low_confidence=True))

        assert storage.awaiting_clarification is True

    async def test_leaves_the_corrected_attempt_counter_alone(self) -> None:
        strategy, _, storage = _strict(findings=(), attempts=1)

        await strategy.plan_turn(make_context(is_low_confidence=True))

        assert storage.attempts == 1

    async def test_a_second_low_confidence_message_proceeds_normally(self) -> None:
        strategy, _, storage = _strict(findings=(), awaiting_clarification=True)

        plan = await strategy.plan_turn(make_context(is_low_confidence=True))

        assert plan.feedback == ()
        assert plan.generate_reply is True

    async def test_the_second_low_confidence_message_clears_the_flag(self) -> None:
        strategy, _, storage = _strict(findings=(), awaiting_clarification=True)

        await strategy.plan_turn(make_context(is_low_confidence=True))

        assert storage.awaiting_clarification is False

    async def test_a_clear_message_after_a_repeat_request_is_evaluated(self) -> None:
        strategy, evaluator, storage = _strict(findings=(_finding(),), awaiting_clarification=True)

        plan = await strategy.plan_turn(make_context())

        assert len(evaluator.calls) == 1
        assert plan.generate_reply is False
        assert storage.awaiting_clarification is False
