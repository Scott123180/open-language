"""T017: upgrading a pre-006 database rewrites nothing (SC-005, FR-024, research R13).

The "before" database is built from the frozen 005 schema, never from the live ORM metadata,
which already holds the 006 tables and columns.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event

from app import database
from app.flashcards.services.sqlite_storage import SQLiteFlashcardStorageProvider
from app.main import app
from app.services.factory import get_flashcard_storage, get_storage
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import _configure_sqlite, make_test_session

SCHEMA_005 = Path(__file__).resolve().parents[2] / "fixtures" / "schema_005.sql"
NOW = "2026-09-20 10:00:00.000000"

SEED_005 = (
    "INSERT INTO app_settings (id, llm_provider, llm_model, llm_effort, target_language, "
    "native_language, tts_voice, suggestion_count, whisper_model, correction_mode, "
    f"conversation_level, updated_at) VALUES (1, 'ollama', 'llama3.1:8b', 'low', 'es', 'en', "
    f"'es_AR-daniela-high', 2, 'small', 'gentle', 'elementary', '{NOW}')",
    "INSERT INTO conversations (id, scenario_id, scenario_title, target_language, "
    "native_language, status, started_at, ended_at, llm_model) VALUES "
    f"(1, 'order-coffee', 'Order a Coffee', 'es', 'en', 'COMPLETED', '{NOW}', '{NOW}', 'llama3.1'),"
    f"(2, 'buy-train-ticket', 'Buy a Train Ticket', 'es', 'en', 'ACTIVE', '{NOW}', NULL, 'llama3.1')",
    "INSERT INTO messages (id, conversation_id, role, content, input_source, created_at) VALUES "
    f"(1, 1, 'ASSISTANT', '¡Hola! ¿Qué desea?', NULL, '{NOW}'),"
    f"(2, 1, 'USER', 'Un café, por favor.', 'KEYBOARD', '{NOW}'),"
    f"(3, 2, 'ASSISTANT', 'Buenos días.', NULL, '{NOW}')",
    "INSERT INTO vocabulary_items (id, word, translation, target_language, native_language, "
    "source_conversation_id, saved_at, classification, manual_override) VALUES "
    f"(1, 'café', 'coffee', 'es', 'en', 1, '{NOW}', 'learned', 0),"
    f"(2, 'billete', 'ticket', 'es', 'en', 2, '{NOW}', 'difficult', 1),"
    f"(3, 'año', 'year', 'es', 'en', NULL, '{NOW}', 'not_practiced', 0)",
    "INSERT INTO decks (id, name, practice_mode, algorithm, requested_size, created_at, "
    f"last_practiced_at) VALUES (1, 'Café words', 'recall', 'mixed_review', 2, '{NOW}', '{NOW}'),"
    f"(2, 'Travel', 'listen', 'not_practiced', 1, '{NOW}', NULL)",
    "INSERT INTO deck_cards (id, deck_id, vocabulary_item_id, position) VALUES "
    "(1, 1, 1, 0), (2, 1, 2, 1), (3, 2, 3, 0)",
    "INSERT INTO practice_sessions (id, deck_id, practice_mode, algorithm, started_at, ended_at, "
    "total_cards, cards_reviewed, knew_it_count, guessed_count, didnt_know_count, completed) "
    f"VALUES (1, 1, 'recall', 'mixed_review', '{NOW}', '{NOW}', 2, 2, 1, 0, 1, 1)",
    "INSERT INTO card_results (id, session_id, vocabulary_item_id, rating, rated_at) VALUES "
    f"(1, 1, 1, 'knew_it', '{NOW}'), (2, 1, 2, 'didnt_know', '{NOW}')",
    "INSERT INTO session_classification_snapshots (id, session_id, snapshotted_at, "
    "not_practiced_count, difficult_count, almost_learned_count, learned_count) "
    f"VALUES (1, 1, '{NOW}', 1, 1, 0, 1)",
)
PRESERVED_TABLES = (
    "app_settings",
    "conversations",
    "messages",
    "vocabulary_items",
    "decks",
    "deck_cards",
    "practice_sessions",
    "card_results",
    "session_classification_snapshots",
)


def _build_005_database(db_file: Path) -> None:
    with sqlite3.connect(db_file) as conn:
        conn.executescript(SCHEMA_005.read_text())
        for statement in SEED_005:
            conn.execute(statement)


def _pre_006_columns(table: str) -> list[str]:
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA_005.read_text())
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _snapshot(db_file: Path) -> dict[str, list[tuple]]:
    with sqlite3.connect(db_file) as conn:
        return {
            table: conn.execute(
                f"SELECT {', '.join(_pre_006_columns(table))} FROM {table} ORDER BY id"
            ).fetchall()
            for table in PRESERVED_TABLES
        }


def _init_db_twice(db_file: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _configure_sqlite)
    monkeypatch.setattr(database, "_engine", engine)
    database.init_db()
    database.init_db()
    engine.dispose()


@pytest.fixture
def upgraded(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "pre-006.db"
    _build_005_database(db_file)
    before = _snapshot(db_file)
    _init_db_twice(db_file, monkeypatch)
    return db_file, before


@pytest.fixture
def client(upgraded):
    db_file, _before = upgraded
    session, _engine = make_test_session(str(db_file))
    app.dependency_overrides[get_storage] = lambda: SQLiteStorageProvider(session)
    app.dependency_overrides[get_flashcard_storage] = lambda: SQLiteFlashcardStorageProvider(
        session
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    session.close()


def test_every_pre_006_row_is_unchanged(upgraded):
    db_file, before = upgraded

    assert _snapshot(db_file) == before


def test_the_settings_keep_spanish_and_the_chosen_voice(client):
    settings = client.get("/api/settings").json()

    assert (settings["target_language"], settings["tts_voice"]) == ("es", "es_AR-daniela-high")


def test_exactly_one_voice_choice_is_seeded(upgraded):
    db_file, _before = upgraded

    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT target_language, voice_key FROM voice_choices").fetchall()

    assert rows == [("es", "es_AR-daniela-high")]


def test_existing_decks_and_sessions_belong_to_spanish(upgraded):
    db_file, _before = upgraded

    with sqlite3.connect(db_file) as conn:
        decks = conn.execute("SELECT DISTINCT target_language FROM decks").fetchall()
        sessions = conn.execute("SELECT DISTINCT target_language FROM practice_sessions").fetchall()

    assert (decks, sessions) == ([("es",)], [("es",)])


def test_existing_decks_list_under_spanish(client):
    decks = client.get("/api/flashcards/decks", params={"language": "es"}).json()

    assert sorted(deck["name"] for deck in decks) == ["Café words", "Travel"]
