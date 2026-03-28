"""SQLiteFlashcardStorageProvider — concrete implementation of FlashcardStorageProvider.

Receives a SQLAlchemy Session via constructor injection (DIP).
Does not inherit from SQLiteStorageProvider; both share the same Session.
"""

from datetime import UTC, datetime

from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from app.flashcards.models import (
    CardResult,
    Deck,
    DeckCard,
    FlashcardRatingHistory,
    PracticeSession,
    SessionClassificationSnapshot,
    SpacedRepetitionSchedule,
    WordLlmCache,
)
from app.flashcards.services.storage import (
    CardResultRecord,
    ClassificationSnapshotRecord,
    DeckCardRecord,
    DeckRecord,
    FlashcardStorageProvider,
    LlmCacheRecord,
    RatingHistoryRecord,
    SessionRecord,
    SrsScheduleRecord,
    WordRecord,
)
from app.models.vocabulary_item import VocabularyItem


def _word_to_record(v: VocabularyItem) -> WordRecord:
    return WordRecord(
        id=v.id,
        word=v.word,
        translation=v.translation,
        target_language=v.target_language,
        native_language=v.native_language,
        source_conversation_id=v.source_conversation_id,
        saved_at=v.saved_at,
        classification=v.classification,
        manual_override=v.manual_override,
        tts_cache_path=v.tts_cache_path,
    )


def _deck_to_record(d: Deck) -> DeckRecord:
    return DeckRecord(
        id=d.id,
        name=d.name,
        practice_mode=d.practice_mode,
        algorithm=d.algorithm,
        requested_size=d.requested_size,
        created_at=d.created_at,
        last_practiced_at=d.last_practiced_at,
    )


def _deck_card_to_record(c: DeckCard) -> DeckCardRecord:
    return DeckCardRecord(
        id=c.id,
        deck_id=c.deck_id,
        vocabulary_item_id=c.vocabulary_item_id,
        position=c.position,
        fill_blank_sentence=c.fill_blank_sentence,
    )


def _session_to_record(s: PracticeSession) -> SessionRecord:
    return SessionRecord(
        id=s.id,
        deck_id=s.deck_id,
        practice_mode=s.practice_mode,
        algorithm=s.algorithm,
        started_at=s.started_at,
        ended_at=s.ended_at,
        total_cards=s.total_cards,
        cards_reviewed=s.cards_reviewed,
        knew_it_count=s.knew_it_count,
        guessed_count=s.guessed_count,
        didnt_know_count=s.didnt_know_count,
        completed=s.completed,
    )


def _card_result_to_record(r: CardResult) -> CardResultRecord:
    return CardResultRecord(
        id=r.id,
        session_id=r.session_id,
        vocabulary_item_id=r.vocabulary_item_id,
        rating=r.rating,
        response_type=r.response_type,
        user_response=r.user_response,
        rated_at=r.rated_at,
    )


def _rating_history_to_record(h: FlashcardRatingHistory) -> RatingHistoryRecord:
    return RatingHistoryRecord(
        id=h.id,
        vocabulary_item_id=h.vocabulary_item_id,
        rating=h.rating,
        rated_at=h.rated_at,
        session_id=h.session_id,
    )


def _llm_cache_to_record(c: WordLlmCache) -> LlmCacheRecord:
    return LlmCacheRecord(
        id=c.id,
        vocabulary_item_id=c.vocabulary_item_id,
        cache_type=c.cache_type,
        language=c.language,
        content=c.content,
        generated_at=c.generated_at,
    )


def _srs_to_record(s: SpacedRepetitionSchedule) -> SrsScheduleRecord:
    return SrsScheduleRecord(
        id=s.id,
        vocabulary_item_id=s.vocabulary_item_id,
        interval_stage=s.interval_stage,
        last_practiced_at=s.last_practiced_at,
        next_due_at=s.next_due_at,
    )


def _snapshot_to_record(s: SessionClassificationSnapshot) -> ClassificationSnapshotRecord:
    return ClassificationSnapshotRecord(
        id=s.id,
        session_id=s.session_id,
        snapshotted_at=s.snapshotted_at,
        not_practiced_count=s.not_practiced_count,
        difficult_count=s.difficult_count,
        almost_learned_count=s.almost_learned_count,
        learned_count=s.learned_count,
    )


