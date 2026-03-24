"""SQLAlchemy ORM models for the flashcards domain.

All models extend the shared Base from app.database so that
create_all() creates their tables alongside existing tables.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    practice_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(30), nullable=False)
    requested_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_practiced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DeckCard(Base):
    __tablename__ = "deck_cards"
    __table_args__ = (
        UniqueConstraint("deck_id", "position", name="uq_deck_card_position"),
        Index("idx_deck_cards_deck", "deck_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    vocabulary_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="SET NULL"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_blank_sentence: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (
        Index("idx_sessions_deck", "deck_id"),
        Index("idx_sessions_started", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deck_id: Mapped[int | None] = mapped_column(
        ForeignKey("decks.id", ondelete="SET NULL"), nullable=True
    )
    practice_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_cards: Mapped[int] = mapped_column(Integer, nullable=False)
    cards_reviewed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    knew_it_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    guessed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    didnt_know_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CardResult(Base):
    __tablename__ = "card_results"
    __table_args__ = (
        Index("idx_card_results_session", "session_id"),
        Index("idx_card_results_vocab", "vocabulary_item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    vocabulary_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    response_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    user_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    rated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class FlashcardRatingHistory(Base):
    __tablename__ = "flashcard_rating_history"
    __table_args__ = (Index("idx_rating_history_vocab", "vocabulary_item_id", "rated_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vocabulary_item_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    rated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False
    )


class WordLlmCache(Base):
    __tablename__ = "word_llm_cache"
    __table_args__ = (
        UniqueConstraint(
            "vocabulary_item_id", "cache_type", "language", name="uq_llm_cache_word_type_lang"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vocabulary_item_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False
    )
    cache_type: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class SpacedRepetitionSchedule(Base):
    __tablename__ = "spaced_repetition_schedule"
    __table_args__ = (UniqueConstraint("vocabulary_item_id", name="uq_srs_vocab_item"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vocabulary_item_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False
    )
    interval_stage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_practiced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessionClassificationSnapshot(Base):
    __tablename__ = "session_classification_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    snapshotted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    not_practiced_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficult_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    almost_learned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    learned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
