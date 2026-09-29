from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.conversation_levels import DEFAULT_CONVERSATION_LEVEL
from app.database import Base
from app.practice_languages import DEFAULT_PRACTICE_LANGUAGE
from app.services.llm.catalog import DEFAULT_PROVIDER_ID
from app.services.llm.selection_types import DEFAULT_EFFORT
from app.services.storage.base import DEFAULT_SUMMARY_LANGUAGE


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    llm_provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DEFAULT_PROVIDER_ID
    )
    llm_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default=lambda: get_settings().ollama_model
    )
    llm_effort: Mapped[str] = mapped_column(String(10), nullable=False, default=DEFAULT_EFFORT)
    target_language: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DEFAULT_PRACTICE_LANGUAGE
    )
    native_language: Mapped[str] = mapped_column(String(20), nullable=False, default="en")
    # Legacy (pre-006): read once by `_seed_voice_choices`; never written.
    tts_voice: Mapped[str] = mapped_column(
        String(200), nullable=False, default="es_ES-davefx-medium"
    )
    suggestion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    whisper_model: Mapped[str] = mapped_column(String(50), nullable=False, default="base")
    correction_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="off")
    conversation_level: Mapped[str] = mapped_column(
        String(12), nullable=False, default=DEFAULT_CONVERSATION_LEVEL.value
    )
    summary_language: Mapped[str] = mapped_column(
        String(12), nullable=False, default=DEFAULT_SUMMARY_LANGUAGE
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
