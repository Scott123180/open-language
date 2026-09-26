import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class InputSource(str, enum.Enum):
    VOICE = "voice"
    KEYBOARD = "keyboard"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    input_source: Mapped[InputSource | None] = mapped_column(SAEnum(InputSource), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    tts_audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # NULL means no confidence information (typed input); 0.0 means words were
    # heard from ranges that read as silence. The two must not be conflated.
    transcription_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_low_confidence: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
