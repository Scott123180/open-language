"""Contract tests for FlashcardStorageProvider ABC.

Each test verifies that the abstract interface declares the required method
signatures. Tests import the ABC directly — they FAIL until T005 creates it
and T009 makes SQLiteFlashcardStorageProvider concrete.
"""

import inspect

import pytest

from app.flashcards.services.storage import FlashcardStorageProvider


def _abstract_method_names(cls) -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if getattr(getattr(cls, name), "__isabstractmethod__", False)
    }


REQUIRED_WORD_METHODS = {
    "list_words",
    "get_word",
    "update_word_classification",
    "delete_word",
    "delete_words",
    "update_word_tts_path",
}

REQUIRED_DECK_METHODS = {
    "create_deck",
    "list_decks",
    "get_deck",
    "get_deck_cards",
    "update_deck_name",
    "delete_deck",
    "replace_deck_cards",
}

REQUIRED_SESSION_METHODS = {
    "create_session",
    "get_session",
    "add_card_result",
    "end_session",
    "get_card_results_for_session",
}

REQUIRED_HISTORY_METHODS = {
    "add_rating_history",
    "get_recent_ratings",
}

REQUIRED_LLM_CACHE_METHODS = {
    "get_llm_cache",
    "set_llm_cache",
    "delete_llm_cache_for_language",
}

REQUIRED_SRS_METHODS = {
    "get_srs_schedule",
    "upsert_srs_schedule",
}

REQUIRED_ANALYTICS_METHODS = {
    "get_sessions_since",
    "get_card_results_since",
    "get_classification_counts",
    "create_classification_snapshot",
    "get_classification_snapshots_since",
}

ALL_REQUIRED = (
    REQUIRED_WORD_METHODS
    | REQUIRED_DECK_METHODS
    | REQUIRED_SESSION_METHODS
    | REQUIRED_HISTORY_METHODS
    | REQUIRED_LLM_CACHE_METHODS
    | REQUIRED_SRS_METHODS
    | REQUIRED_ANALYTICS_METHODS
)


class TestFlashcardStorageProviderContract:
    def test_is_abstract_class(self):
        assert inspect.isabstract(FlashcardStorageProvider)

    def test_word_methods_declared(self):
        abstract_names = _abstract_method_names(FlashcardStorageProvider)
        for method in REQUIRED_WORD_METHODS:
            assert method in abstract_names, f"Missing abstract method: {method}"

    def test_deck_methods_declared(self):
        abstract_names = _abstract_method_names(FlashcardStorageProvider)
        for method in REQUIRED_DECK_METHODS:
            assert method in abstract_names, f"Missing abstract method: {method}"

    def test_session_methods_declared(self):
        abstract_names = _abstract_method_names(FlashcardStorageProvider)
        for method in REQUIRED_SESSION_METHODS:
            assert method in abstract_names, f"Missing abstract method: {method}"

    def test_history_methods_declared(self):
        abstract_names = _abstract_method_names(FlashcardStorageProvider)
        for method in REQUIRED_HISTORY_METHODS:
            assert method in abstract_names, f"Missing abstract method: {method}"

    def test_llm_cache_methods_declared(self):
        abstract_names = _abstract_method_names(FlashcardStorageProvider)
        for method in REQUIRED_LLM_CACHE_METHODS:
            assert method in abstract_names, f"Missing abstract method: {method}"

    def test_srs_methods_declared(self):
        abstract_names = _abstract_method_names(FlashcardStorageProvider)
        for method in REQUIRED_SRS_METHODS:
            assert method in abstract_names, f"Missing abstract method: {method}"

    def test_analytics_methods_declared(self):
        abstract_names = _abstract_method_names(FlashcardStorageProvider)
        for method in REQUIRED_ANALYTICS_METHODS:
            assert method in abstract_names, f"Missing abstract method: {method}"

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            FlashcardStorageProvider()


# --- 006: every listing, count and creation is scoped to one language (T078) -----------

LANGUAGE_SCOPED_METHODS = (
    "list_words",
    "list_decks",
    "create_deck",
    "get_sessions_since",
    "get_card_results_since",
    "get_classification_counts",
    "get_classification_snapshots_since",
)


def _implementations():
    from app.flashcards.services.sqlite_storage import SQLiteFlashcardStorageProvider

    return (FlashcardStorageProvider, SQLiteFlashcardStorageProvider)


@pytest.mark.parametrize("method", LANGUAGE_SCOPED_METHODS)
@pytest.mark.parametrize("cls", _implementations(), ids=lambda c: c.__name__)
def test_language_is_a_required_keyword_only_parameter(cls, method):
    parameter = inspect.signature(getattr(cls, method)).parameters.get("language")

    assert parameter is not None, f"{cls.__name__}.{method} has no language parameter"
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty


def test_calling_without_a_language_raises_type_error():
    from app.flashcards.services.sqlite_storage import SQLiteFlashcardStorageProvider

    with pytest.raises(TypeError):
        SQLiteFlashcardStorageProvider(db=None).list_decks()


@pytest.mark.parametrize("record", ["DeckRecord", "SessionRecord"])
def test_deck_and_session_records_carry_their_language(record):
    import dataclasses

    from app.flashcards.services import storage

    fields = {field.name for field in dataclasses.fields(getattr(storage, record))}
    assert "target_language" in fields
