"""ORM models owned by the corrections domain (data-model.md).

Both tables are created by ``create_all()``; neither modifies an existing table,
so an installation that predates feature 003 upgrades in place.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CorrectionMode(str, enum.Enum):
    OFF = "off"
    GENTLE = "gentle"
    STRICT = "strict"


class FeedbackKind(str, enum.Enum):
    CORRECTION = "correction"
    REPEAT_REQUEST = "repeat_request"


class ErrorCategory(str, enum.Enum):
    CONJUGATION = "conjugation"
    AGREEMENT = "agreement"
    WORD_CHOICE = "word_choice"
    WORD_ORDER = "word_order"


class MessageFeedback(Base):
    """One app note attached to exactly one learner-authored message."""

    __tablename__ = "message_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[FeedbackKind] = mapped_column(SAEnum(FeedbackKind), nullable=False)
    category: Mapped[ErrorCategory | None] = mapped_column(SAEnum(ErrorCategory), nullable=True)
    error_fragment: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[CorrectionMode] = mapped_column(SAEnum(CorrectionMode), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class ConversationCorrectionState(Base):
    """The Strict pause, one row per conversation, created on first Strict evaluation."""

    __tablename__ = "conversation_correction_state"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    consecutive_corrected_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    awaiting_clarification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
