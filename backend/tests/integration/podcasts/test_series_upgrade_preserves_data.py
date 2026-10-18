"""010 T005: upgrading a pre-010 database rewrites nothing (SC-009, FR-022).

The "before" database is built from the frozen 007 schema, never from the live ORM metadata,
which already holds the five 010 tables.
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app import database
from tests.integration.conftest import _configure_sqlite
from tests.support.podcast_harness import podcast_harness_on

SCHEMA_007 = Path(__file__).resolve().parents[2] / "fixtures" / "schema_007.sql"
NOW = "2026-10-10 10:00:00.000000"

SEED_007 = (
    "INSERT INTO app_settings (id, llm_provider, llm_model, llm_effort, target_language, "
    "native_language, tts_voice, suggestion_count, whisper_model, correction_mode, "
    f"conversation_level, summary_language, updated_at) VALUES (1, 'ollama', 'llama3.1:8b', "
    f"'low', 'es', 'en', 'es_ES-davefx-medium', 2, 'small', 'off', 'natural', 'conversation', "
    f"'{NOW}')",
    "INSERT INTO podcast_preferences (id, last_format, is_show_text_on, interests, learner_name, "
    f"updated_at) VALUES (1, 'panel', 1, '[\"chess\"]', 'Sam', '{NOW}')",
    "INSERT INTO conversations (id, scenario_id, scenario_title, target_language, "
    "native_language, status, started_at, ended_at, llm_model) VALUES "
    f"(1, 'podcast', 'Big Little Questions', 'es', 'en', 'COMPLETED', '{NOW}', '{NOW}', 'l3'),"
    f"(2, 'podcast', 'Game Day', 'de', 'en', 'ACTIVE', '{NOW}', NULL, 'l3'),"
    f"(3, 'order-coffee', 'Order a Coffee', 'es', 'en', 'COMPLETED', '{NOW}', '{NOW}', 'l3')",
    "INSERT INTO podcast_episodes (conversation_id, show_source, show_id, premise, topic, "
    "learner_role, format, length, learner_name, created_at) VALUES "
    "(1, 'ready_made', 'big-little-questions', 'Everyday curiosities.', 'everyday curiosities', "
    f"'guest', 'one_host', 'short', 'Sam', '{NOW}'),"
    "(2, 'ready_made', 'game-day', 'Big matches.', 'sport', 'co_host', 'panel', 'short', NULL, "
    f"'{NOW}')",
    "INSERT INTO podcast_hosts (id, conversation_id, slot, name, personality, voice_key, "
    "show_role, angle) VALUES "
    "(1, 1, 'lead', 'Hugo', 'curious_interviewer', 'es_ES-davefx-medium', 'host', NULL),"
    "(2, 2, 'lead', 'Jonas', 'enthusiast', 'de_DE-thorsten-medium', 'host', NULL),"
    "(3, 2, 'second', 'Lea', 'contrarian', 'de_DE-kerstin-low', 'co_host', NULL)",
    "INSERT INTO messages (id, conversation_id, role, content, input_source, created_at) VALUES "
    f"(1, 1, 'ASSISTANT', '¡Bienvenidos!', NULL, '{NOW}'),"
    f"(2, 1, 'USER', 'Odio las mañanas.', 'KEYBOARD', '{NOW}'),"
    f"(3, 2, 'ASSISTANT', 'Willkommen!', NULL, '{NOW}'),"
    f"(4, 3, 'ASSISTANT', '¿Qué desea?', NULL, '{NOW}')",
    "INSERT INTO podcast_host_lines (message_id, conversation_id, host_id, intent, "
    "invites_learner, is_passed, is_revealed, was_trimmed) VALUES "
    "(1, 1, 1, 'open', 1, 0, 0, 0), (3, 2, 2, 'open', 0, 0, 0, 0)",
    "INSERT INTO vocabulary_items (id, word, translation, target_language, native_language, "
    "source_conversation_id, saved_at, classification, manual_override) VALUES "
    f"(1, 'mañana', 'morning', 'es', 'en', 1, '{NOW}', 'learned', 0),"
    f"(2, 'Spiel', 'game', 'de', 'en', 2, '{NOW}', 'not_practiced', 0)",
)
PRESERVED_TABLES = {
    "app_settings": "id",
    "podcast_preferences": "id",
    "conversations": "id",
    "podcast_episodes": "conversation_id",
    "podcast_hosts": "id",
    "podcast_host_lines": "message_id",
    "messages": "id",
    "vocabulary_items": "id",
}
SERIES_TABLES = {
    "podcast_shows",
    "podcast_series",
    "podcast_series_hosts",
    "podcast_series_episodes",
    "podcast_series_memories",
}


def _build_007_database(db_file: Path) -> None:
    with sqlite3.connect(db_file) as conn:
        conn.executescript(SCHEMA_007.read_text())
        for statement in SEED_007:
            conn.execute(statement)


def _pre_010_columns(table: str) -> list[str]:
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA_007.read_text())
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _snapshot(db_file: Path) -> dict[str, list[tuple]]:
    with sqlite3.connect(db_file) as conn:
        return {
            table: conn.execute(
                f"SELECT {', '.join(_pre_010_columns(table))} FROM {table} ORDER BY {order}"
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
    db_file = tmp_path / "pre-010.db"
    _build_007_database(db_file)
    before = _snapshot(db_file)
    _init_db_twice(db_file, monkeypatch)
    return db_file, before


def test_the_fixture_is_the_pre_010_schema():
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA_007.read_text())
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}

    assert {"podcast_episodes", "podcast_hosts", "podcast_host_lines"} <= tables
    assert not SERIES_TABLES & tables


def test_every_pre_010_row_is_unchanged(upgraded):
    db_file, before = upgraded

    assert _snapshot(db_file) == before


def test_the_five_series_tables_exist_after_the_upgrade(upgraded):
    db_file, _before = upgraded

    assert _tables(db_file) >= SERIES_TABLES


def test_no_pre_010_episode_belongs_to_a_series(upgraded):
    db_file, _before = upgraded

    with sqlite3.connect(db_file) as conn:
        count = conn.execute("SELECT count(*) FROM podcast_series_episodes").fetchone()

    assert count == (0,)


# --- T043: the upgraded data through the API (FR-022) ---------------------------------------


@pytest.fixture
def upgraded_app(upgraded, tmp_path):
    db_file, _before = upgraded
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, poolclass=NullPool
    )
    event.listen(engine, "connect", _configure_sqlite)
    with podcast_harness_on(sessionmaker(bind=engine), tmp_path) as harness:
        yield harness
    engine.dispose()


def test_pre_010_episodes_are_listed_with_no_episode_number(upgraded_app):
    rows = upgraded_app.client.get("/api/podcasts/episodes").json()

    assert sorted(row["conversation_id"] for row in rows) == [1, 2]
    assert all(row["episode_number"] is None for row in rows)


def test_every_show_opens_with_no_series(upgraded_app):
    shows = upgraded_app.client.get("/api/podcasts/catalog").json()["shows"]

    assert all(show["series"] is None for show in shows)


def test_a_show_a_pre_010_episode_used_starts_its_series_at_episode_1(upgraded_app):
    episode = upgraded_app.start_series(show_id="big-little-questions")

    assert episode["series"]["episode_number"] == 1
