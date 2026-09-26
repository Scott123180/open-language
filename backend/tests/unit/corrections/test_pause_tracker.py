"""Unit tests for CorrectionPauseTracker — the state machine in data-model.md."""

from app.corrections.config import MAX_CONSECUTIVE_CORRECTED_ATTEMPTS
from app.corrections.services.pause_tracker import CorrectionPauseTracker
from app.corrections.services.storage import CorrectionStorageProvider, PauseSnapshot

CONVERSATION_ID = 1


class InMemoryPauseStorage(CorrectionStorageProvider):
    """Just enough storage to exercise the tracker without a database."""

    def __init__(self, attempts: int = 0, awaiting_clarification: bool = False) -> None:
        self.attempts = attempts
        self.awaiting_clarification = awaiting_clarification
        self.writes: list[tuple[int, bool]] = []

    def save_feedback(self, message_id, drafts):
        raise AssertionError("the tracker never persists feedback")

    def list_feedback(self, conversation_id):
        raise AssertionError("the tracker never reads the transcript")

    def get_pause_state(self, conversation_id: int) -> PauseSnapshot:
        return PauseSnapshot(
            consecutive_corrected_attempts=self.attempts,
            awaiting_clarification=self.awaiting_clarification,
            awaiting_retry=self.attempts > 0,
        )

    def set_pause_state(self, conversation_id, attempts, awaiting_clarification):
        self.attempts = attempts
        self.awaiting_clarification = awaiting_clarification
        self.writes.append((attempts, awaiting_clarification))
        return self.get_pause_state(conversation_id)


def _tracker(attempts: int = 0, awaiting_clarification: bool = False):
    storage = InMemoryPauseStorage(attempts, awaiting_clarification)
    return CorrectionPauseTracker(storage), storage


class TestCountingCorrectedAttempts:
    def test_a_correction_increments_the_counter(self) -> None:
        tracker, storage = _tracker(attempts=0)

        tracker.record_correction(CONVERSATION_ID)

        assert storage.attempts == 1

    def test_a_second_correction_increments_again(self) -> None:
        tracker, storage = _tracker(attempts=1)

        tracker.record_correction(CONVERSATION_ID)

        assert storage.attempts == 2

    def test_a_clean_message_resets_the_counter(self) -> None:
        tracker, storage = _tracker(attempts=1)

        tracker.record_clean_message(CONVERSATION_ID)

        assert storage.attempts == 0

    def test_a_clean_message_at_zero_writes_nothing(self) -> None:
        """No pause is open, so there is no row to create."""
        tracker, storage = _tracker(attempts=0)

        tracker.record_clean_message(CONVERSATION_ID)

        assert storage.writes == []


class TestTheCapPreventsDeadlock:
    """FR-018 / SC-006: the third message is answered whatever it contains."""

    def test_evaluation_is_skipped_at_the_cap(self) -> None:
        tracker, _ = _tracker(attempts=MAX_CONSECUTIVE_CORRECTED_ATTEMPTS)

        assert tracker.should_evaluate(CONVERSATION_ID) is False

    def test_evaluation_runs_below_the_cap(self) -> None:
        tracker, _ = _tracker(attempts=MAX_CONSECUTIVE_CORRECTED_ATTEMPTS - 1)

        assert tracker.should_evaluate(CONVERSATION_ID) is True

    def test_reaching_the_cap_resets_the_counter_for_the_next_turn(self) -> None:
        tracker, storage = _tracker(attempts=MAX_CONSECUTIVE_CORRECTED_ATTEMPTS)

        tracker.release_pause(CONVERSATION_ID)

        assert storage.attempts == 0

    def test_a_brand_new_error_at_the_cap_is_still_answered(self) -> None:
        """The counter counts attempts, not matching errors — that is what makes
        SC-006 structural rather than probabilistic."""
        tracker, storage = _tracker(attempts=MAX_CONSECUTIVE_CORRECTED_ATTEMPTS)

        should_evaluate = tracker.should_evaluate(CONVERSATION_ID)
        tracker.release_pause(CONVERSATION_ID)

        assert should_evaluate is False
        assert storage.attempts == 0
        assert tracker.should_evaluate(CONVERSATION_ID) is True


class TestClarificationRequests:
    """FR-027: at most one ask-to-repeat, then the conversation moves on."""

    def test_a_repeat_request_may_be_issued_when_none_is_outstanding(self) -> None:
        tracker, _ = _tracker(awaiting_clarification=False)

        assert tracker.may_request_repeat(CONVERSATION_ID) is True

    def test_a_second_repeat_request_is_refused(self) -> None:
        tracker, _ = _tracker(awaiting_clarification=True)

        assert tracker.may_request_repeat(CONVERSATION_ID) is False

    def test_recording_a_repeat_request_raises_the_flag(self) -> None:
        tracker, storage = _tracker()

        tracker.record_repeat_request(CONVERSATION_ID)

        assert storage.awaiting_clarification is True

    def test_a_repeat_request_leaves_the_corrected_attempt_counter_alone(self) -> None:
        tracker, storage = _tracker(attempts=1)

        tracker.record_repeat_request(CONVERSATION_ID)

        assert storage.attempts == 1

    def test_clearing_the_flag_leaves_the_counter_alone(self) -> None:
        tracker, storage = _tracker(attempts=1, awaiting_clarification=True)

        tracker.clear_clarification(CONVERSATION_ID)

        assert storage.awaiting_clarification is False
        assert storage.attempts == 1

    def test_clearing_an_unset_flag_writes_nothing(self) -> None:
        tracker, storage = _tracker(awaiting_clarification=False)

        tracker.clear_clarification(CONVERSATION_ID)

        assert storage.writes == []
