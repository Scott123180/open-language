"""SQLiteSummaryStorage: one row per conversation, replaced on every new summary."""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.conversation_summary.models import ConversationSummary
from app.conversation_summary.services.storage import StoredSummary, SummaryPoint, SummaryStorage


class SQLiteSummaryStorage(SummaryStorage):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_latest(self, conversation_id: int) -> StoredSummary | None:
        row = self._db.get(ConversationSummary, conversation_id)
        return _record(row) if row is not None else None

    def save(self, summary: StoredSummary) -> None:
        row = self._db.get(ConversationSummary, summary.conversation_id)
        if row is None:
            row = ConversationSummary(conversation_id=summary.conversation_id)
            self._db.add(row)
        row.up_to_message_id = summary.up_to_message_id
        row.level = summary.level
        row.points = json.dumps(
            [_point_json(point) for point in summary.points], ensure_ascii=False
        )
        row.created_at = datetime.now(UTC)
        self._db.commit()


def _point_json(point: SummaryPoint) -> dict[str, str]:
    return {"conversation_language": point.conversation_language, "english": point.english}


def _record(row: ConversationSummary) -> StoredSummary:
    points = tuple(SummaryPoint(**point) for point in json.loads(row.points))
    return StoredSummary(row.conversation_id, row.up_to_message_id, row.level, points)
