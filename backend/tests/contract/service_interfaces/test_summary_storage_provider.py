"""T079: SummaryStorage is an ABC with get_latest and save, implemented by SQLite."""

from abc import ABC

from app.conversation_summary.services.sqlite_storage import SQLiteSummaryStorage
from app.conversation_summary.services.storage import StoredSummary, SummaryStorage
from app.conversation_summary.services.summariser import SummaryPoint
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.support.scratch_database import make_session


def test_summary_storage_is_an_abc_with_two_methods():
    assert issubclass(SummaryStorage, ABC)
    assert SummaryStorage.__abstractmethods__ == frozenset({"get_latest", "save"})
    assert issubclass(SQLiteSummaryStorage, SummaryStorage)


def test_the_sqlite_storage_keeps_the_latest_summary(tmp_path):
    session = make_session(tmp_path / "summaries.db")
    conversation = SQLiteStorageProvider(session).create_conversation("s", "S", "es", "en", "m")
    storage = SQLiteSummaryStorage(session)
    first = StoredSummary(conversation.id, 3, "natural", (SummaryPoint("Uno.", "One."),))
    second = StoredSummary(conversation.id, 5, "beginner", (SummaryPoint("Dos.", "Two."),))

    storage.save(first)
    storage.save(second)

    assert storage.get_latest(conversation.id) == second
    assert storage.get_latest(999) is None
