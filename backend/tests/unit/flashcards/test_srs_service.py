"""Unit tests for SpacedRepetitionService — T059.

Covers:
  - Stage advances on knew_it
  - Stage holds on guessed
  - Stage resets to 1 on didnt_know
  - next_due_at computed correctly per stage interval
  - Stage caps at maximum
  - New schedule is created when none exists
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.flashcards.services.srs import STAGE_INTERVALS, SpacedRepetitionService


@pytest.fixture()
def service():
    return SpacedRepetitionService()


def _make_schedule(stage: int, next_due_at=None) -> MagicMock:
    s = MagicMock()
    s.interval_stage = stage
    s.next_due_at = next_due_at
    return s


class TestStageAdvancement:
    def test_knew_it_advances_stage(self, service):
        result = service.compute_next_stage(current_stage=1, rating="knew_it")
        assert result > 1

    def test_guessed_holds_stage(self, service):
        result = service.compute_next_stage(current_stage=2, rating="guessed")
        assert result == 2

    def test_didnt_know_resets_to_stage_one(self, service):
        result = service.compute_next_stage(current_stage=4, rating="didnt_know")
        assert result == 1

    def test_stage_does_not_exceed_maximum(self, service):
        max_stage = len(STAGE_INTERVALS)
        result = service.compute_next_stage(current_stage=max_stage, rating="knew_it")
        assert result <= max_stage


class TestNextDueAt:
    def test_next_due_at_uses_stage_interval(self, service):
        now = datetime.now(UTC)
        next_due = service.compute_next_due_at(stage=1, from_time=now)
        expected_interval = STAGE_INTERVALS[0]
        assert abs((next_due - now).days - expected_interval) <= 1

    def test_higher_stage_produces_later_due_date(self, service):
        now = datetime.now(UTC)
        due_stage_1 = service.compute_next_due_at(stage=1, from_time=now)
        due_stage_2 = service.compute_next_due_at(stage=2, from_time=now)
        assert due_stage_2 > due_stage_1

    def test_all_stage_intervals_produce_future_dates(self, service):
        now = datetime.now(UTC)
        for stage in range(1, len(STAGE_INTERVALS) + 1):
            due = service.compute_next_due_at(stage=stage, from_time=now)
            assert due > now


class _RecordingSrsStorage:
    """Storage double whose SRS methods mirror FlashcardStorageProvider exactly.

    The signatures deliberately omit **kwargs so that calling upsert_srs_schedule
    with an argument the real interface does not accept raises TypeError here,
    exactly as it would against SQLiteFlashcardStorageProvider.
    """

    def __init__(self, existing_schedule=None) -> None:
        self.existing_schedule = existing_schedule
        self.upserts: list[dict] = []

    def get_srs_schedule(self, vocabulary_item_id: int):
        return self.existing_schedule

    def upsert_srs_schedule(self, vocabulary_item_id: int, interval_stage: int, next_due_at):
        record = {
            "vocabulary_item_id": vocabulary_item_id,
            "interval_stage": interval_stage,
            "next_due_at": next_due_at,
        }
        self.upserts.append(record)
        return record


class TestUpdateSchedule:
    def test_creates_schedule_when_word_has_none(self, service):
        storage = _RecordingSrsStorage(existing_schedule=None)

        service.update_schedule(vocabulary_item_id=7, rating="knew_it", storage=storage)

        assert len(storage.upserts) == 1
        assert storage.upserts[0]["vocabulary_item_id"] == 7

    def test_knew_it_advances_persisted_stage(self, service):
        storage = _RecordingSrsStorage(existing_schedule=_make_schedule(stage=2))

        service.update_schedule(vocabulary_item_id=1, rating="knew_it", storage=storage)

        assert storage.upserts[0]["interval_stage"] == 3

    def test_didnt_know_resets_persisted_stage(self, service):
        storage = _RecordingSrsStorage(existing_schedule=_make_schedule(stage=5))

        service.update_schedule(vocabulary_item_id=1, rating="didnt_know", storage=storage)

        assert storage.upserts[0]["interval_stage"] == 1

    def test_guessed_holds_persisted_stage(self, service):
        storage = _RecordingSrsStorage(existing_schedule=_make_schedule(stage=4))

        service.update_schedule(vocabulary_item_id=1, rating="guessed", storage=storage)

        assert storage.upserts[0]["interval_stage"] == 4

    def test_next_due_at_matches_the_new_stage_interval(self, service):
        storage = _RecordingSrsStorage(existing_schedule=_make_schedule(stage=1))
        before = datetime.now(UTC)

        service.update_schedule(vocabulary_item_id=1, rating="knew_it", storage=storage)

        next_due = storage.upserts[0]["next_due_at"]
        expected_days = STAGE_INTERVALS[1]  # stage 2 after advancing from stage 1
        assert abs((next_due - before).days - expected_days) <= 1
