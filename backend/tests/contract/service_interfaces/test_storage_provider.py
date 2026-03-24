from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.storage.sqlite import SQLiteStorageProvider


def _configure_sqlite(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def storage(tmp_path: Path) -> StorageProvider:
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _configure_sqlite)
    import app.models.app_settings  # noqa: F401
    import app.models.conversation  # noqa: F401
    import app.models.learning_tool_result  # noqa: F401
    import app.models.message  # noqa: F401
    import app.models.vocabulary_item  # noqa: F401

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)  # noqa: N806
    session = Session()
    yield SQLiteStorageProvider(session)
    session.close()


def test_create_conversation_get_conversation_round_trip(storage: StorageProvider) -> None:
    conv = storage.create_conversation(
        scenario_id="buy-train-ticket",
        scenario_title="Buy a Train Ticket",
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
    )
    fetched = storage.get_conversation(conv.id)
    assert fetched is not None
    assert fetched.id == conv.id
    assert fetched.scenario_id == "buy-train-ticket"
    assert fetched.status == "active"


def test_save_message_get_messages_ordered(storage: StorageProvider) -> None:
    conv = storage.create_conversation(
        scenario_id="s1",
        scenario_title="S1",
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
    )
    storage.save_message(conv.id, "user", "Hello")
    storage.save_message(conv.id, "assistant", "Hola")
    messages = storage.get_messages(conv.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[0].created_at <= messages[1].created_at


def test_get_or_create_learning_result_calls_compute_once(storage: StorageProvider) -> None:
    conv = storage.create_conversation(
        scenario_id="s1",
        scenario_title="S1",
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
    )
    msg = storage.save_message(conv.id, "user", "Hello")
    call_count = 0

    def compute():
        nonlocal call_count
        call_count += 1
        return "grammar feedback"

    r1 = storage.get_or_create_learning_result(msg.id, "grammar", None, compute)
    r2 = storage.get_or_create_learning_result(msg.id, "grammar", None, compute)
    assert call_count == 1
    assert r1.result == r2.result == "grammar feedback"


def test_save_vocabulary_item_idempotent(storage: StorageProvider) -> None:
    conv = storage.create_conversation(
        scenario_id="s1",
        scenario_title="S1",
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
    )
    storage.save_vocabulary_item("hola", "hello", "es", "en", conv.id)
    storage.save_vocabulary_item("hola", "hello", "es", "en", conv.id)
    items = storage.list_vocabulary()
    assert len([i for i in items if i.word == "hola" and i.target_language == "es"]) == 1


def test_get_settings_returns_defaults(storage: StorageProvider) -> None:
    settings = storage.get_settings()
    assert isinstance(settings, AppSettingsRecord)
    assert settings.llm_model == "llama3.1:8b"
    assert settings.target_language == "es"
    assert settings.native_language == "en"
    assert settings.suggestion_count == 1


def test_update_settings_changes_field_and_persists(storage: StorageProvider) -> None:
    storage.get_settings()
    updated = storage.update_settings(llm_model="mistral", suggestion_count=3)
    assert updated.llm_model == "mistral"
    assert updated.suggestion_count == 3
    refetched = storage.get_settings()
    assert refetched.llm_model == "mistral"
    assert refetched.suggestion_count == 3
