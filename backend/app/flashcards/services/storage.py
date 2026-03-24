"""FlashcardStorageProvider ABC.

Separate from the existing StorageProvider to comply with ISP:
non-flashcard consumers are not forced to depend on flashcard storage methods.
SQLiteStorageProvider implements both ABCs via Python multiple inheritance.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

# ---------------------------------------------------------------------------
# Data records (frozen dataclasses — no business logic, transport only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WordRecord:
    id: int
    word: str
    translation: str
    target_language: str
    native_language: str
    source_conversation_id: int | None
    saved_at: datetime
    classification: str
    manual_override: bool
    tts_cache_path: str | None


@dataclass(frozen=True)
class DeckRecord:
    id: int
    name: str
    practice_mode: str
    algorithm: str
    requested_size: int
    created_at: datetime
    last_practiced_at: datetime | None


@dataclass(frozen=True)
class DeckCardRecord:
    id: int
    deck_id: int
    vocabulary_item_id: int | None
    position: int
    fill_blank_sentence: str | None


@dataclass(frozen=True)
class SessionRecord:
    id: int
    deck_id: int | None
    practice_mode: str
    algorithm: str
    started_at: datetime
    ended_at: datetime | None
    total_cards: int
    cards_reviewed: int
    knew_it_count: int
    guessed_count: int
    didnt_know_count: int
    completed: bool


@dataclass(frozen=True)
class CardResultRecord:
    id: int
    session_id: int
    vocabulary_item_id: int | None
    rating: str
    response_type: str | None
    user_response: str | None
    rated_at: datetime


@dataclass(frozen=True)
class RatingHistoryRecord:
    id: int
    vocabulary_item_id: int
    rating: str
    rated_at: datetime
    session_id: int


@dataclass(frozen=True)
class LlmCacheRecord:
    id: int
    vocabulary_item_id: int
    cache_type: str
    language: str
    content: str
    generated_at: datetime


@dataclass(frozen=True)
class SrsScheduleRecord:
    id: int
    vocabulary_item_id: int
    interval_stage: int
    last_practiced_at: datetime | None
    next_due_at: datetime | None


@dataclass(frozen=True)
class ClassificationSnapshotRecord:
    id: int
    session_id: int
    snapshotted_at: datetime
    not_practiced_count: int
    difficult_count: int
    almost_learned_count: int
    learned_count: int


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class FlashcardStorageProvider(ABC):
    """Storage operations required by the flashcards domain."""

    # --- Word library ---

    @abstractmethod
    def list_words(
        self,
        classifications: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> list[WordRecord]:
        """Return vocabulary words, optionally filtered."""
        ...

    @abstractmethod
    def get_word(self, vocabulary_item_id: int) -> WordRecord | None:
        """Return a single word by id, or None if not found."""
        ...

    @abstractmethod
    def update_word_classification(
        self, vocabulary_item_id: int, classification: str, manual_override: bool
    ) -> WordRecord:
        """Update classification and manual_override flag on a word."""
        ...

    @abstractmethod
    def delete_word(self, vocabulary_item_id: int) -> None:
        """Delete a word from the library."""
        ...

    @abstractmethod
    def update_word_tts_path(self, vocabulary_item_id: int, tts_path: str) -> WordRecord:
        """Persist TTS cache path for a vocabulary word."""
        ...

    # --- Deck management ---

    @abstractmethod
    def create_deck(
        self,
        name: str,
        practice_mode: str,
        algorithm: str,
        requested_size: int,
        cards: list[dict],
    ) -> tuple[DeckRecord, list[DeckCardRecord]]:
        """Persist a new deck and its cards; return (deck, cards)."""
        ...

    @abstractmethod
    def list_decks(self) -> list[DeckRecord]:
        """Return all decks, most recently created first."""
        ...

    @abstractmethod
    def get_deck(self, deck_id: int) -> DeckRecord | None:
        """Return a deck by id, or None."""
        ...

    @abstractmethod
    def get_deck_cards(self, deck_id: int) -> list[DeckCardRecord]:
        """Return all cards for a deck ordered by position."""
        ...

    @abstractmethod
    def update_deck_name(self, deck_id: int, name: str) -> DeckRecord:
        """Update the deck name."""
        ...

    @abstractmethod
    def delete_deck(self, deck_id: int) -> None:
        """Delete a deck (cards cascade; sessions retained as orphaned)."""
        ...

    @abstractmethod
    def replace_deck_cards(self, deck_id: int, cards: list[dict]) -> list[DeckCardRecord]:
        """Delete all existing deck cards and insert the new set."""
        ...

    # --- Practice sessions ---

    @abstractmethod
    def create_session(
        self,
        deck_id: int,
        practice_mode: str,
        algorithm: str,
        total_cards: int,
    ) -> SessionRecord:
        """Create and return a new incomplete practice session."""
        ...

    @abstractmethod
    def get_session(self, session_id: int) -> SessionRecord | None:
        """Return a session by id, or None."""
        ...

    @abstractmethod
    def add_card_result(
        self,
        session_id: int,
        vocabulary_item_id: int | None,
        rating: str,
        response_type: str | None,
        user_response: str | None,
    ) -> CardResultRecord:
        """Persist a single card result and update session counters."""
        ...

    @abstractmethod
    def end_session(self, session_id: int, completed: bool) -> SessionRecord:
        """Set ended_at and completed flag; return updated session."""
        ...

    @abstractmethod
    def get_card_results_for_session(self, session_id: int) -> list[CardResultRecord]:
        """Return all card results for a session ordered by rated_at."""
        ...

    # --- Rating history ---

    @abstractmethod
    def add_rating_history(
        self,
        vocabulary_item_id: int,
        rating: str,
        session_id: int,
    ) -> RatingHistoryRecord:
        """Append a rating history entry; prune to keep only last 5 per word."""
        ...

    @abstractmethod
    def get_recent_ratings(
        self, vocabulary_item_id: int, limit: int = 5
    ) -> list[RatingHistoryRecord]:
        """Return the most recent ratings for a word, newest first."""
        ...

    # --- LLM cache ---

    @abstractmethod
    def get_llm_cache(
        self, vocabulary_item_id: int, cache_type: str, language: str
    ) -> LlmCacheRecord | None:
        """Return cached LLM content, or None on cache miss."""
        ...

    @abstractmethod
    def set_llm_cache(
        self,
        vocabulary_item_id: int,
        cache_type: str,
        language: str,
        content: str,
    ) -> LlmCacheRecord:
        """Persist LLM content (upsert by word + type + language)."""
        ...

    @abstractmethod
    def delete_llm_cache_for_language(self, language: str) -> int:
        """Delete all cache entries for a given language; return deleted count."""
        ...

    # --- Spaced repetition ---

    @abstractmethod
    def get_srs_schedule(self, vocabulary_item_id: int) -> SrsScheduleRecord | None:
        """Return SRS schedule for a word, or None if not yet scheduled."""
        ...

    @abstractmethod
    def upsert_srs_schedule(
        self,
        vocabulary_item_id: int,
        interval_stage: int,
        next_due_at: datetime | None,
    ) -> SrsScheduleRecord:
        """Create or update the SRS schedule for a word."""
        ...

    # --- Analytics ---

    @abstractmethod
    def get_sessions_since(self, cutoff: datetime | None) -> list[SessionRecord]:
        """Return sessions started on or after cutoff (None = all time)."""
        ...

    @abstractmethod
    def get_card_results_since(self, cutoff: datetime | None) -> list[CardResultRecord]:
        """Return card results from sessions started since cutoff."""
        ...

    @abstractmethod
    def get_classification_counts(self) -> dict[str, int]:
        """Return current count of words per classification."""
        ...

    @abstractmethod
    def create_classification_snapshot(
        self,
        session_id: int,
        not_practiced: int,
        difficult: int,
        almost_learned: int,
        learned: int,
    ) -> ClassificationSnapshotRecord:
        """Persist classification distribution snapshot at session end."""
        ...

    @abstractmethod
    def get_classification_snapshots_since(
        self, cutoff: datetime | None
    ) -> list[ClassificationSnapshotRecord]:
        """Return classification snapshots since cutoff (None = all time)."""
        ...
