"""The podcast tables (data-model §2.1–§2.4). Each cascades from `conversations`."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.podcasts.catalog import DEFAULT_PODCAST_FORMAT

_EPISODE_ID = "podcast_episodes.conversation_id"
_EMPTY_INTERESTS = "[]"


def _now() -> datetime:
    return datetime.now(UTC)


class PodcastEpisode(Base):
    __tablename__ = "podcast_episodes"

    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    show_source: Mapped[str] = mapped_column(String(12), nullable=False)
    show_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    premise: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    learner_role: Mapped[str] = mapped_column(String(12), nullable=False)
    format: Mapped[str] = mapped_column(String(12), nullable=False)
    length: Mapped[str] = mapped_column(String(8), nullable=False)
    learner_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PodcastHost(Base):
    __tablename__ = "podcast_hosts"
    __table_args__ = (
        UniqueConstraint("conversation_id", "slot"),
        UniqueConstraint("conversation_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(_EPISODE_ID, ondelete="CASCADE"), nullable=False, index=True
    )
    slot: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    personality: Mapped[str] = mapped_column(String(30), nullable=False)
    voice_key: Mapped[str] = mapped_column(String(200), nullable=False)
    show_role: Mapped[str] = mapped_column(String(20), nullable=False)
    angle: Mapped[str | None] = mapped_column(Text, nullable=True)


class PodcastHostLine(Base):
    __tablename__ = "podcast_host_lines"

    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(_EPISODE_ID, ondelete="CASCADE"), nullable=False, index=True
    )
    host_id: Mapped[int] = mapped_column(ForeignKey("podcast_hosts.id"), nullable=False)
    intent: Mapped[str] = mapped_column(String(10), nullable=False)
    invites_learner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_revealed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    was_trimmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PodcastPreferences(Base):
    __tablename__ = "podcast_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    last_format: Mapped[str] = mapped_column(
        String(12), nullable=False, default=DEFAULT_PODCAST_FORMAT
    )
    is_show_text_on: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interests: Mapped[str] = mapped_column(Text, nullable=False, default=_EMPTY_INTERESTS)
    learner_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
