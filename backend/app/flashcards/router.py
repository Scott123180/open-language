"""FastAPI router for the flashcards domain.

Prefix: /flashcards (mounted at /api in main.py → full path: /api/flashcards/*)
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.flashcards.schemas import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    CardResultRequest,
    CardResultResponse,
    ClassificationUpdateRequest,
    DeckCardItem,
    DeckConfigRequest,
    DeckDetail,
    DeckNameUpdateRequest,
    DeckSummary,
    EncouragementResponse,
    GenerationAlgorithmEnum,
    LlmCacheResponse,
    LlmCacheTypeEnum,
    PracticeModeEnum,
    SessionEndRequest,
    SessionStarted,
    SessionStartRequest,
    SessionSummary,
    WordClassificationEnum,
    WordListItem,
)
from app.flashcards.services.storage import FlashcardStorageProvider
from app.flashcards.services.llm_cache import LlmCacheService
from app.services.factory import get_flashcard_storage, get_llm, get_tts
from app.services.llm.base import LLMProvider
from app.services.tts.base import TTSProvider

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _storage(
    storage: FlashcardStorageProvider = Depends(get_flashcard_storage),
) -> FlashcardStorageProvider:
    return storage


# ---------------------------------------------------------------------------
# Word library
# ---------------------------------------------------------------------------


@router.get("/words", response_model=list[WordListItem])
def get_words(
    classification: Annotated[list[str] | None, Query()] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> list[WordListItem]:
    records = storage.list_words(
        classifications=classification or None,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return [
        WordListItem(
            id=r.id,
            word=r.word,
            translation=r.translation,
            target_language=r.target_language,
            native_language=r.native_language,
            classification=WordClassificationEnum(r.classification),
            manual_override=r.manual_override,
            saved_at=r.saved_at,
            source_conversation_id=r.source_conversation_id,
        )
        for r in records
    ]


@router.patch("/words/{vocabulary_item_id}/classification", response_model=WordListItem)
def patch_word_classification(
    vocabulary_item_id: int,
    body: ClassificationUpdateRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> WordListItem:
    word = storage.get_word(vocabulary_item_id)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found.")
    updated = storage.update_word_classification(
        vocabulary_item_id, body.classification.value, manual_override=True
    )
    return WordListItem(
        id=updated.id,
        word=updated.word,
        translation=updated.translation,
        target_language=updated.target_language,
        native_language=updated.native_language,
        classification=WordClassificationEnum(updated.classification),
        manual_override=updated.manual_override,
        saved_at=updated.saved_at,
        source_conversation_id=updated.source_conversation_id,
    )


@router.delete("/words", response_model=BulkDeleteResponse)
def bulk_delete_words(
    body: BulkDeleteRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> BulkDeleteResponse:
    deleted = storage.delete_words(body.ids)
    return BulkDeleteResponse(deleted=deleted)


@router.delete("/words/{vocabulary_item_id}", status_code=204)
def delete_word(
    vocabulary_item_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> None:
    word = storage.get_word(vocabulary_item_id)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found.")
    storage.delete_word(vocabulary_item_id)


@router.get("/words/{vocabulary_item_id}/info/{cache_type}", response_model=LlmCacheResponse)
def get_word_info(
    vocabulary_item_id: int,
    cache_type: LlmCacheTypeEnum,
    storage: FlashcardStorageProvider = Depends(_storage),
    llm: LLMProvider = Depends(get_llm),
) -> LlmCacheResponse:
    from datetime import UTC
    from datetime import datetime as _dt

    word = storage.get_word(vocabulary_item_id)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found.")

    llm_cache = LlmCacheService(storage=storage, llm_client=llm)
    content = llm_cache.get_or_generate(
        vocabulary_item_id=vocabulary_item_id,
        cache_type=cache_type.value,
        word=word.word,
        language=word.target_language,
    )
    if content is None:
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable. Please try again shortly.",
        )
    cached = storage.get_llm_cache(vocabulary_item_id, cache_type.value, word.target_language)
    return LlmCacheResponse(
        vocabulary_item_id=vocabulary_item_id,
        cache_type=cache_type,
        content=content,
        from_cache=cached is not None,
        generated_at=cached.generated_at if cached else _dt.now(UTC),
    )


@router.get("/tts/{vocabulary_item_id}")
def get_vocab_tts(
    vocabulary_item_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
    tts: TTSProvider = Depends(get_tts),
):
    """Return TTS audio for a vocabulary word. Generates and caches WAV on first request."""
    from pathlib import Path

    word = storage.get_word(vocabulary_item_id)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found.")

    if word.tts_cache_path:
        cached = Path(word.tts_cache_path)
        if cached.exists():
            return FileResponse(str(cached), media_type="audio/wav")

    cache_dir = Path.home() / ".open-language" / "tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = cache_dir / f"vocab_{vocabulary_item_id}.wav"

    tts.synthesize(word.word, audio_path)
    storage.update_word_tts_path(vocabulary_item_id, str(audio_path))

    return FileResponse(str(audio_path), media_type="audio/wav")


# ---------------------------------------------------------------------------
# Deck management
# ---------------------------------------------------------------------------


def _build_deck_detail(
    deck_record, card_records, word_lookup: dict, translation_lookup: dict | None = None
) -> DeckDetail:
    cards = [
        DeckCardItem(
            position=c.position,
            vocabulary_item_id=c.vocabulary_item_id,
            word=word_lookup.get(c.vocabulary_item_id),
            translation=(
                translation_lookup.get(c.vocabulary_item_id) if translation_lookup else None
            ),
            fill_blank_sentence=c.fill_blank_sentence,
        )
        for c in card_records
    ]
    return DeckDetail(
        id=deck_record.id,
        name=deck_record.name,
        practice_mode=PracticeModeEnum(deck_record.practice_mode),
        algorithm=GenerationAlgorithmEnum(deck_record.algorithm),
        requested_size=deck_record.requested_size,
        actual_size=len(cards),
        size_adjusted=len(cards) != deck_record.requested_size,
        created_at=deck_record.created_at,
        cards=cards,
    )


@router.post("/decks", response_model=DeckDetail, status_code=201)
def create_deck(
    body: DeckConfigRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> DeckDetail:
    from app.flashcards.services.deck_generation import DeckGenerationService

    # Resolve word pool
    if body.word_source == "selected":
        words = [storage.get_word(wid) for wid in body.selected_word_ids]
        words = [w for w in words if w is not None]
    elif body.word_source == "filtered":
        words = storage.list_words(
            classifications=(
                [c.value for c in body.filter_classifications]
                if body.filter_classifications
                else None
            ),
            date_from=body.filter_date_from,
            date_to=body.filter_date_to,
            search=body.filter_search,
        )
    else:
        words = storage.list_words()

    from datetime import UTC

    # T063: exclude Learned words whose SRS schedule is not yet due
    now = datetime.now(UTC)
    eligible_words = _filter_srs_eligible(words, storage, now)

    service = DeckGenerationService()
    selected = service.select_words(eligible_words, body.size, body.algorithm.value)

    name = body.name or f"Deck \u2014 {now.strftime('%b %d, %Y')}"

    cards_data = _build_cards_data(selected, body.practice_mode.value, storage)
    deck_record, card_records = storage.create_deck(
        name=name,
        practice_mode=body.practice_mode.value,
        algorithm=body.algorithm.value,
        requested_size=body.size,
        cards=cards_data,
    )

    word_lookup = {w.id: w.word for w in selected}
    translation_lookup = {w.id: w.translation for w in selected}
    return _build_deck_detail(deck_record, card_records, word_lookup, translation_lookup)


def _filter_srs_eligible(words: list, storage: FlashcardStorageProvider, now: datetime) -> list:
    """Remove Learned words that have an SRS schedule with next_due_at in the future."""

    eligible = []
    for w in words:
        if w.classification == "learned":
            schedule = storage.get_srs_schedule(w.id)
            if schedule and schedule.next_due_at:
                due = schedule.next_due_at
                # Normalize to aware for comparison
                if due.tzinfo is None:
                    due = due.replace(tzinfo=UTC)
                if due > now:
                    continue  # Not yet due — skip
        eligible.append(w)
    return eligible


def _build_cards_data(
    selected: list,
    practice_mode: str,
    storage: FlashcardStorageProvider,
) -> list[dict]:
    from app.flashcards.services.llm_cache import LlmCacheService

    if practice_mode != "fill_blank":
        return [{"vocabulary_item_id": w.id, "position": i} for i, w in enumerate(selected)]

    llm_cache = LlmCacheService(storage=storage)
    cards = []
    for i, w in enumerate(selected):
        sentence = llm_cache.get_fill_blank_sentence(
            vocabulary_item_id=w.id,
            word=w.word,
            language=w.target_language,
        )
        cards.append(
            {
                "vocabulary_item_id": w.id,
                "position": i,
                "fill_blank_sentence": sentence,
            }
        )
    return cards


@router.get("/decks", response_model=list[DeckSummary])
def list_decks(
    storage: FlashcardStorageProvider = Depends(_storage),
) -> list[DeckSummary]:
    decks = storage.list_decks()
    result = []
    for d in decks:
        cards = storage.get_deck_cards(d.id)
        result.append(
            DeckSummary(
                id=d.id,
                name=d.name,
                practice_mode=PracticeModeEnum(d.practice_mode),
                algorithm=GenerationAlgorithmEnum(d.algorithm),
                card_count=len(cards),
                created_at=d.created_at,
                last_practiced_at=d.last_practiced_at,
            )
        )
    return result


@router.get("/decks/{deck_id}", response_model=DeckDetail)
def get_deck(
    deck_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> DeckDetail:
    deck = storage.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    cards = storage.get_deck_cards(deck_id)
    word_lookup = {}
    translation_lookup = {}
    for c in cards:
        if c.vocabulary_item_id:
            w = storage.get_word(c.vocabulary_item_id)
            if w:
                word_lookup[c.vocabulary_item_id] = w.word
                translation_lookup[c.vocabulary_item_id] = w.translation
    return _build_deck_detail(deck, cards, word_lookup, translation_lookup)


@router.patch("/decks/{deck_id}", response_model=DeckSummary)
def update_deck_name(
    deck_id: int,
    body: DeckNameUpdateRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> DeckSummary:
    deck = storage.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    updated = storage.update_deck_name(deck_id, body.name)
    cards = storage.get_deck_cards(deck_id)
    return DeckSummary(
        id=updated.id,
        name=updated.name,
        practice_mode=PracticeModeEnum(updated.practice_mode),
        algorithm=GenerationAlgorithmEnum(updated.algorithm),
        card_count=len(cards),
        created_at=updated.created_at,
        last_practiced_at=updated.last_practiced_at,
    )


@router.post("/decks/{deck_id}/refresh", response_model=DeckDetail)
def refresh_deck(
    deck_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> DeckDetail:
    from app.flashcards.services.deck_generation import DeckGenerationService

    deck = storage.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")

    existing_cards = storage.get_deck_cards(deck_id)
    learned_ids = set()
    for c in existing_cards:
        if c.vocabulary_item_id:
            w = storage.get_word(c.vocabulary_item_id)
            if w and w.classification == "learned":
                learned_ids.add(c.vocabulary_item_id)

    all_words = storage.list_words()
    eligible = [
        w
        for w in all_words
        if w.id not in {c.vocabulary_item_id for c in existing_cards} or w.id in learned_ids
    ]

    service = DeckGenerationService()
    selected = service.select_words(eligible, deck.requested_size, deck.algorithm)

    cards_data = [{"vocabulary_item_id": w.id, "position": i} for i, w in enumerate(selected)]
    new_cards = storage.replace_deck_cards(deck_id, cards_data)
    word_lookup = {w.id: w.word for w in selected}
    return _build_deck_detail(deck, new_cards, word_lookup)


@router.delete("/decks/{deck_id}", status_code=204)
def delete_deck(
    deck_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> None:
    deck = storage.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    storage.delete_deck(deck_id)


# ---------------------------------------------------------------------------
# Practice sessions
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=SessionStarted, status_code=201)
def start_session(
    body: SessionStartRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> SessionStarted:
    deck = storage.get_deck(body.deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    cards = storage.get_deck_cards(body.deck_id)
    session = storage.create_session(
        deck_id=body.deck_id,
        practice_mode=deck.practice_mode,
        algorithm=deck.algorithm,
        total_cards=len(cards),
    )
    return SessionStarted(
        id=session.id,
        deck_id=session.deck_id,
        practice_mode=PracticeModeEnum(session.practice_mode),
        total_cards=session.total_cards,
        started_at=session.started_at,
    )


@router.post("/sessions/{session_id}/cards/{position}", response_model=CardResultResponse)
def record_card_result(
    session_id: int,
    position: int,
    body: CardResultRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> CardResultResponse:
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Resolve vocabulary_item_id from deck card at this position
    if session.deck_id:
        cards = storage.get_deck_cards(session.deck_id)
        card = next((c for c in cards if c.position == position), None)
        vocab_id = card.vocabulary_item_id if card else None
    else:
        vocab_id = None

    storage.add_card_result(
        session_id=session_id,
        vocabulary_item_id=vocab_id,
        rating=body.rating.value,
        response_type=body.response_type,
        user_response=body.user_response,
    )
    if vocab_id:
        storage.add_rating_history(
            vocabulary_item_id=vocab_id,
            rating=body.rating.value,
            session_id=session_id,
        )

    updated_session = storage.get_session(session_id)
    return CardResultResponse(cards_reviewed=updated_session.cards_reviewed)


@router.post("/sessions/{session_id}/end", response_model=SessionSummary)
def end_session(
    session_id: int,
    body: SessionEndRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> SessionSummary:
    from app.flashcards.services.session import SessionService

    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    service = SessionService(storage)
    summary = service.end_session(session_id, body.completed)
    return summary


@router.get("/sessions/{session_id}/summary", response_model=SessionSummary)
def get_session_summary(
    session_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> SessionSummary:
    from app.flashcards.services.session import SessionService

    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    service = SessionService(storage)
    return service.build_summary(session_id)


@router.get("/sessions/{session_id}/encouragement", response_model=EncouragementResponse)
def get_encouragement(
    session_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> EncouragementResponse:
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    # LLM integration implemented in T076 — return default message for now
    accuracy = session.knew_it_count / max(session.cards_reviewed, 1)
    if accuracy >= 0.8:
        msg = "Excellent work! You're making great progress."
    elif accuracy >= 0.5:
        msg = "Good effort! Keep practicing and you'll get there."
    else:
        msg = "Don't give up! Every session helps you improve."
    return EncouragementResponse(message=msg)


@router.post("/sessions/{session_id}/missed-deck", response_model=DeckDetail, status_code=201)
def create_missed_deck(
    session_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> DeckDetail:
    session = storage.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    results = storage.get_card_results_for_session(session_id)
    didnt_know_ids = [
        r.vocabulary_item_id
        for r in results
        if r.rating == "didnt_know" and r.vocabulary_item_id is not None
    ]

    if not didnt_know_ids:
        raise HTTPException(
            status_code=400,
            detail="No 'Didn't Know' words in this session to create a missed deck.",
        )

    from datetime import UTC

    now = datetime.now(UTC)
    cards_data = [
        {"vocabulary_item_id": vid, "position": i} for i, vid in enumerate(didnt_know_ids)
    ]
    deck_record, card_records = storage.create_deck(
        name=f"Missed Words \u2014 {now.strftime('%b %d, %Y')}",
        practice_mode=session.practice_mode,
        algorithm="not_practiced",
        requested_size=len(didnt_know_ids),
        cards=cards_data,
    )

    word_lookup = {}
    for vid in didnt_know_ids:
        w = storage.get_word(vid)
        if w:
            word_lookup[vid] = w.word
    return _build_deck_detail(deck_record, card_records, word_lookup)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics")
def get_analytics(
    range: str = "7d",
    storage: FlashcardStorageProvider = Depends(_storage),
):
    from app.flashcards.services.analytics import AnalyticsService

    service = AnalyticsService(storage)
    return service.build_summary(range)
