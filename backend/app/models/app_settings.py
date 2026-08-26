from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    llm_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default=lambda: get_settings().ollama_model
    )
    target_language: Mapped[str] = mapped_column(String(20), nullable=False, default="es")
    native_language: Mapped[str] = mapped_column(String(20), nullable=False, default="en")
    tts_voice: Mapped[str] = mapped_column(
        String(200), nullable=False, default="es_ES-davefx-medium"
    )
    suggestion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    whisper_model: Mapped[str] = mapped_column(String(50), nullable=False, default="base")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
