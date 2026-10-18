"""The podcast tables (007 data-model §2.1–§2.4, 010 data-model §2.1–§2.5).

Every 007 table cascades from `conversations`; every 010 table from a new parent or from
`conversations`, so a deleted conversation takes its series link and memories with it.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.podcasts.catalog import DEFAULT_PODCAST_FORMAT

_EPISODE_ID = "podcast_episodes.conversation_id"
_SERIES_ID = "podcast_series.id"
_CASCADE = "CASCADE"
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


class PodcastShow(Base):
    """A show the learner has state for: a ready-made template id, or a learner-made show."""

    __tablename__ = "podcast_shows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    source: Mapped[str] = mapped_column(String(12), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    premise: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    learner_role: Mapped[str | None] = mapped_column(String(12), nullable=True)
    lead_personality: Mapped[str | None] = mapped_column(String(30), nullable=True)
    second_personality: Mapped[str | None] = mapped_column(String(30), nullable=True)
    lead_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    second_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    favourited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PodcastSeries(Base):
    """One show in one practice language."""

    __tablename__ = "podcast_series"
    __table_args__ = (UniqueConstraint("show_id", "target_language"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    show_id: Mapped[int] = mapped_column(
        ForeignKey("podcast_shows.id", ondelete=_CASCADE), nullable=False
    )
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PodcastSeriesHost(Base):
    """A series' host in one slot. A recast updates the row in place."""

    __tablename__ = "podcast_series_hosts"
    __table_args__ = (UniqueConstraint("series_id", "slot"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey(_SERIES_ID, ondelete=_CASCADE), nullable=False
    )
    slot: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    personality: Mapped[str] = mapped_column(String(30), nullable=False)
    voice_key: Mapped[str] = mapped_column(String(200), nullable=False)
    show_role: Mapped[str] = mapped_column(String(20), nullable=False)
    angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    joined_after_episodes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class PodcastSeriesEpisode(Base):
    """The link that makes an episode part of a series. One-off episodes have none."""

    __tablename__ = "podcast_series_episodes"

    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(_EPISODE_ID, ondelete=_CASCADE), primary_key=True
    )
    series_id: Mapped[int] = mapped_column(
        ForeignKey(_SERIES_ID, ondelete=_CASCADE), nullable=False, index=True
    )
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    remembered_up_to_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PodcastSeriesMemory(Base):
    """One remembered point, in the conversation's language and in English."""

    __tablename__ = "podcast_series_memories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey(_SERIES_ID, ondelete=_CASCADE), nullable=False, index=True
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete=_CASCADE), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    conversation_language: Mapped[str] = mapped_column(Text, nullable=False)
    english: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
