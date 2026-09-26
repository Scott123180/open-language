"""The corrections replay endpoint (contracts/api.md §1.5).

Rebuilds everything the chat screen needs to show a conversation's feedback
after a reload (FR-022, FR-029).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.corrections.schemas import (
    ConversationFeedbackResponse,
    rendered_notes,
    to_note_response,
)
from app.corrections.services.storage import CorrectionStorageProvider
from app.services.factory import get_correction_storage, get_storage
from app.services.storage.base import StorageProvider

router = APIRouter(tags=["corrections"])


@router.get(
    "/corrections/conversations/{conversation_id}",
    response_model=ConversationFeedbackResponse,
)
def get_conversation_feedback(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    correction_storage: CorrectionStorageProvider = Depends(get_correction_storage),
):
    if storage.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    pause = correction_storage.get_pause_state(conversation_id)
    notes = rendered_notes(correction_storage.list_feedback(conversation_id))
    return ConversationFeedbackResponse(
        conversation_id=conversation_id,
        awaiting_retry=pause.awaiting_retry,
        awaiting_clarification=pause.awaiting_clarification,
        consecutive_corrected_attempts=pause.consecutive_corrected_attempts,
        feedback=[to_note_response(note) for note in notes],
    )
