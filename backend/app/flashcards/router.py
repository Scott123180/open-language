"""FastAPI router for the flashcards domain.

Prefix: /flashcards (mounted at /api in main.py → full path: /api/flashcards/*)
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.flashcards.schemas import (
    PRACTICE_LANGUAGE_PATTERN,
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
from app.flashcards.services.llm_cache import LlmCacheService
from app.flashcards.services.storage import DeckRecord, FlashcardStorageProvider, WordRecord
from app.services.factory import get_flashcard_storage, get_llm, get_speech_for_language
from app.services.llm.base import LLMProvider
from app.services.tts.selection import SpeechForLanguage

router = APIRouter(prefix="/flashcards", tags=["flashcards"])

WORD_NOT_FOUND = "Word not found."
OTHER_LANGUAGE_WORDS = "Some selected words are in another language. Reload the word list."

# Required on every collection: the Flashcards screens show one language at a time (FR-020).
LanguageQuery = Annotated[str, Query(pattern=PRACTICE_LANGUAGE_PATTERN)]


def _storage(
    storage: FlashcardStorageProvider = Depends(get_flashcard_storage),
) -> FlashcardStorageProvider:
    return storage


# ---------------------------------------------------------------------------
# Word library
# ---------------------------------------------------------------------------


@router.get("/words", response_model=list[WordListItem])
def get_words(
    language: LanguageQuery,
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
        language=language,
    )
    return [_word_list_item(r) for r in records]


def _word_list_item(r: WordRecord) -> WordListItem:
    return WordListItem(
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
    return _word_list_item(updated)


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
    word = _require_word(storage, vocabulary_item_id)
    # Read the cache before generating: get_or_generate writes on a miss, so a
    # lookup afterwards would report every response as cached.
    cached = storage.get_llm_cache(vocabulary_item_id, cache_type.value, word.target_language)
    content = _word_info_content(LlmCacheService(storage=storage, llm_client=llm), word, cache_type)
    return LlmCacheResponse(
        vocabulary_item_id=vocabulary_item_id,
        cache_type=cache_type,
        content=content,
        from_cache=cached is not None,
        generated_at=cached.generated_at if cached else _generated_now(storage, word, cache_type),
    )


def _require_word(storage: FlashcardStorageProvider, vocabulary_item_id: int):
    word = storage.get_word(vocabulary_item_id)
    if word is None:
        raise HTTPException(status_code=404, detail=WORD_NOT_FOUND)
    return word


def _generated_now(storage: FlashcardStorageProvider, word, cache_type: LlmCacheTypeEnum):
    """When the entry just written was generated; now, if it wasn't stored."""
    stored = storage.get_llm_cache(word.id, cache_type.value, word.target_language)
    return stored.generated_at if stored else datetime.now(UTC)


def _word_info_content(llm_cache: LlmCacheService, word, cache_type: LlmCacheTypeEnum) -> str:
    """Cached or freshly generated; an LLMError reaches the shared 503 handler."""
    return llm_cache.get_or_generate(
        vocabulary_item_id=word.id,
        cache_type=cache_type.value,
        word=word.word,
        language=word.target_language,
        native_language=word.native_language,
    )


@router.get("/tts/{vocabulary_item_id}")
def get_vocab_tts(
    vocabulary_item_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
    speech: SpeechForLanguage = Depends(get_speech_for_language),
):
    """Return TTS audio for a vocabulary word, in its own language's voice (FR-014, FR-018)."""
    word = storage.get_word(vocabulary_item_id)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found.")
    audio_path = _cached_word_audio(word) or _synthesize_word(speech, storage, word)
    return FileResponse(str(audio_path), media_type="audio/wav")


def _tts_cache_dir() -> Path:
    return Path.home() / ".open-language" / "tts_cache"


def _cached_word_audio(word: WordRecord) -> Path | None:
    if word.tts_cache_path and Path(word.tts_cache_path).exists():
        return Path(word.tts_cache_path)
    return None


def _synthesize_word(
    speech: SpeechForLanguage, storage: FlashcardStorageProvider, word: WordRecord
) -> Path:
    """`VoiceUnavailable` propagates to the 503 handler; no other voice is tried."""
    provider = speech.provider_for(word.target_language)
    cache_dir = _tts_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = cache_dir / f"vocab_{word.id}.wav"
    provider.synthesize(word.word, audio_path)
    storage.update_word_tts_path(word.id, str(audio_path))
    return audio_path


# ---------------------------------------------------------------------------
# Deck management
# ---------------------------------------------------------------------------


def _build_deck_detail(
    deck_record, card_records, word_lookup: dict, translation_lookup: dict | None = None
) -> DeckDetail:
    cards = [_deck_card_item(c, word_lookup, translation_lookup or {}) for c in card_records]
    return DeckDetail(
        id=deck_record.id,
        name=deck_record.name,
        practice_mode=PracticeModeEnum(deck_record.practice_mode),
        algorithm=GenerationAlgorithmEnum(deck_record.algorithm),
        requested_size=deck_record.requested_size,
        actual_size=len(cards),
        size_adjusted=len(cards) != deck_record.requested_size,
        created_at=deck_record.created_at,
        target_language=deck_record.target_language,
        cards=cards,
    )


def _deck_card_item(card, word_lookup: dict, translation_lookup: dict) -> DeckCardItem:
    return DeckCardItem(
        position=card.position,
        vocabulary_item_id=card.vocabulary_item_id,
        word=word_lookup.get(card.vocabulary_item_id),
        translation=translation_lookup.get(card.vocabulary_item_id),
        fill_blank_sentence=card.fill_blank_sentence,
    )


