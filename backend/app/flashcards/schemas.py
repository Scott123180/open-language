"""Pydantic request/response schemas for the flashcards domain."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WordClassificationEnum(str, Enum):
    NOT_PRACTICED = "not_practiced"
    DIFFICULT = "difficult"
    ALMOST_LEARNED = "almost_learned"
    LEARNED = "learned"


class PracticeModeEnum(str, Enum):
    RECALL = "recall"
    LISTEN = "listen"
    PRODUCE = "produce"
    FILL_BLANK = "fill_blank"


class GenerationAlgorithmEnum(str, Enum):
    NOT_PRACTICED = "not_practiced"
    DIFFICULT = "difficult"
    PREVIOUSLY_GUESSED = "previously_guessed"
    MIXED_REVIEW = "mixed_review"


class RatingEnum(str, Enum):
    KNEW_IT = "knew_it"
    GUESSED = "guessed"
    DIDNT_KNOW = "didnt_know"


class LlmCacheTypeEnum(str, Enum):
    MEANINGS = "meanings"
    USAGE = "usage"
    PHRASES = "phrases"
    SIMILAR = "similar"
    FILL_BLANK = "fill_blank"


# ---------------------------------------------------------------------------
# Word library
# ---------------------------------------------------------------------------


class WordListItem(BaseModel):
    id: int
    word: str
    translation: str
    target_language: str
    native_language: str
    classification: WordClassificationEnum
    manual_override: bool
    saved_at: datetime
    source_conversation_id: int | None = None

    model_config = {"from_attributes": True}


class ClassificationUpdateRequest(BaseModel):
    classification: WordClassificationEnum


class BulkDeleteRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class BulkDeleteResponse(BaseModel):
    deleted: int


# ---------------------------------------------------------------------------
# Decks
# ---------------------------------------------------------------------------


class DeckCardItem(BaseModel):
    position: int
    vocabulary_item_id: int | None
    word: str | None = None
    translation: str | None = None
    fill_blank_sentence: str | None = None


class DeckConfigRequest(BaseModel):
    name: str | None = None
    size: int = Field(default=20, ge=1, le=500)
    word_source: str = "all"  # "all" | "filtered" | "selected"
    selected_word_ids: list[int] = Field(default_factory=list)
    practice_mode: PracticeModeEnum = PracticeModeEnum.RECALL
    algorithm: GenerationAlgorithmEnum = GenerationAlgorithmEnum.MIXED_REVIEW
    # Optional filters applied when word_source == "filtered"
    filter_classifications: list[WordClassificationEnum] | None = None
    filter_date_from: datetime | None = None
    filter_date_to: datetime | None = None
    filter_search: str | None = None


class DeckDetail(BaseModel):
    id: int
    name: str
    practice_mode: PracticeModeEnum
    algorithm: GenerationAlgorithmEnum
    requested_size: int
    actual_size: int
    size_adjusted: bool
    created_at: datetime
    cards: list[DeckCardItem]


class DeckSummary(BaseModel):
    id: int
    name: str
    practice_mode: PracticeModeEnum
    algorithm: GenerationAlgorithmEnum
    card_count: int
    created_at: datetime
    last_practiced_at: datetime | None = None
    session_count: int = 0
    last_accuracy: float | None = None


class DeckNameUpdateRequest(BaseModel):
    name: str


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SessionStartRequest(BaseModel):
    deck_id: int


class SessionStarted(BaseModel):
    id: int
    deck_id: int | None
    practice_mode: PracticeModeEnum
    total_cards: int
    started_at: datetime


class CardResultRequest(BaseModel):
    rating: RatingEnum
    response_type: str | None = None  # "spoken" | "typed" | None
    user_response: str | None = None


class CardResultResponse(BaseModel):
    cards_reviewed: int


class SessionEndRequest(BaseModel):
    completed: bool


class WordNeedingWork(BaseModel):
    id: int
    word: str
    translation: str
    rating: RatingEnum


class SessionSummary(BaseModel):
    session_id: int
    completed: bool
    cards_reviewed: int
    total_cards: int
    knew_it_count: int
    guessed_count: int
    didnt_know_count: int
    duration_seconds: int | None
    current_streak: int
    words_needing_work: list[WordNeedingWork] = Field(default_factory=list)


class EncouragementResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# LLM cache
# ---------------------------------------------------------------------------


class LlmCacheResponse(BaseModel):
    vocabulary_item_id: int
    cache_type: LlmCacheTypeEnum
    content: str
    from_cache: bool
    generated_at: datetime


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class AtAGlanceStats(BaseModel):
    total_words: int
    words_learned: int
    current_streak: int
    sessions_this_week: int


class AccuracyPoint(BaseModel):
    session_id: int
    date: str
    accuracy: float


class DailyActivityPoint(BaseModel):
    date: str
    cards_reviewed: int


class ClassificationOverTimePoint(BaseModel):
    date: str
    not_practiced: int
    difficult: int
    almost_learned: int
    learned: int


class ClassificationNow(BaseModel):
    not_practiced: int
    difficult: int
    almost_learned: int
    learned: int


class HardestWord(BaseModel):
    id: int
    word: str
    encounters: int
    success_rate: float


class RecentlyLearnedWord(BaseModel):
    id: int
    word: str
    learned_at: datetime


class ModePerformanceItem(BaseModel):
    mode: str
    accuracy: float


class AnalyticsSummary(BaseModel):
    at_a_glance: AtAGlanceStats
    accuracy_trend: list[AccuracyPoint]
    daily_activity: list[DailyActivityPoint]
    classification_over_time: list[ClassificationOverTimePoint]
    classification_now: ClassificationNow
    hardest_words: list[HardestWord]
    recently_learned: list[RecentlyLearnedWord]
    mode_performance: list[ModePerformanceItem]
