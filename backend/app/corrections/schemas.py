"""Response models for the corrections API (contracts/api.md §1.5, §2.2)."""

from datetime import datetime

from pydantic import BaseModel

from app.corrections.services.storage import FeedbackRecord

GENTLE_MODE = "gentle"


class FeedbackNoteResponse(BaseModel):
    id: int
    message_id: int
    kind: str
    category: str | None
    error_fragment: str | None
    corrected_text: str | None
    explanation: str
    mode: str
    rank: int
    created_at: datetime


class ConversationFeedbackResponse(BaseModel):
    conversation_id: int
    awaiting_retry: bool
    awaiting_clarification: bool
    consecutive_corrected_attempts: int
    feedback: list[FeedbackNoteResponse]


def to_note_response(record: FeedbackRecord) -> FeedbackNoteResponse:
    return FeedbackNoteResponse(
        id=record.id,
        message_id=record.message_id,
        kind=record.kind,
        category=record.category,
        error_fragment=record.error_fragment,
        corrected_text=record.corrected_text,
        explanation=record.explanation,
        mode=record.mode,
        rank=record.rank,
        created_at=record.created_at,
    )


def to_note_payload(record: FeedbackRecord) -> dict:
    """The same note shape, as a JSON-ready dict for the SSE frame."""
    return to_note_response(record).model_dump(mode="json")


def rendered_notes(records: list[FeedbackRecord]) -> list[FeedbackRecord]:
    """The notes a client renders: a gentle correction *is* the reply, so it is not one."""
    return [record for record in records if record.mode != GENTLE_MODE]
