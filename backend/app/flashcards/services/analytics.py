"""AnalyticsService — aggregated statistics queries."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.flashcards.schemas import (
    AccuracyPoint,
    AnalyticsSummary,
    AtAGlanceStats,
    ClassificationNow,
    ClassificationOverTimePoint,
    DailyActivityPoint,
    HardestWord,
    ModePerformanceItem,
    RecentlyLearnedWord,
)
from app.flashcards.services.storage import FlashcardStorageProvider


class AnalyticsService:
    def __init__(self, storage: FlashcardStorageProvider) -> None:
        self._storage = storage

    def build_summary(self, range_param: str) -> AnalyticsSummary:
        cutoff = self._cutoff_for_range(range_param)
        return AnalyticsSummary(
            at_a_glance=self._build_at_a_glance(),
            accuracy_trend=self.accuracy_trend(cutoff),
            daily_activity=self.daily_activity(cutoff),
            classification_over_time=self.classification_over_time(cutoff),
            classification_now=self.classification_now(),
            hardest_words=self.hardest_words(limit=10, cutoff=cutoff),
            recently_learned=self._recently_learned(),
            mode_performance=self.mode_performance(cutoff),
        )

    def accuracy_trend(self, cutoff: datetime | None) -> list[AccuracyPoint]:
        sessions = self._storage.get_sessions_since(cutoff)
        points = []
        for s in sessions:
            if s.cards_reviewed == 0:
                continue
            accuracy = s.knew_it_count / s.cards_reviewed
            date_str = s.started_at.date().isoformat()
            points.append(
                AccuracyPoint(
                    session_id=s.id,
                    date=date_str,
                    accuracy=round(accuracy, 4),
                )
            )
        return points

    def daily_activity(self, cutoff: datetime | None) -> list[DailyActivityPoint]:
        sessions = self._storage.get_sessions_since(cutoff)
        by_date: dict[str, int] = defaultdict(int)
        for s in sessions:
            date_str = s.started_at.date().isoformat()
            by_date[date_str] += s.cards_reviewed
        return [
            DailyActivityPoint(date=date, cards_reviewed=count)
            for date, count in sorted(by_date.items())
        ]

    def classification_over_time(
        self, cutoff: datetime | None
    ) -> list[ClassificationOverTimePoint]:
        snapshots = self._storage.get_classification_snapshots_since(cutoff)
        return [
            ClassificationOverTimePoint(
                date=snap.snapshotted_at.date().isoformat(),
                not_practiced=snap.not_practiced_count,
                difficult=snap.difficult_count,
                almost_learned=snap.almost_learned_count,
                learned=snap.learned_count,
            )
            for snap in sorted(snapshots, key=lambda s: s.snapshotted_at)
        ]

    def classification_now(self) -> ClassificationNow:
        counts = self._storage.get_classification_counts()
        return ClassificationNow(
            not_practiced=counts.get("not_practiced", 0),
            difficult=counts.get("difficult", 0),
            almost_learned=counts.get("almost_learned", 0),
            learned=counts.get("learned", 0),
        )

    def hardest_words(self, limit: int, cutoff: datetime | None) -> list[HardestWord]:
        results = self._storage.get_card_results_since(cutoff)
        by_word: dict[int, dict[str, int]] = defaultdict(lambda: {"total": 0, "didnt_know": 0})
        for r in results:
            if r.vocabulary_item_id is None:
                continue
            by_word[r.vocabulary_item_id]["total"] += 1
            if r.rating == "didnt_know":
                by_word[r.vocabulary_item_id]["didnt_know"] += 1

        candidates = []
        for vocab_id, counts in by_word.items():
            if counts["didnt_know"] == 0:
                continue
            word = self._storage.get_word(vocab_id)
            if word is None:
                continue
            success_rate = (counts["total"] - counts["didnt_know"]) / counts["total"]
            candidates.append(
                HardestWord(
                    id=word.id,
                    word=word.word,
                    encounters=counts["total"],
                    success_rate=round(success_rate, 4),
                )
            )

        candidates.sort(key=lambda hw: hw.success_rate)
        return candidates[:limit]

    def mode_performance(self, cutoff: datetime | None) -> list[ModePerformanceItem]:
        sessions = self._storage.get_sessions_since(cutoff)
        by_mode: dict[str, dict[str, int]] = defaultdict(lambda: {"knew_it": 0, "total": 0})
        for s in sessions:
            if s.cards_reviewed == 0:
                continue
            by_mode[s.practice_mode]["knew_it"] += s.knew_it_count
            by_mode[s.practice_mode]["total"] += s.cards_reviewed

        items = []
        for mode, counts in by_mode.items():
            if counts["total"] == 0:
                continue
            accuracy = counts["knew_it"] / counts["total"]
            items.append(ModePerformanceItem(mode=mode, accuracy=round(accuracy, 4)))
        return items

    def streak(self) -> int:
        sessions = self._storage.get_sessions_since(cutoff=None)
        if not sessions:
            return 0
        completed_dates = {s.started_at.date() for s in sessions if s.started_at}
        today = datetime.now(UTC).date()
        count = 0
        check_date = today
        while check_date in completed_dates:
            count += 1
            check_date -= timedelta(days=1)
        return count

    def _build_at_a_glance(self) -> AtAGlanceStats:
        counts = self._storage.get_classification_counts()
        return AtAGlanceStats(
            total_words=sum(counts.values()),
            words_learned=counts.get("learned", 0),
            current_streak=self.streak(),
            sessions_this_week=self._count_sessions_this_week(),
        )

    def _count_sessions_this_week(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        return len(self._storage.get_sessions_since(cutoff))

    def _recently_learned(self) -> list[RecentlyLearnedWord]:
        words = self._storage.list_words(classifications=["learned"])
        result = []
        for w in words:
            schedule = self._storage.get_srs_schedule(w.id)
            if schedule and schedule.last_practiced_at:
                result.append(
                    RecentlyLearnedWord(
                        id=w.id,
                        word=w.word,
                        learned_at=schedule.last_practiced_at,
                    )
                )
        result.sort(key=lambda r: r.learned_at, reverse=True)
        return result[:10]

    def _cutoff_for_range(self, range_param: str) -> datetime | None:
        now = datetime.now(UTC)
        if range_param == "7d":
            return now - timedelta(days=7)
        if range_param == "30d":
            return now - timedelta(days=30)
        return None
