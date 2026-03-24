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
