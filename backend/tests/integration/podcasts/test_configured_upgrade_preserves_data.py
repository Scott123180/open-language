"""011 T004: upgrading a pre-011 database rewrites nothing (SC-010, FR-025).

The "before" database is built from the frozen 010 schema, never from the live ORM metadata,
which already holds the two 011 tables. A pre-feature episode has no settings row, so it loads
as legacy and its standing prompt is still 007's, byte for byte.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app import database
from app.conversation_levels import ConversationLevel
from app.podcasts.services.episodes import load_episode
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from tests.integration.conftest import _configure_sqlite

SCHEMA_010 = Path(__file__).resolve().parents[2] / "fixtures" / "schema_010.sql"
GOLDEN_FILE = Path(__file__).resolve().parents[2] / "unit" / "podcasts" / "golden"
ONE_OFF_GOLDEN_KEY = "standing|one_host|Sam|beginner"
NOW = "2026-10-30 10:00:00.000000"
ONE_OFF_ID, FIRST_SERIES_ID, SECOND_SERIES_ID, ROLEPLAY_ID = 1, 2, 3, 4
SNAPSHOT_1 = json.dumps(
    {"episode_number": 1, "topics_covered": [], "about_learner": [], "new_host_slots": []}
)
SNAPSHOT_2 = json.dumps(
    {
        "episode_number": 2,
        "topics_covered": ["los bostezos"],
        "about_learner": ["Odia las mañanas."],
        "new_host_slots": [],
    },
    ensure_ascii=False,
)

SEED_010 = (
    "INSERT INTO app_settings (id, llm_provider, llm_model, llm_effort, target_language, "
    "native_language, tts_voice, suggestion_count, whisper_model, correction_mode, "
    f"conversation_level, summary_language, updated_at) VALUES (1, 'ollama', 'llama3.1:8b', "
    f"'low', 'es', 'en', 'es_ES-davefx-medium', 2, 'small', 'off', 'beginner', 'conversation', "
    f"'{NOW}')",
    "INSERT INTO podcast_preferences (id, last_format, is_show_text_on, interests, learner_name, "
    f"updated_at) VALUES (1, 'one_host', 0, '[\"chess\"]', 'Sam', '{NOW}')",
    "INSERT INTO conversations (id, scenario_id, scenario_title, target_language, "
    "native_language, status, started_at, ended_at, llm_model) VALUES "
    f"(1, 'podcast', 'Weekend Food Talk', 'es', 'en', 'ACTIVE', '{NOW}', NULL, 'l3'),"
    f"(2, 'podcast', 'Big Little Questions', 'es', 'en', 'COMPLETED', '{NOW}', '{NOW}', 'l3'),"
    f"(3, 'podcast', 'Big Little Questions', 'es', 'en', 'COMPLETED', '{NOW}', '{NOW}', 'l3'),"
    f"(4, 'order-coffee', 'Order a Coffee', 'es', 'en', 'COMPLETED', '{NOW}', '{NOW}', 'l3')",
    "INSERT INTO podcast_episodes (conversation_id, show_source, show_id, premise, topic, "
    "learner_role, format, length, learner_name, created_at) VALUES "
    "(1, 'ready_made', 'weekend-food-talk', "
    "'Two food lovers swap weekend cooking wins and disasters.', 'food', 'guest', 'one_host', "
    f"'medium', 'Sam', '{NOW}'),"
    "(2, 'ready_made', 'big-little-questions', 'Everyday curiosities.', 'everyday curiosities', "
    f"'guest', 'panel', 'short', 'Sam', '{NOW}'),"
    "(3, 'ready_made', 'big-little-questions', 'Everyday curiosities.', 'everyday curiosities', "
    f"'guest', 'panel', 'short', 'Sam', '{NOW}')",
    "INSERT INTO podcast_hosts (id, conversation_id, slot, name, personality, voice_key, "
    "show_role, angle) VALUES "
    "(1, 1, 'lead', 'Lucía', 'enthusiast', 'es_AR-daniela-high', 'host', 'Loves markets.'),"
    "(2, 2, 'lead', 'Hugo', 'curious_interviewer', 'es_ES-davefx-medium', 'host', NULL),"
    "(3, 2, 'second', 'Inés', 'expert', 'es_AR-daniela-high', 'co_host', NULL),"
    "(4, 3, 'lead', 'Hugo', 'curious_interviewer', 'es_ES-davefx-medium', 'host', NULL),"
    "(5, 3, 'second', 'Inés', 'expert', 'es_AR-daniela-high', 'co_host', NULL)",
    "INSERT INTO messages (id, conversation_id, role, content, input_source, created_at) VALUES "
    f"(1, 1, 'ASSISTANT', '¡Bienvenidos al programa!', NULL, '{NOW}'),"
    f"(2, 1, 'ASSISTANT', 'Hoy hablamos de pan.', NULL, '{NOW}'),"
    f"(3, 1, 'ASSISTANT', '¿Qué cocinas tú?', NULL, '{NOW}'),"
    f"(4, 2, 'ASSISTANT', '¡Hola a todos!', NULL, '{NOW}'),"
    f"(5, 3, 'ASSISTANT', '¡Bienvenidos otra vez!', NULL, '{NOW}'),"
    f"(6, 4, 'ASSISTANT', '¿Qué desea?', NULL, '{NOW}')",
    "INSERT INTO podcast_host_lines (message_id, conversation_id, host_id, intent, "
    "invites_learner, is_passed, is_revealed, was_trimmed) VALUES "
    "(1, 1, 1, 'discuss', 1, 0, 0, 0), (2, 1, 1, 'discuss', 1, 1, 0, 0),"
    "(3, 1, 1, 'discuss', 1, 0, 0, 0), (4, 2, 2, 'open', 0, 0, 0, 0),"
    "(5, 3, 4, 'open', 0, 0, 0, 0)",
    "INSERT INTO podcast_shows (id, template_id, source, title, premise, topic, learner_role, "
    "lead_personality, second_personality, lead_angle, second_angle, favourited_at, "
    "last_played_at, created_at) VALUES (1, 'big-little-questions', 'ready_made', NULL, NULL, "
    f"NULL, NULL, NULL, NULL, NULL, NULL, '{NOW}', '{NOW}', '{NOW}')",
    "INSERT INTO podcast_series (id, show_id, target_language, created_at) VALUES "
    f"(1, 1, 'es', '{NOW}')",
    "INSERT INTO podcast_series_hosts (id, series_id, slot, name, personality, voice_key, "
    "show_role, angle, joined_after_episodes) VALUES "
    "(1, 1, 'lead', 'Hugo', 'curious_interviewer', 'es_ES-davefx-medium', 'host', NULL, 0),"
    "(2, 1, 'second', 'Inés', 'expert', 'es_AR-daniela-high', 'co_host', NULL, 0)",
    "INSERT INTO podcast_series_episodes (conversation_id, series_id, episode_number, snapshot, "
    f"remembered_up_to_message_id) VALUES (2, 1, 1, '{SNAPSHOT_1}', 4), "
    f"(3, 1, 2, '{SNAPSHOT_2}', 5)",
    "INSERT INTO podcast_series_memories (id, series_id, conversation_id, kind, "
    "conversation_language, english, created_at) VALUES "
    f"(1, 1, 2, 'topic', 'los bostezos', 'yawning', '{NOW}'),"
    f"(2, 1, 2, 'learner', 'Odia las mañanas.', 'You hate mornings.', '{NOW}'),"
    f"(3, 1, 3, 'topic', 'el sueño', 'sleep', '{NOW}')",
    "INSERT INTO vocabulary_items (id, word, translation, target_language, native_language, "
    "source_conversation_id, saved_at, classification, manual_override) VALUES "
    f"(1, 'pan', 'bread', 'es', 'en', 1, '{NOW}', 'learned', 0),"
    f"(2, 'café', 'coffee', 'es', 'en', 4, '{NOW}', 'not_practiced', 0)",
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
    "podcast_shows": "id",
    "podcast_series": "id",
    "podcast_series_hosts": "id",
    "podcast_series_episodes": "conversation_id",
    "podcast_series_memories": "id",
}
SETTINGS_TABLES = {"podcast_episode_settings", "podcast_series_settings"}


def _build_010_database(db_file: Path) -> None:
    with sqlite3.connect(db_file) as conn:
        conn.executescript(SCHEMA_010.read_text())
        for statement in SEED_010:
            conn.execute(statement)


def _pre_011_columns(table: str) -> list[str]:
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA_010.read_text())
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _snapshot(db_file: Path) -> dict[str, list[tuple]]:
    with sqlite3.connect(db_file) as conn:
        return {
            table: conn.execute(
                f"SELECT {', '.join(_pre_011_columns(table))} FROM {table} ORDER BY {order}"
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


def _row_count(db_file: Path, table: str) -> int:
    with sqlite3.connect(db_file) as conn:
        return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


@pytest.fixture
def upgraded(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "pre-011.db"
    _build_010_database(db_file)
    before = _snapshot(db_file)
    _init_db_twice(db_file, monkeypatch)
    return db_file, before


@pytest.fixture
def upgraded_storage(upgraded):
    db_file, _before = upgraded
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, poolclass=NullPool
    )
    event.listen(engine, "connect", _configure_sqlite)
    session = sessionmaker(bind=engine)()
    yield SQLitePodcastStorage(session)
    session.close()
    engine.dispose()


def test_the_fixture_is_the_pre_011_schema():
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA_010.read_text())
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}

    assert {"podcast_series", "podcast_series_memories", "podcast_preferences"} <= tables
    assert not SETTINGS_TABLES & tables
    assert "last_style" not in _pre_011_columns("podcast_preferences")


def test_every_pre_011_row_is_unchanged(upgraded):
    db_file, before = upgraded

    assert _snapshot(db_file) == before


def test_the_two_settings_tables_exist_and_are_empty(upgraded):
    db_file, _before = upgraded

    assert _tables(db_file) >= SETTINGS_TABLES
    assert [_row_count(db_file, table) for table in sorted(SETTINGS_TABLES)] == [0, 0]


def test_the_preferences_row_gains_the_default_last_used_settings(upgraded):
    db_file, _before = upgraded

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT last_style, last_line_length, last_invite_frequency FROM podcast_preferences"
        ).fetchone()

    assert row == ("balanced", "medium", "sometimes")


def test_pre_011_host_lines_have_no_ask_and_no_addressee(upgraded):
    db_file, _before = upgraded

    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT ask, addressee FROM podcast_host_lines").fetchall()

    assert set(rows) == {(None, None)}


def test_a_pre_011_episode_loads_with_no_settings(upgraded_storage):
    assert upgraded_storage.get_episode(ONE_OFF_ID).settings is None


def test_a_pre_011_one_off_keeps_the_007_standing_prompt(upgraded_storage):
    golden = json.loads((GOLDEN_FILE / "one_off_prompts.json").read_text(encoding="utf-8"))

    episode = load_episode(upgraded_storage, ONE_OFF_ID)

    assert episode.standing_prompt(ConversationLevel.BEGINNER) == golden[ONE_OFF_GOLDEN_KEY]


# --- 011 T096: the pre-feature series through the API -------------------------------------

SERIES_ID = 1
STANDARD_USUAL = {
    "format": "one_host",
    "length": "medium",
    "style": "balanced",
    "line_length": "medium",
    "invite_frequency": "sometimes",
    "learner_role": "guest",
}


@pytest.fixture
def upgraded_harness(upgraded, tmp_path):
    from tests.support.podcast_harness import podcast_harness_on

    db_file, _before = upgraded
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, poolclass=NullPool
    )
    event.listen(engine, "connect", _configure_sqlite)
    with podcast_harness_on(sessionmaker(bind=engine), tmp_path) as harness:
        yield harness
    engine.dispose()


def test_a_pre_feature_series_has_the_shows_standard_settings(upgraded_harness):
    detail = upgraded_harness.client.get(f"/api/podcasts/series/{SERIES_ID}").json()

    assert (detail["usual_settings"], detail["is_standard"]) == (STANDARD_USUAL, True)
    assert [host["name"] for host in detail["hosts"]] == ["Hugo", "Inés"]
    assert all(host["has_taken_part"] for host in detail["hosts"])
    assert detail["episode_count"] == 2
    assert [p["text"] for p in detail["remembered"]["topics"]] == ["sleep", "yawning"]


def test_a_pre_feature_series_next_episode_is_configured(upgraded_harness):
    episode = upgraded_harness.start_series("panel")

    assert episode["series"] == {"series_id": SERIES_ID, "episode_number": 3}
    assert episode["settings"] is not None


def test_a_pre_feature_series_episodes_still_load_their_010_snapshots(upgraded_harness):
    numbers = [
        upgraded_harness.episode(conversation_id)["series"]["episode_number"]
        for conversation_id in (FIRST_SERIES_ID, SECOND_SERIES_ID)
    ]

    assert numbers == [1, 2]
