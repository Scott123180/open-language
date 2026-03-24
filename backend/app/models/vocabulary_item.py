from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WordClassification(str, Enum):
    NOT_PRACTICED = "not_practiced"
    DIFFICULT = "difficult"
    ALMOST_LEARNED = "almost_learned"
    LEARNED = "learned"


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"
    __table_args__ = (UniqueConstraint("word", "target_language", name="uq_vocabulary_word_lang"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(500), nullable=False)
    translation: Mapped[str] = mapped_column(String(500), nullable=False)
    target_language: Mapped[str] = mapped_column(String(20), nullable=False)
    native_language: Mapped[str] = mapped_column(String(20), nullable=False)
    source_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    classification: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WordClassification.NOT_PRACTICED.value
    )
    manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tts_cache_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
