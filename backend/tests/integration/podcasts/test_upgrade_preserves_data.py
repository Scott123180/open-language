"""T005: upgrading a pre-007 database rewrites nothing (SC-011, research R18).

The "before" database is built from the frozen 006 schema, never from the live ORM metadata,
which already holds the 007 tables and columns.
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event

from app import database
from tests.integration.conftest import _configure_sqlite

SCHEMA_006 = Path(__file__).resolve().parents[2] / "fixtures" / "schema_006.sql"
NOW = "2026-09-27 10:00:00.000000"

SEED_006 = (
    "INSERT INTO app_settings (id, llm_provider, llm_model, llm_effort, target_language, "
    "native_language, tts_voice, suggestion_count, whisper_model, correction_mode, "
    f"conversation_level, updated_at) VALUES (1, 'ollama', 'llama3.1:8b', 'low', 'de', 'en', "
    f"'es_ES-davefx-medium', 2, 'small', 'gentle', 'elementary', '{NOW}')",
    "INSERT INTO voice_choices (target_language, voice_key, updated_at) VALUES "
    f"('de', 'de_DE-kerstin-low', '{NOW}')",
    "INSERT INTO conversations (id, scenario_id, scenario_title, target_language, "
    "native_language, status, started_at, ended_at, llm_model) VALUES "
    f"(1, 'order-coffee', 'Order a Coffee', 'es', 'en', 'COMPLETED', '{NOW}', '{NOW}', 'llama3.1'),"
    f"(2, 'buy-train-ticket', 'Buy a Train Ticket', 'de', 'en', 'ACTIVE', '{NOW}', NULL, "
    "'llama3.1')",
    "INSERT INTO messages (id, conversation_id, role, content, input_source, created_at) VALUES "
    f"(1, 1, 'ASSISTANT', '¡Hola! ¿Qué desea?', NULL, '{NOW}'),"
    f"(2, 1, 'USER', 'Un café, por favor.', 'KEYBOARD', '{NOW}'),"
    f"(3, 2, 'ASSISTANT', 'Guten Tag.', NULL, '{NOW}')",
    "INSERT INTO vocabulary_items (id, word, translation, target_language, native_language, "
    "source_conversation_id, saved_at, classification, manual_override) VALUES "
    f"(1, 'café', 'coffee', 'es', 'en', 1, '{NOW}', 'learned', 0),"
    f"(2, 'Fahrkarte', 'ticket', 'de', 'en', 2, '{NOW}', 'difficult', 1),"
    f"(3, 'año', 'year', 'es', 'en', NULL, '{NOW}', 'not_practiced', 0)",
    "INSERT INTO decks (id, name, practice_mode, algorithm, requested_size, created_at, "
    f"last_practiced_at, target_language) VALUES (1, 'Café words', 'recall', 'mixed_review', 2, "
    f"'{NOW}', '{NOW}', 'es')",
    "INSERT INTO deck_cards (id, deck_id, vocabulary_item_id, position) VALUES "
    "(1, 1, 1, 0), (2, 1, 3, 1)",
)
PRESERVED_TABLES = {
    "conversations": "id",
    "messages": "id",
    "vocabulary_items": "id",
    "decks": "id",
    "deck_cards": "id",
    "voice_choices": "target_language",
    "app_settings": "id",
}
PODCAST_TABLES = {"podcast_episodes", "podcast_hosts", "podcast_host_lines", "podcast_preferences"}


def _build_006_database(db_file: Path) -> None:
    with sqlite3.connect(db_file) as conn:
        conn.executescript(SCHEMA_006.read_text())
        for statement in SEED_006:
            conn.execute(statement)


def _pre_007_columns(table: str) -> list[str]:
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA_006.read_text())
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _snapshot(db_file: Path) -> dict[str, list[tuple]]:
    with sqlite3.connect(db_file) as conn:
        return {
            table: conn.execute(
                f"SELECT {', '.join(_pre_007_columns(table))} FROM {table} ORDER BY {order}"
            ).fetchall()
            for table, order in PRESERVED_TABLES.items()
        }


def _tables(db_file: Path) -> set[str]:
    with sqlite3.connect(db_file) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _init_db_twice(db_file: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _configure_sqlite)
    monkeypatch.setattr(database, "_engine", engine)
    database.init_db()
    database.init_db()
    engine.dispose()


@pytest.fixture
def upgraded(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "pre-007.db"
    _build_006_database(db_file)
    before = _snapshot(db_file)
    _init_db_twice(db_file, monkeypatch)
    return db_file, before


def test_the_fixture_is_the_pre_007_schema():
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA_006.read_text())
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}

    assert "voice_choices" in tables
    assert not PODCAST_TABLES & tables


def test_every_pre_007_row_is_unchanged(upgraded):
    db_file, before = upgraded

    assert _snapshot(db_file) == before


def test_the_podcast_tables_exist_after_the_upgrade(upgraded):
    db_file, _before = upgraded

    assert _tables(db_file) >= PODCAST_TABLES
