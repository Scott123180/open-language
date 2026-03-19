import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ToolType(str, enum.Enum):
    GRAMMAR = "grammar"
    TRANSLATION = "translation"
    ALTERNATIVE_PHRASING = "alternative_phrasing"
    WORD_LOOKUP = "word_lookup"


class LearningToolResult(Base):
    __tablename__ = "learning_tool_results"
    __table_args__ = (
        UniqueConstraint("message_id", "tool_type", "input_selection", name="uq_tool_result"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_type: Mapped[ToolType] = mapped_column(SAEnum(ToolType), nullable=False)
    input_selection: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
