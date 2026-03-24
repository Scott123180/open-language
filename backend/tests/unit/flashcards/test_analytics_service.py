"""Unit tests for AnalyticsService (T085).

Covers:
  - accuracy_trend: per-session accuracy from CardResults
  - daily_activity: cards reviewed per day
  - classification_over_time: from SessionClassificationSnapshot
  - classification_now: current word counts per class
  - hardest_words: ranked by didnt_know ratio
  - mode_performance: accuracy grouped by practice mode
  - streak: consecutive days with sessions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from app.flashcards.services.analytics import AnalyticsService
from app.flashcards.services.storage import (
    CardResultRecord,
    ClassificationSnapshotRecord,
    SessionRecord,
    WordRecord,
)

# ---------------------------------------------------------------------------
# Minimal in-memory storage stub
# ---------------------------------------------------------------------------


@dataclass
class FakeStorage:
    words: list[WordRecord] = field(default_factory=list)
    sessions: list[SessionRecord] = field(default_factory=list)
    card_results: list[CardResultRecord] = field(default_factory=list)
    snapshots: list[ClassificationSnapshotRecord] = field(default_factory=list)
    classification_counts: dict[str, int] = field(default_factory=dict)

    # -- word library --
    def list_words(
        self, classifications=None, date_from=None, date_to=None, search=None, word_ids=None
    ):
        return self.words

    def get_word(self, vocabulary_item_id):
        for w in self.words:
            if w.id == vocabulary_item_id:
                return w
        return None

    # -- analytics --
    def get_sessions_since(self, cutoff):
        if cutoff is None:
            return list(self.sessions)
        return [s for s in self.sessions if s.started_at >= cutoff]

    def get_card_results_since(self, cutoff):
        session_ids = {s.id for s in self.get_sessions_since(cutoff)}
        return [r for r in self.card_results if r.session_id in session_ids]

    def get_classification_counts(self):
        return dict(self.classification_counts)

    def get_classification_snapshots_since(self, cutoff):
        if cutoff is None:
            return list(self.snapshots)
        return [s for s in self.snapshots if s.snapshotted_at >= cutoff]

    # -- stubs for unused methods --
    def get_recent_ratings(self, *a, **kw):
        return []

    def get_srs_schedule(self, *a, **kw):
        return None

    def create_classification_snapshot(self, *a, **kw):
        pass


def _make_word(id, word="hello", classification="not_practiced"):
    return WordRecord(
        id=id,
        word=word,
        translation="hola",
        target_language="es",
        native_language="en",
        source_conversation_id=None,
        saved_at=datetime.now(UTC),
        classification=classification,
        manual_override=False,
        tts_cache_path=None,
    )


def _make_session(
    id,
    practice_mode="recall",
    algorithm="mixed_review",
    days_ago=0,
    knew_it=0,
    guessed=0,
    didnt_know=0,
    cards_reviewed=None,
    total_cards=5,
    completed=True,
):
    started = datetime.now(UTC) - timedelta(days=days_ago)
    reviewed = cards_reviewed if cards_reviewed is not None else knew_it + guessed + didnt_know
    return SessionRecord(
        id=id,
        deck_id=1,
        practice_mode=practice_mode,
        algorithm=algorithm,
        started_at=started,
        ended_at=started + timedelta(minutes=10),
        total_cards=total_cards,
        cards_reviewed=reviewed,
        knew_it_count=knew_it,
        guessed_count=guessed,
        didnt_know_count=didnt_know,
        completed=completed,
    )


def _make_result(id, session_id, vocab_id, rating, days_ago=0):
    rated = datetime.now(UTC) - timedelta(days=days_ago)
    return CardResultRecord(
        id=id,
        session_id=session_id,
        vocabulary_item_id=vocab_id,
        rating=rating,
        response_type=None,
        user_response=None,
        rated_at=rated,
    )


def _make_snapshot(id, session_id, days_ago=0, np=0, d=0, al=0, ln=0):
    snapped = datetime.now(UTC) - timedelta(days=days_ago)
    return ClassificationSnapshotRecord(
        id=id,
        session_id=session_id,
        snapshotted_at=snapped,
        not_practiced_count=np,
        difficult_count=d,
        almost_learned_count=al,
        learned_count=ln,
    )


# ---------------------------------------------------------------------------
# accuracy_trend
# ---------------------------------------------------------------------------


class TestAccuracyTrend:
    def test_single_session_all_knew_it(self):
        storage = FakeStorage(
            sessions=[_make_session(1, knew_it=4, guessed=0, didnt_know=0, cards_reviewed=4)],
        )
        svc = AnalyticsService(storage)
        trend = svc.accuracy_trend(cutoff=None)
        assert len(trend) == 1
        assert trend[0].session_id == 1
        assert trend[0].accuracy == 1.0

    def test_partial_accuracy(self):
        storage = FakeStorage(
            sessions=[_make_session(1, knew_it=2, guessed=1, didnt_know=1, cards_reviewed=4)],
        )
        svc = AnalyticsService(storage)
        trend = svc.accuracy_trend(cutoff=None)
        assert trend[0].accuracy == pytest.approx(0.5)

    def test_cutoff_excludes_old_sessions(self):
        storage = FakeStorage(
            sessions=[
                _make_session(1, knew_it=3, days_ago=10, cards_reviewed=3),
                _make_session(2, knew_it=1, days_ago=1, cards_reviewed=1),
            ]
        )
        svc = AnalyticsService(storage)
        cutoff = datetime.now(UTC) - timedelta(days=5)
        trend = svc.accuracy_trend(cutoff=cutoff)
        assert len(trend) == 1
        assert trend[0].session_id == 2

    def test_zero_reviewed_excluded(self):
        storage = FakeStorage(
            sessions=[_make_session(1, knew_it=0, guessed=0, didnt_know=0, cards_reviewed=0)],
        )
        svc = AnalyticsService(storage)
        trend = svc.accuracy_trend(cutoff=None)
        assert len(trend) == 0


# ---------------------------------------------------------------------------
# daily_activity
# ---------------------------------------------------------------------------


class TestDailyActivity:
    def test_single_day(self):
        storage = FakeStorage(
            sessions=[_make_session(1, cards_reviewed=5, days_ago=0)],
        )
        svc = AnalyticsService(storage)
        activity = svc.daily_activity(cutoff=None)
        assert len(activity) >= 1
        today = datetime.now(UTC).date().isoformat()
        today_point = next((p for p in activity if p.date == today), None)
        assert today_point is not None
        assert today_point.cards_reviewed == 5

    def test_two_sessions_same_day_aggregated(self):
        s1 = _make_session(1, cards_reviewed=3, days_ago=0)
        s2 = _make_session(2, cards_reviewed=4, days_ago=0)
        storage = FakeStorage(sessions=[s1, s2])
        svc = AnalyticsService(storage)
        activity = svc.daily_activity(cutoff=None)
        today = datetime.now(UTC).date().isoformat()
        today_point = next((p for p in activity if p.date == today), None)
        assert today_point is not None
        assert today_point.cards_reviewed == 7

    def test_cutoff_excludes_older_days(self):
        storage = FakeStorage(
            sessions=[
                _make_session(1, cards_reviewed=5, days_ago=40),
                _make_session(2, cards_reviewed=2, days_ago=1),
            ]
        )
        svc = AnalyticsService(storage)
        cutoff = datetime.now(UTC) - timedelta(days=30)
        activity = svc.daily_activity(cutoff=cutoff)
        total = sum(p.cards_reviewed for p in activity)
        assert total == 2


# ---------------------------------------------------------------------------
# classification_over_time
# ---------------------------------------------------------------------------


class TestClassificationOverTime:
    def test_returns_snapshot_data(self):
        storage = FakeStorage(
            snapshots=[_make_snapshot(1, session_id=1, days_ago=2, np=10, d=3, al=2, ln=1)],
        )
        svc = AnalyticsService(storage)
        series = svc.classification_over_time(cutoff=None)
        assert len(series) == 1
        pt = series[0]
        assert pt.not_practiced == 10
        assert pt.difficult == 3
        assert pt.almost_learned == 2
        assert pt.learned == 1

    def test_cutoff_filters_snapshots(self):
        storage = FakeStorage(
            snapshots=[
                _make_snapshot(1, session_id=1, days_ago=40, np=5, d=0, al=0, ln=0),
                _make_snapshot(2, session_id=2, days_ago=2, np=3, d=1, al=1, ln=2),
            ]
        )
        svc = AnalyticsService(storage)
        cutoff = datetime.now(UTC) - timedelta(days=30)
        series = svc.classification_over_time(cutoff=cutoff)
        assert len(series) == 1
        assert series[0].not_practiced == 3


# ---------------------------------------------------------------------------
# classification_now
# ---------------------------------------------------------------------------


class TestClassificationNow:
    def test_returns_current_counts(self):
        storage = FakeStorage(
            classification_counts={
                "not_practiced": 10,
                "difficult": 3,
                "almost_learned": 5,
                "learned": 7,
            }
        )
        svc = AnalyticsService(storage)
        now = svc.classification_now()
        assert now.not_practiced == 10
        assert now.difficult == 3
        assert now.almost_learned == 5
        assert now.learned == 7

    def test_missing_classifications_default_to_zero(self):
        storage = FakeStorage(classification_counts={"learned": 4})
        svc = AnalyticsService(storage)
        now = svc.classification_now()
        assert now.not_practiced == 0
        assert now.difficult == 0
        assert now.learned == 4


# ---------------------------------------------------------------------------
# hardest_words
# ---------------------------------------------------------------------------


class TestHardestWords:
    def test_ranked_by_didnt_know_ratio(self):
        words = [
            _make_word(1, word="gato"),
            _make_word(2, word="perro"),
        ]
        results = [
            # word 1: 2 didnt_know out of 4 → 50% fail rate
            _make_result(1, session_id=1, vocab_id=1, rating="didnt_know"),
            _make_result(2, session_id=1, vocab_id=1, rating="didnt_know"),
            _make_result(3, session_id=1, vocab_id=1, rating="knew_it"),
            _make_result(4, session_id=1, vocab_id=1, rating="knew_it"),
            # word 2: 3 didnt_know out of 4 → 75% fail rate
            _make_result(5, session_id=1, vocab_id=2, rating="didnt_know"),
            _make_result(6, session_id=1, vocab_id=2, rating="didnt_know"),
            _make_result(7, session_id=1, vocab_id=2, rating="didnt_know"),
            _make_result(8, session_id=1, vocab_id=2, rating="knew_it"),
        ]
        sessions = [_make_session(1)]
        storage = FakeStorage(words=words, sessions=sessions, card_results=results)
        svc = AnalyticsService(storage)
        hardest = svc.hardest_words(limit=10, cutoff=None)
        assert hardest[0].id == 2  # perro is harder
        assert hardest[1].id == 1

    def test_respects_limit(self):
        words = [_make_word(i, word=f"word{i}") for i in range(1, 6)]
        results = [
            _make_result(i, session_id=1, vocab_id=i, rating="didnt_know") for i in range(1, 6)
        ]
        sessions = [_make_session(1)]
        storage = FakeStorage(words=words, sessions=sessions, card_results=results)
        svc = AnalyticsService(storage)
        hardest = svc.hardest_words(limit=3, cutoff=None)
        assert len(hardest) <= 3

    def test_excludes_words_with_no_didnt_know(self):
        words = [_make_word(1, word="fácil")]
        results = [_make_result(1, session_id=1, vocab_id=1, rating="knew_it")]
        sessions = [_make_session(1)]
        storage = FakeStorage(words=words, sessions=sessions, card_results=results)
        svc = AnalyticsService(storage)
        hardest = svc.hardest_words(limit=10, cutoff=None)
        assert len(hardest) == 0


# ---------------------------------------------------------------------------
# mode_performance
# ---------------------------------------------------------------------------


class TestModePerformance:
    def test_accuracy_per_mode(self):
        sessions = [
            _make_session(1, practice_mode="recall", knew_it=3, cards_reviewed=4),
            _make_session(2, practice_mode="produce", knew_it=2, cards_reviewed=4),
        ]
        storage = FakeStorage(sessions=sessions)
        svc = AnalyticsService(storage)
        perf = svc.mode_performance(cutoff=None)
        modes = {p.mode: p.accuracy for p in perf}
        assert "recall" in modes
        assert modes["recall"] == pytest.approx(0.75)
        assert "produce" in modes
        assert modes["produce"] == pytest.approx(0.5)

    def test_multiple_sessions_same_mode_averaged(self):
        sessions = [
            _make_session(1, practice_mode="recall", knew_it=4, cards_reviewed=4),
            _make_session(2, practice_mode="recall", knew_it=0, cards_reviewed=4),
        ]
        storage = FakeStorage(sessions=sessions)
        svc = AnalyticsService(storage)
        perf = svc.mode_performance(cutoff=None)
        recall = next(p for p in perf if p.mode == "recall")
        assert recall.accuracy == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# streak
# ---------------------------------------------------------------------------


class TestStreak:
    def test_no_sessions_returns_zero(self):
        storage = FakeStorage()
        svc = AnalyticsService(storage)
        assert svc.streak() == 0

    def test_practiced_today_is_streak_1(self):
        storage = FakeStorage(sessions=[_make_session(1, days_ago=0)])
        svc = AnalyticsService(storage)
        assert svc.streak() >= 1

    def test_consecutive_days_count(self):
        storage = FakeStorage(
            sessions=[
                _make_session(1, days_ago=0),
                _make_session(2, days_ago=1),
                _make_session(3, days_ago=2),
            ]
        )
        svc = AnalyticsService(storage)
        assert svc.streak() == 3

    def test_gap_breaks_streak(self):
        storage = FakeStorage(
            sessions=[
                _make_session(1, days_ago=0),
                _make_session(2, days_ago=2),  # gap on day 1
            ]
        )
        svc = AnalyticsService(storage)
        assert svc.streak() == 1