_RATING_COUNTER = {
    "knew_it": "knew_it_count",
    "guessed": "guessed_count",
    "didnt_know": "didnt_know_count",
}
_MAX_RATING_HISTORY = 5


class SQLiteFlashcardStorageProvider(FlashcardStorageProvider):
    def __init__(self, db: Session) -> None:
        self._db = db

    # --- Word library ---

    def list_words(
        self,
        classifications: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> list[WordRecord]:
        query = self._db.query(VocabularyItem)
        if classifications:
            query = query.filter(VocabularyItem.classification.in_(classifications))
        if date_from:
            query = query.filter(VocabularyItem.saved_at >= date_from)
        if date_to:
            query = query.filter(VocabularyItem.saved_at <= date_to)
        if search:
            query = query.filter(VocabularyItem.word.ilike(f"%{search}%"))
        rows = query.order_by(VocabularyItem.saved_at.desc()).all()
        return [_word_to_record(r) for r in rows]

    def get_word(self, vocabulary_item_id: int) -> WordRecord | None:
        row = self._db.get(VocabularyItem, vocabulary_item_id)
        return _word_to_record(row) if row else None

    def update_word_classification(
        self, vocabulary_item_id: int, classification: str, manual_override: bool
    ) -> WordRecord:
        row = self._db.get(VocabularyItem, vocabulary_item_id)
        row.classification = classification
        row.manual_override = manual_override
        self._db.commit()
        self._db.refresh(row)
        return _word_to_record(row)

    def delete_word(self, vocabulary_item_id: int) -> None:
        row = self._db.get(VocabularyItem, vocabulary_item_id)
        self._db.delete(row)
        self._db.commit()

    def delete_words(self, ids: list[int]) -> int:
        count = 0
        for wid in ids:
            row = self._db.get(VocabularyItem, wid)
            if row is not None:
                self._db.delete(row)
                count += 1
        self._db.commit()
        return count

    def update_word_tts_path(self, vocabulary_item_id: int, tts_path: str) -> WordRecord:
        row = self._db.get(VocabularyItem, vocabulary_item_id)
        row.tts_cache_path = tts_path
        self._db.commit()
        self._db.refresh(row)
        return _word_to_record(row)

    # --- Deck management ---

    def create_deck(
        self,
        name: str,
        practice_mode: str,
        algorithm: str,
        requested_size: int,
        cards: list[dict],
    ) -> tuple[DeckRecord, list[DeckCardRecord]]:
        deck = Deck(
            name=name,
            practice_mode=practice_mode,
            algorithm=algorithm,
            requested_size=requested_size,
            created_at=datetime.now(UTC),
        )
        self._db.add(deck)
        self._db.flush()  # get deck.id before inserting cards

        card_rows = [
            DeckCard(
                deck_id=deck.id,
                vocabulary_item_id=card["vocabulary_item_id"],
                position=card["position"],
                fill_blank_sentence=card.get("fill_blank_sentence"),
            )
            for card in cards
        ]
        self._db.add_all(card_rows)
        self._db.commit()
        self._db.refresh(deck)
        for c in card_rows:
            self._db.refresh(c)
        return _deck_to_record(deck), [_deck_card_to_record(c) for c in card_rows]

    def list_decks(self) -> list[DeckRecord]:
        rows = self._db.query(Deck).order_by(Deck.created_at.desc()).all()
        return [_deck_to_record(r) for r in rows]

    def get_deck(self, deck_id: int) -> DeckRecord | None:
        row = self._db.get(Deck, deck_id)
        return _deck_to_record(row) if row else None

    def get_deck_cards(self, deck_id: int) -> list[DeckCardRecord]:
        rows = (
            self._db.query(DeckCard)
            .filter(DeckCard.deck_id == deck_id)
            .order_by(DeckCard.position.asc())
            .all()
        )
        return [_deck_card_to_record(r) for r in rows]

    def update_deck_name(self, deck_id: int, name: str) -> DeckRecord:
        row = self._db.get(Deck, deck_id)
        row.name = name
        self._db.commit()
        self._db.refresh(row)
        return _deck_to_record(row)

    def delete_deck(self, deck_id: int) -> None:
        row = self._db.get(Deck, deck_id)
        self._db.delete(row)
        self._db.commit()

    def replace_deck_cards(self, deck_id: int, cards: list[dict]) -> list[DeckCardRecord]:
        self._db.execute(delete(DeckCard).where(DeckCard.deck_id == deck_id))
        card_rows = [
            DeckCard(
                deck_id=deck_id,
                vocabulary_item_id=card["vocabulary_item_id"],
                position=card["position"],
                fill_blank_sentence=card.get("fill_blank_sentence"),
            )
            for card in cards
        ]
        self._db.add_all(card_rows)
        self._db.commit()
        for c in card_rows:
            self._db.refresh(c)
        return [_deck_card_to_record(c) for c in card_rows]

    # --- Practice sessions ---

    def create_session(
        self,
        deck_id: int,
        practice_mode: str,
        algorithm: str,
        total_cards: int,
    ) -> SessionRecord:
        session = PracticeSession(
            deck_id=deck_id,
            practice_mode=practice_mode,
            algorithm=algorithm,
            started_at=datetime.now(UTC),
            total_cards=total_cards,
        )
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return _session_to_record(session)

    def get_session(self, session_id: int) -> SessionRecord | None:
        row = self._db.get(PracticeSession, session_id)
        return _session_to_record(row) if row else None

    def add_card_result(
        self,
        session_id: int,
        vocabulary_item_id: int | None,
        rating: str,
        response_type: str | None,
        user_response: str | None,
    ) -> CardResultRecord:
        result = CardResult(
            session_id=session_id,
            vocabulary_item_id=vocabulary_item_id,
            rating=rating,
            response_type=response_type,
            user_response=user_response,
            rated_at=datetime.now(UTC),
        )
        self._db.add(result)

        # Update session counters
        session_row = self._db.get(PracticeSession, session_id)
        session_row.cards_reviewed += 1
        counter_field = _RATING_COUNTER.get(rating)
        if counter_field:
            setattr(session_row, counter_field, getattr(session_row, counter_field) + 1)

        self._db.commit()
        self._db.refresh(result)
        return _card_result_to_record(result)

    def end_session(self, session_id: int, completed: bool) -> SessionRecord:
        row = self._db.get(PracticeSession, session_id)
        row.ended_at = datetime.now(UTC)
        row.completed = completed

        # Touch deck.last_practiced_at
        if row.deck_id:
            deck_row = self._db.get(Deck, row.deck_id)
            if deck_row:
                deck_row.last_practiced_at = row.ended_at

        self._db.commit()
        self._db.refresh(row)
        return _session_to_record(row)

    def get_card_results_for_session(self, session_id: int) -> list[CardResultRecord]:
        rows = (
            self._db.query(CardResult)
            .filter(CardResult.session_id == session_id)
            .order_by(CardResult.rated_at.asc())
            .all()
        )
        return [_card_result_to_record(r) for r in rows]

    # --- Rating history ---

    def add_rating_history(
        self,
        vocabulary_item_id: int,
        rating: str,
        session_id: int,
    ) -> RatingHistoryRecord:
        entry = FlashcardRatingHistory(
            vocabulary_item_id=vocabulary_item_id,
            rating=rating,
            rated_at=datetime.now(UTC),
            session_id=session_id,
        )
        self._db.add(entry)
        self._db.flush()

        # Prune to last _MAX_RATING_HISTORY entries
        rows = (
            self._db.query(FlashcardRatingHistory)
            .filter(FlashcardRatingHistory.vocabulary_item_id == vocabulary_item_id)
            .order_by(FlashcardRatingHistory.rated_at.desc())
            .all()
        )
        if len(rows) > _MAX_RATING_HISTORY:
            for old in rows[_MAX_RATING_HISTORY:]:
                self._db.delete(old)

        self._db.commit()
        self._db.refresh(entry)
        return _rating_history_to_record(entry)

    def get_recent_ratings(
        self, vocabulary_item_id: int, limit: int = 5
    ) -> list[RatingHistoryRecord]:
        rows = (
            self._db.query(FlashcardRatingHistory)
            .filter(FlashcardRatingHistory.vocabulary_item_id == vocabulary_item_id)
            .order_by(FlashcardRatingHistory.rated_at.desc())
            .limit(limit)
            .all()
        )
        return [_rating_history_to_record(r) for r in rows]

    # --- LLM cache ---

    def get_llm_cache(
        self, vocabulary_item_id: int, cache_type: str, language: str
    ) -> LlmCacheRecord | None:
        row = (
            self._db.query(WordLlmCache)
            .filter(
                WordLlmCache.vocabulary_item_id == vocabulary_item_id,
                WordLlmCache.cache_type == cache_type,
                WordLlmCache.language == language,
            )
            .first()
        )
        return _llm_cache_to_record(row) if row else None

    def set_llm_cache(
        self,
        vocabulary_item_id: int,
        cache_type: str,
        language: str,
        content: str,
    ) -> LlmCacheRecord:
        row = (
            self._db.query(WordLlmCache)
            .filter(
                WordLlmCache.vocabulary_item_id == vocabulary_item_id,
                WordLlmCache.cache_type == cache_type,
                WordLlmCache.language == language,
            )
            .first()
        )
        if row:
            row.content = content
            row.generated_at = datetime.now(UTC)
        else:
            row = WordLlmCache(
                vocabulary_item_id=vocabulary_item_id,
                cache_type=cache_type,
                language=language,
                content=content,
                generated_at=datetime.now(UTC),
            )
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _llm_cache_to_record(row)

    def delete_llm_cache_for_language(self, language: str) -> int:
        result = self._db.execute(delete(WordLlmCache).where(WordLlmCache.language == language))
        self._db.commit()
        return result.rowcount

    # --- Spaced repetition ---

    def get_srs_schedule(self, vocabulary_item_id: int) -> SrsScheduleRecord | None:
        row = (
            self._db.query(SpacedRepetitionSchedule)
            .filter(SpacedRepetitionSchedule.vocabulary_item_id == vocabulary_item_id)
            .first()
        )
        return _srs_to_record(row) if row else None

    def upsert_srs_schedule(
        self,
        vocabulary_item_id: int,
        interval_stage: int,
        next_due_at: datetime | None,
    ) -> SrsScheduleRecord:
        row = (
            self._db.query(SpacedRepetitionSchedule)
            .filter(SpacedRepetitionSchedule.vocabulary_item_id == vocabulary_item_id)
            .first()
        )
        now = datetime.now(UTC)
        if row:
            row.interval_stage = interval_stage
            row.last_practiced_at = now
            row.next_due_at = next_due_at
        else:
            row = SpacedRepetitionSchedule(
                vocabulary_item_id=vocabulary_item_id,
                interval_stage=interval_stage,
                last_practiced_at=now,
                next_due_at=next_due_at,
            )
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _srs_to_record(row)

    # --- Analytics ---

    def get_sessions_since(self, cutoff: datetime | None) -> list[SessionRecord]:
        query = self._db.query(PracticeSession)
        if cutoff:
            query = query.filter(PracticeSession.started_at >= cutoff)
        rows = query.order_by(PracticeSession.started_at.asc()).all()
        return [_session_to_record(r) for r in rows]

    def get_card_results_since(self, cutoff: datetime | None) -> list[CardResultRecord]:
        query = self._db.query(CardResult)
        if cutoff:
            query = query.join(
                PracticeSession,
                CardResult.session_id == PracticeSession.id,
            ).filter(PracticeSession.started_at >= cutoff)
        rows = query.order_by(CardResult.rated_at.asc()).all()
        return [_card_result_to_record(r) for r in rows]

    def get_classification_counts(self) -> dict[str, int]:
        rows = (
            self._db.query(VocabularyItem.classification, func.count(VocabularyItem.id))
            .group_by(VocabularyItem.classification)
            .all()
        )
        return {classification: count for classification, count in rows}

    def create_classification_snapshot(
        self,
        session_id: int,
        not_practiced: int,
        difficult: int,
        almost_learned: int,
        learned: int,
    ) -> ClassificationSnapshotRecord:
        row = SessionClassificationSnapshot(
            session_id=session_id,
            snapshotted_at=datetime.now(UTC),
            not_practiced_count=not_practiced,
            difficult_count=difficult,
            almost_learned_count=almost_learned,
            learned_count=learned,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _snapshot_to_record(row)

    def get_classification_snapshots_since(
        self, cutoff: datetime | None
    ) -> list[ClassificationSnapshotRecord]:
        query = self._db.query(SessionClassificationSnapshot)
        if cutoff:
            query = query.filter(SessionClassificationSnapshot.snapshotted_at >= cutoff)
        rows = query.order_by(SessionClassificationSnapshot.snapshotted_at.asc()).all()
        return [_snapshot_to_record(r) for r in rows]
