"""The Strict pause: how many consecutive attempts have been corrected.

The counter counts *attempts*, not matching errors, which is what makes SC-006
(no deadlock) structural: after two corrected attempts the next message is
answered whatever it contains, including a brand-new mistake.
"""

from app.corrections.config import MAX_CONSECUTIVE_CORRECTED_ATTEMPTS
from app.corrections.services.storage import CorrectionStorageProvider


class CorrectionPauseTracker:
    def __init__(self, storage: CorrectionStorageProvider) -> None:
        self._storage = storage

    def should_evaluate(self, conversation_id: int) -> bool:
        """False once the cap is reached — the next message is simply answered."""
        state = self._storage.get_pause_state(conversation_id)
        return state.consecutive_corrected_attempts < MAX_CONSECUTIVE_CORRECTED_ATTEMPTS

    def record_correction(self, conversation_id: int) -> None:
        state = self._storage.get_pause_state(conversation_id)
        self._storage.set_pause_state(
            conversation_id,
            attempts=state.consecutive_corrected_attempts + 1,
            awaiting_clarification=False,
        )

    def record_clean_message(self, conversation_id: int) -> None:
        state = self._storage.get_pause_state(conversation_id)
        if state.consecutive_corrected_attempts == 0 and not state.awaiting_clarification:
            return
        self._storage.set_pause_state(conversation_id, attempts=0, awaiting_clarification=False)

    def may_request_repeat(self, conversation_id: int) -> bool:
        """FR-027: one ask-to-repeat, never a second — a bad mic cannot stall a scenario."""
        return not self._storage.get_pause_state(conversation_id).awaiting_clarification

    def record_repeat_request(self, conversation_id: int) -> None:
        state = self._storage.get_pause_state(conversation_id)
        self._storage.set_pause_state(
            conversation_id,
            attempts=state.consecutive_corrected_attempts,
            awaiting_clarification=True,
        )

    def clear_clarification(self, conversation_id: int) -> None:
        state = self._storage.get_pause_state(conversation_id)
        if not state.awaiting_clarification:
            return
        self._storage.set_pause_state(
            conversation_id,
            attempts=state.consecutive_corrected_attempts,
            awaiting_clarification=False,
        )

    def release_pause(self, conversation_id: int) -> None:
        """Clear the cap so the conversation resumes from a clean slate (FR-018)."""
        self._storage.set_pause_state(conversation_id, attempts=0, awaiting_clarification=False)
