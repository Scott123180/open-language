"""FR-026 / SC-004a: every evaluation failure looks exactly like Off mode."""

import asyncio
import logging

from app.corrections.services.strategies import CorrectionStrategy, TurnContext, TurnPlan
from app.services.llm.base import LLMError

_OFF_MODE_SEQUENCE = ["user_message_saved", "token", "token", "done"]


def _kinds(events: list[dict]) -> list[str]:
    sequence = []
    for event in events:
        if "token" in event:
            sequence.append("token")
        elif event.get("done"):
            sequence.append("done")
        elif "error" in event:
            sequence.append("error")
        else:
            sequence.append(event["event"])
    return sequence


class HangingStrategy(CorrectionStrategy):
    """Exceeds any timeout the router is willing to wait."""

    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        await asyncio.sleep(30)
        raise AssertionError("the router must not wait this long")


class RaisingStrategy(CorrectionStrategy):
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        raise self._error


class UnparseableOutputStrategy(CorrectionStrategy):
    """Stands in for an evaluator that returned prose: no findings survive parsing."""

    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        return TurnPlan(feedback=(), generate_reply=True, reply_prompt_suffix=None)


def _short_timeout(monkeypatch) -> None:
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "correction_timeout_seconds", 0.05, raising=False)


class TestTimeoutFailsOpen:
    def test_the_reply_is_still_delivered(self, make_harness, monkeypatch) -> None:
        _short_timeout(monkeypatch)
        harness = make_harness(mode="strict", strategy=HangingStrategy())
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert _kinds(events) == _OFF_MODE_SEQUENCE

    def test_no_feedback_and_no_error_frame_reach_the_learner(
        self, make_harness, monkeypatch
    ) -> None:
        _short_timeout(monkeypatch)
        harness = make_harness(mode="strict", strategy=HangingStrategy())
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert all(e.get("event") != "feedback" for e in events)
        assert all("error" not in e for e in events)

    def test_the_timeout_is_logged_as_a_warning(self, make_harness, monkeypatch, caplog) -> None:
        _short_timeout(monkeypatch)
        harness = make_harness(mode="strict", strategy=HangingStrategy())
        conv_id = harness.create_conversation()

        with caplog.at_level(logging.WARNING, logger="app.routers.chat"):
            harness.send(conv_id, "Yo tener veinte años")

        assert any(record.levelno == logging.WARNING for record in caplog.records)


class TestLlmErrorFailsOpen:
    def test_the_reply_is_still_delivered(self, make_harness) -> None:
        harness = make_harness(mode="gentle", strategy=RaisingStrategy(LLMError("down")))
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert _kinds(events) == _OFF_MODE_SEQUENCE

    def test_the_failure_is_logged_as_a_warning(self, make_harness, caplog) -> None:
        harness = make_harness(mode="gentle", strategy=RaisingStrategy(LLMError("down")))
        conv_id = harness.create_conversation()

        with caplog.at_level(logging.WARNING, logger="app.routers.chat"):
            harness.send(conv_id, "Yo tener veinte años")

        assert any(record.levelno == logging.WARNING for record in caplog.records)

    def test_no_correction_rows_are_written(self, make_harness) -> None:
        harness = make_harness(mode="gentle", strategy=RaisingStrategy(LLMError("down")))
        conv_id = harness.create_conversation()

        harness.send(conv_id, "Yo tener veinte años")

        assert harness.correction_storage.list_feedback(conv_id) == []


class TestUnparseableOutputFailsOpen:
    def test_the_stream_is_identical_to_off_mode(self, make_harness) -> None:
        harness = make_harness(mode="strict", strategy=UnparseableOutputStrategy())
        conv_id = harness.create_conversation()

        events = harness.send(conv_id, "Yo tener veinte años")

        assert _kinds(events) == _OFF_MODE_SEQUENCE

    def test_off_mode_and_a_failed_evaluation_produce_the_same_stream(self, make_harness) -> None:
        failing = make_harness(mode="strict", strategy=UnparseableOutputStrategy())
        failing_events = failing.send(failing.create_conversation(), "Yo tener veinte años")

        off = make_harness(mode="off")
        off_events = off.send(off.create_conversation(), "Yo tener veinte años")

        assert _kinds(failing_events) == _kinds(off_events)
