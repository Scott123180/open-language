from __future__ import annotations

from datetime import UTC, datetime, timedelta

# Days per interval stage: stage 1 = 1 day, stage 2 = 3 days, ...
STAGE_INTERVALS: list[int] = [1, 3, 7, 14, 30, 60, 120]

_MAX_STAGE = len(STAGE_INTERVALS)


class SpacedRepetitionService:
    """Manage interval-stage progression for vocabulary words."""

    def compute_next_stage(self, current_stage: int, rating: str) -> int:
        if rating == "knew_it":
            return min(current_stage + 1, _MAX_STAGE)
        if rating == "didnt_know":
            return 1
        return current_stage  # guessed — hold

    def compute_next_due_at(self, stage: int, from_time: datetime | None = None) -> datetime:
        base = from_time or datetime.now(UTC)
        clamped = max(1, min(stage, _MAX_STAGE))
        interval_days = STAGE_INTERVALS[clamped - 1]
        return base + timedelta(days=interval_days)

    def update_schedule(
        self,
        vocabulary_item_id: int,
        rating: str,
        storage,
    ) -> None:
        schedule = storage.get_srs_schedule(vocabulary_item_id)
        current_stage = schedule.interval_stage if schedule else 1
        next_stage = self.compute_next_stage(current_stage, rating)
        now = datetime.now(UTC)
        next_due = self.compute_next_due_at(next_stage, from_time=now)
        storage.upsert_srs_schedule(
            vocabulary_item_id=vocabulary_item_id,
            interval_stage=next_stage,
            last_practiced_at=now,
            next_due_at=next_due,
        )
