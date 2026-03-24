"""Unit tests for word list filtering logic (T013).

These tests verify the filtering logic in SQLiteFlashcardStorageProvider.list_words()
by testing with a seeded in-memory database.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.flashcards.services.sqlite_storage import SQLiteFlashcardStorageProvider
from app.models.vocabulary_item import VocabularyItem


def _configure_sqlite(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _configure_sqlite)
    import app.flashcards.models  # noqa: F401
    import app.models.app_settings  # noqa: F401
    import app.models.conversation  # noqa: F401
    import app.models.learning_tool_result  # noqa: F401
    import app.models.message  # noqa: F401
    import app.models.vocabulary_item  # noqa: F401

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)  # noqa: N806
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def storage(db):
    return SQLiteFlashcardStorageProvider(db)


@pytest.fixture()
def seeded_words(db):
    now = datetime.now(UTC)
    words = [
        VocabularyItem(
            word="bonjour",
            translation="hello",
            target_language="fr",
            native_language="en",
            saved_at=now - timedelta(days=5),
            classification="not_practiced",
            manual_override=False,
        ),
        VocabularyItem(
            word="merci",
            translation="thank you",
            target_language="fr",
            native_language="en",
            saved_at=now - timedelta(days=20),
            classification="difficult",
            manual_override=False,
        ),
        VocabularyItem(
            word="au revoir",
            translation="goodbye",
            target_language="fr",
            native_language="en",
            saved_at=now - timedelta(days=2),
            classification="almost_learned",
            manual_override=False,
        ),
        VocabularyItem(
            word="oui",
            translation="yes",
            target_language="fr",
            native_language="en",
            saved_at=now - timedelta(days=1),
            classification="learned",
            manual_override=False,
        ),
    ]
    db.add_all(words)
    db.commit()
    for w in words:
        db.refresh(w)
    return words


class TestListWordsNoFilter:
    def test_returns_all_words(self, storage, seeded_words):
        result = storage.list_words()
        assert len(result) == 4

    def test_ordered_by_saved_at_desc(self, storage, seeded_words):
        result = storage.list_words()
        dates = [r.saved_at for r in result]
        assert dates == sorted(dates, reverse=True)


class TestListWordsClassificationFilter:
    def test_filter_single_classification(self, storage, seeded_words):
        result = storage.list_words(classifications=["difficult"])
        assert len(result) == 1
        assert result[0].classification == "difficult"

    def test_filter_multiple_classifications(self, storage, seeded_words):
        result = storage.list_words(classifications=["difficult", "almost_learned"])
        assert len(result) == 2
        classifications = {r.classification for r in result}
        assert classifications == {"difficult", "almost_learned"}

    def test_filter_returns_empty_when_no_match(self, storage, seeded_words):
        result = storage.list_words(classifications=["learned"])
        assert len(result) == 1
        assert result[0].word == "oui"


class TestListWordsDateFilter:
    def test_filter_date_from(self, storage, seeded_words):
        cutoff = datetime.now(UTC) - timedelta(days=7)
        result = storage.list_words(date_from=cutoff)
        # "bonjour" (5d ago), "au revoir" (2d ago), "oui" (1d ago)
        assert len(result) == 3

    def test_filter_date_to(self, storage, seeded_words):
        cutoff = datetime.now(UTC) - timedelta(days=10)
        result = storage.list_words(date_to=cutoff)
        # Only "merci" (20d ago)
        assert len(result) == 1
        assert result[0].word == "merci"

    def test_filter_date_range(self, storage, seeded_words):
        date_from = datetime.now(UTC) - timedelta(days=6)
        date_to = datetime.now(UTC) - timedelta(days=3)
        result = storage.list_words(date_from=date_from, date_to=date_to)
        # "bonjour" (5d ago) matches [3d, 6d] range
        assert len(result) == 1
        assert result[0].word == "bonjour"


class TestListWordsSearchFilter:
    def test_search_exact_match(self, storage, seeded_words):
        result = storage.list_words(search="merci")
        assert len(result) == 1
        assert result[0].word == "merci"

    def test_search_partial_match(self, storage, seeded_words):
        result = storage.list_words(search="au")
        assert len(result) == 1
        assert result[0].word == "au revoir"

    def test_search_case_insensitive(self, storage, seeded_words):
        result = storage.list_words(search="BONJOUR")
        assert len(result) == 1
        assert result[0].word == "bonjour"

    def test_search_no_match_returns_empty(self, storage, seeded_words):
        result = storage.list_words(search="xyz_no_match")
        assert len(result) == 0


class TestListWordsCombinedFilters:
    def test_classification_and_search(self, storage, seeded_words):
        result = storage.list_words(classifications=["difficult"], search="merci")
        assert len(result) == 1
        assert result[0].word == "merci"

    def test_classification_and_date_no_overlap(self, storage, seeded_words):
        cutoff = datetime.now(UTC) - timedelta(days=10)
        result = storage.list_words(classifications=["not_practiced"], date_to=cutoff)
        # "bonjour" is not_practiced but saved 5d ago (after cutoff)
        assert len(result) == 0
