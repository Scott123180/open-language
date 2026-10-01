"""The learner's message: what a client sends, and how it is stored."""

from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.storage.base import MessageRecord, StorageProvider

USER_ROLE = "user"


class LearnerMessageRequest(BaseModel):
    content: str
    input_source: str = "keyboard"
    transcription_confidence: float | None = Field(None, ge=0.0, le=1.0)

    @property
    def spoken_confidence(self) -> float | None:
        """The value is client-supplied, so it counts only for spoken input."""
        if self.input_source != "voice":
            return None
        return self.transcription_confidence


def _is_low_confidence(confidence: float | None) -> bool:
    """None means "no information" and is never gated (FR-010a); 0.0 is."""
    if confidence is None:
        return False
    return confidence < get_settings().low_confidence_threshold


def save_learner_message(
    storage: StorageProvider, conversation_id: int, req: LearnerMessageRequest
) -> MessageRecord:
    confidence = req.spoken_confidence
    return storage.save_message(
        conversation_id=conversation_id,
        role=USER_ROLE,
        content=req.content,
        input_source=req.input_source,
        transcription_confidence=confidence,
        is_low_confidence=_is_low_confidence(confidence) if confidence is not None else None,
    )
