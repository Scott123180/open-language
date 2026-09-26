"""SQLite implementation of CorrectionStorageProvider."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.corrections.models import (
    ConversationCorrectionState,
    CorrectionMode,
    ErrorCategory,
    FeedbackKind,
    MessageFeedback,
)
from app.corrections.services.storage import (
    CorrectionStorageProvider,
    FeedbackDraft,
    FeedbackRecord,
    PauseSnapshot,
)
from app.models.message import Message, MessageRole

_ZEROED_PAUSE = PauseSnapshot(
    consecutive_corrected_attempts=0, awaiting_clarification=False, awaiting_retry=False
)


def _to_record(row: MessageFeedback) -> FeedbackRecord:
    return FeedbackRecord(
        id=row.id,
        message_id=row.message_id,
        kind=row.kind.value,
        category=row.category.value if row.category else None,
        error_fragment=row.error_fragment,
        corrected_text=row.corrected_text,
        explanation=row.explanation,
        mode=row.mode.value,
        rank=row.rank,
        created_at=row.created_at,
    )


def _to_row(message_id: int, draft: FeedbackDraft) -> MessageFeedback:
    return MessageFeedback(
        message_id=message_id,
        kind=FeedbackKind(draft.kind),
        category=ErrorCategory(draft.category) if draft.category else None,
        error_fragment=draft.error_fragment,
        corrected_text=draft.corrected_text,
        explanation=draft.explanation,
        mode=CorrectionMode(draft.mode),
        rank=draft.rank,
        created_at=datetime.now(UTC),
    )


class SQLiteCorrectionStorageProvider(CorrectionStorageProvider):
    def __init__(self, db: Session) -> None:
        self._db = db

    def save_feedback(
        self, message_id: int, drafts: Sequence[FeedbackDraft]
    ) -> list[FeedbackRecord]:
        rows = [_to_row(message_id, draft) for draft in drafts]
        self._db.add_all(rows)
        self._db.commit()
        for row in rows:
            self._db.refresh(row)
        return [_to_record(row) for row in rows]

    def list_feedback(self, conversation_id: int) -> list[FeedbackRecord]:
        rows = (
            self._db.query(MessageFeedback)
            .join(Message, Message.id == MessageFeedback.message_id)
            .filter(Message.conversation_id == conversation_id)
            .order_by(MessageFeedback.message_id.asc(), MessageFeedback.rank.asc())
            .all()
        )
        return [_to_record(row) for row in rows]

    def get_pause_state(self, conversation_id: int) -> PauseSnapshot:
        state = self._db.get(ConversationCorrectionState, conversation_id)
        if state is None:
            return _ZEROED_PAUSE
        return self._snapshot(conversation_id, state)

    def set_pause_state(
        self, conversation_id: int, attempts: int, awaiting_clarification: bool
    ) -> PauseSnapshot:
        state = self._db.get(ConversationCorrectionState, conversation_id)
        if state is None:
            state = ConversationCorrectionState(conversation_id=conversation_id)
            self._db.add(state)
        state.consecutive_corrected_attempts = attempts
        state.awaiting_clarification = awaiting_clarification
        state.updated_at = datetime.now(UTC)
        self._db.commit()
        self._db.refresh(state)
        return self._snapshot(conversation_id, state)

    def _snapshot(self, conversation_id: int, state: ConversationCorrectionState) -> PauseSnapshot:
        return PauseSnapshot(
            consecutive_corrected_attempts=state.consecutive_corrected_attempts,
            awaiting_clarification=state.awaiting_clarification,
            awaiting_retry=(
                state.consecutive_corrected_attempts > 0
                and self._last_message_is_from_the_learner(conversation_id)
            ),
        )

    def _last_message_is_from_the_learner(self, conversation_id: int) -> bool:
        last = (
            self._db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .first()
        )
        return last is not None and last.role == MessageRole.USER
