"""SessionService — session lifecycle and classification recalculation.

Responsibilities:
  - End a session (sets ended_at, completed flag)
  - Recalculate classifications for all rated words (calls ClassificationEngine)
  - Build a rich SessionSummary for the API response
  - Calculate current practice streak
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.flashcards.schemas import (
    RatingEnum,
    SessionSummary,
    WordNeedingWork,
)
from app.flashcards.services import classification as classification_engine
from app.flashcards.services.srs import SpacedRepetitionService
from app.flashcards.services.storage import FlashcardStorageProvider


class SessionService:
    def __init__(self, storage: FlashcardStorageProvider) -> None:
        self._storage = storage
        self._srs = SpacedRepetitionService()

    def end_session(self, session_id: int, completed: bool) -> SessionSummary:
        """End the session, recalculate classifications, return summary."""
        self._storage.end_session(session_id, completed)
        self._recalculate_classifications(session_id)
        self._snapshot_classifications(session_id)
        return self.build_summary(session_id)

    def _snapshot_classifications(self, session_id: int) -> None:
        """Persist current classification distribution after recalculation."""
        counts = self._storage.get_classification_counts()
        self._storage.create_classification_snapshot(
            session_id=session_id,
            not_practiced=counts.get("not_practiced", 0),
            difficult=counts.get("difficult", 0),
            almost_learned=counts.get("almost_learned", 0),
            learned=counts.get("learned", 0),
        )

    def build_summary(self, session_id: int) -> SessionSummary:
        session = self._storage.get_session(session_id)
        duration = None
        if session.ended_at and session.started_at:
            duration = int((session.ended_at - session.started_at).total_seconds())

        results = self._storage.get_card_results_for_session(session_id)
        words_needing_work = self._build_words_needing_work(results)
        streak = self._calculate_streak()

        return SessionSummary(
            session_id=session_id,
            completed=session.completed,
            cards_reviewed=session.cards_reviewed,
            total_cards=session.total_cards,
            knew_it_count=session.knew_it_count,
            guessed_count=session.guessed_count,
            didnt_know_count=session.didnt_know_count,
            duration_seconds=duration,
            current_streak=streak,
            words_needing_work=words_needing_work,
        )

    def _recalculate_classifications(self, session_id: int) -> None:
        results = self._storage.get_card_results_for_session(session_id)
        rated_vocab_ids = {r.vocabulary_item_id for r in results if r.vocabulary_item_id}

        for vocab_id in rated_vocab_ids:
            word = self._storage.get_word(vocab_id)
            if word is None:
                continue
            if word.manual_override:
                # T064: Clear override flag — automatic system resumes after session
                self._storage.update_word_classification(
                    vocab_id, word.classification, manual_override=False
                )
                continue
            history = self._storage.get_recent_ratings(vocab_id, limit=5)
            ratings = [h.rating for h in history]
            new_classification = classification_engine.recalculate(
                ratings, current_classification=word.classification
            )
            if new_classification != word.classification:
                self._storage.update_word_classification(
                    vocab_id, new_classification, manual_override=False
                )
            else:
                # Ensure manual_override is cleared even if classification unchanged
                self._storage.update_word_classification(
                    vocab_id, word.classification, manual_override=False
                )

            # T062: Update SRS schedule for words that become Learned
            most_recent_rating = ratings[0] if ratings else None
            if most_recent_rating and new_classification == "learned":
                self._srs.update_schedule(vocab_id, most_recent_rating, self._storage)

    def _build_words_needing_work(self, results) -> list[WordNeedingWork]:
        needing_work = []
        for r in results:
            if r.rating in ("didnt_know", "guessed") and r.vocabulary_item_id:
                word = self._storage.get_word(r.vocabulary_item_id)
                if word:
                    needing_work.append(
                        WordNeedingWork(
                            id=word.id,
                            word=word.word,
                            translation=word.translation,
                            rating=RatingEnum(r.rating),
                        )
                    )
        return needing_work

    def _calculate_streak(self) -> int:
        """Count consecutive calendar days with at least one completed session."""
        sessions = self._storage.get_sessions_since(cutoff=None)
        if not sessions:
            return 0

        completed_dates = {s.started_at.date() for s in sessions if s.started_at}
        if not completed_dates:
            return 0

        today = datetime.now(UTC).date()
        streak = 0
        check_date = today
        while check_date in completed_dates:
            streak += 1
            check_date -= timedelta(days=1)
        return streak