@router.post("/decks", response_model=DeckDetail, status_code=201)
def create_deck(
    body: DeckConfigRequest,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> DeckDetail:
    from app.flashcards.services.deck_generation import DeckGenerationService

    now = datetime.now(UTC)
    # T063: exclude Learned words whose SRS schedule is not yet due
    eligible = _filter_srs_eligible(_deck_word_pool(body, storage), storage, now)
    selected = DeckGenerationService().select_words(eligible, body.size, body.algorithm.value)
    deck_record, card_records = storage.create_deck(
        name=_deck_name(body, now),
        practice_mode=body.practice_mode.value,
        algorithm=body.algorithm.value,
        requested_size=body.size,
        cards=_build_cards_data(selected, body.practice_mode.value, storage),
        language=body.language,
    )
    lookups = ({w.id: w.word for w in selected}, {w.id: w.translation for w in selected})
    return _build_deck_detail(deck_record, card_records, *lookups)


def _deck_word_pool(body: DeckConfigRequest, storage: FlashcardStorageProvider) -> list:
    """The words a new deck may draw from, all in the deck's language."""
    if body.word_source == "selected":
        words = [storage.get_word(wid) for wid in body.selected_word_ids]
        return _require_same_language([w for w in words if w is not None], body.language)
    if body.word_source != "filtered":
        return storage.list_words(language=body.language)
    return storage.list_words(
        classifications=[c.value for c in body.filter_classifications or []] or None,
        date_from=body.filter_date_from,
        date_to=body.filter_date_to,
        search=body.filter_search,
        language=body.language,
    )


def _require_same_language(words: list, language: str) -> list:
    if any(w.target_language != language for w in words):
        raise HTTPException(status_code=422, detail=OTHER_LANGUAGE_WORDS)
    return words


def _deck_name(body: DeckConfigRequest, now: datetime) -> str:
    return body.name or f"Deck \u2014 {now.strftime('%b %d, %Y')}"


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
            native_language=w.native_language,
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
    language: LanguageQuery,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> list[DeckSummary]:
    return [_deck_summary(d, storage) for d in storage.list_decks(language=language)]


def _deck_summary(deck: DeckRecord, storage: FlashcardStorageProvider) -> DeckSummary:
    return DeckSummary(
        id=deck.id,
        name=deck.name,
        practice_mode=PracticeModeEnum(deck.practice_mode),
        algorithm=GenerationAlgorithmEnum(deck.algorithm),
        card_count=len(storage.get_deck_cards(deck.id)),
        created_at=deck.created_at,
        target_language=deck.target_language,
        last_practiced_at=deck.last_practiced_at,
    )


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
    return _deck_summary(storage.update_deck_name(deck_id, body.name), storage)


@router.post("/decks/{deck_id}/refresh", response_model=DeckDetail)
def refresh_deck(
    deck_id: int,
    storage: FlashcardStorageProvider = Depends(_storage),
) -> DeckDetail:
    from app.flashcards.services.deck_generation import DeckGenerationService

    deck = storage.get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    candidates = _refresh_candidates(deck, storage.get_deck_cards(deck_id), storage)
    selected = DeckGenerationService().select_words(candidates, deck.requested_size, deck.algorithm)

    cards_data = [{"vocabulary_item_id": w.id, "position": i} for i, w in enumerate(selected)]
    new_cards = storage.replace_deck_cards(deck_id, cards_data)
    word_lookup = {w.id: w.word for w in selected}
    return _build_deck_detail(deck, new_cards, word_lookup)


def _learned_card_ids(cards: list, storage: FlashcardStorageProvider) -> set[int]:
    words = (storage.get_word(c.vocabulary_item_id) for c in cards if c.vocabulary_item_id)
    return {w.id for w in words if w and w.classification == "learned"}


def _refresh_candidates(deck: DeckRecord, cards: list, storage: FlashcardStorageProvider) -> list:
    """The deck's own language's words not already in it, plus the ones it has learned."""
    in_deck = {c.vocabulary_item_id for c in cards}
    learned = _learned_card_ids(cards, storage)
    words = storage.list_words(language=deck.target_language)
    return [w for w in words if w.id not in in_deck or w.id in learned]


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
    missed_ids = _missed_word_ids(storage.get_card_results_for_session(session_id))
    if not missed_ids:
        raise HTTPException(
            status_code=400,
            detail="No 'Didn't Know' words in this session to create a missed deck.",
        )
    deck_record, card_records = _create_missed_deck(storage, session, missed_ids)
    word_lookup = {vid: w.word for vid in missed_ids if (w := storage.get_word(vid))}
    return _build_deck_detail(deck_record, card_records, word_lookup)


def _create_missed_deck(storage: FlashcardStorageProvider, session, missed_ids: list[int]):
    """A deck of the session's missed words, in the session's own language."""
    return storage.create_deck(
        name=f"Missed Words \u2014 {datetime.now(UTC).strftime('%b %d, %Y')}",
        practice_mode=session.practice_mode,
        algorithm="not_practiced",
        requested_size=len(missed_ids),
        cards=_missed_deck_cards(missed_ids),
        language=session.target_language,
    )


def _missed_word_ids(results: list) -> list[int]:
    return [
        r.vocabulary_item_id
        for r in results
        if r.rating == "didnt_know" and r.vocabulary_item_id is not None
    ]


def _missed_deck_cards(missed_ids: list[int]) -> list[dict]:
    return [{"vocabulary_item_id": vid, "position": i} for i, vid in enumerate(missed_ids)]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics")
def get_analytics(
    language: LanguageQuery,
    range: str = "7d",
    storage: FlashcardStorageProvider = Depends(_storage),
):
    from app.flashcards.services.analytics import AnalyticsService

    return AnalyticsService(storage, language).build_summary(range)
