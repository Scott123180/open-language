from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VoiceChoice(Base):
    """The voice a learner chose for one practice language. No row means the default."""

    __tablename__ = "voice_choices"

    target_language: Mapped[str] = mapped_column(String(20), primary_key=True)
    voice_key: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
