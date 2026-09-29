"""Unit tests for the additive schema migration helper in app.database."""

import pytest
from sqlalchemy import create_engine, text

from app.database import _add_column_if_missing


@pytest.fixture()
def connection():
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE widgets (id INTEGER PRIMARY KEY)"))
        conn.commit()
        yield conn


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


LEGACY_APP_SETTINGS = (
    "CREATE TABLE app_settings (id INTEGER PRIMARY KEY, llm_model VARCHAR(100) NOT NULL, "
    "target_language VARCHAR(20) NOT NULL DEFAULT 'es', "
    "tts_voice VARCHAR(200) NOT NULL DEFAULT 'es_ES-davefx-medium')"
)
LEGACY_TABLES = (
    "CREATE TABLE conversations (id INTEGER PRIMARY KEY, scenario_id VARCHAR(100))",
    "CREATE TABLE messages (id INTEGER PRIMARY KEY, content TEXT NOT NULL)",
    "CREATE TABLE vocabulary_items (id INTEGER PRIMARY KEY)",
    "CREATE TABLE decks (id INTEGER PRIMARY KEY)",
    "CREATE TABLE practice_sessions (id INTEGER PRIMARY KEY)",
)


def _legacy_engine(db_file, monkeypatch):
    """A database from before the additive columns, as `init_db()` finds it.

    `create_all()` runs before `_migrate_db()`, so the tables new in 006 already exist.
    """
    import app.models.voice_choice  # noqa: F401
    from app import database

    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        for statement in (LEGACY_APP_SETTINGS, *LEGACY_TABLES):
            conn.execute(text(statement))
        conn.commit()
    database.Base.metadata.create_all(
        bind=engine, tables=[database.Base.metadata.tables["voice_choices"]]
    )
    monkeypatch.setattr(database, "_engine", engine)
    return engine


class TestAddColumnIfMissing:
    def test_adds_a_column_that_does_not_exist(self, connection):
        _add_column_if_missing(connection, "widgets", "label VARCHAR(50)")

        assert "label" in _columns(connection, "widgets")

    def test_is_idempotent_when_the_column_already_exists(self, connection):
        _add_column_if_missing(connection, "widgets", "label VARCHAR(50)")
        _add_column_if_missing(connection, "widgets", "label VARCHAR(50)")

        assert "label" in _columns(connection, "widgets")

    def test_raises_when_the_table_does_not_exist(self, connection):
        with pytest.raises(Exception, match="no such table"):
            _add_column_if_missing(connection, "missing_table", "label VARCHAR(50)")

    def test_raises_on_malformed_column_definition(self, connection):
        with pytest.raises(Exception):  # noqa: B017 — any DB error must surface, not be swallowed
            _add_column_if_missing(connection, "widgets", "not a valid column def!!")


class TestMigrateDb:
    """_migrate_db() must upgrade a database that predates the current schema."""

    @pytest.fixture()
    def legacy_engine(self, tmp_path, monkeypatch):
        """An app_settings table created without any of the added columns."""
        return _legacy_engine(tmp_path / "legacy.db", monkeypatch)

    def _table_columns(self, engine, table: str) -> set[str]:
        with engine.connect() as conn:
            return _columns(conn, table)

    def test_adds_correction_mode_to_app_settings(self, legacy_engine):
        from app.database import _migrate_db

        _migrate_db()

        assert "correction_mode" in self._table_columns(legacy_engine, "app_settings")

    def test_correction_mode_defaults_to_off_for_existing_rows(self, legacy_engine):
        from app.database import _migrate_db

        with legacy_engine.connect() as conn:
            conn.execute(text("INSERT INTO app_settings (id, llm_model) VALUES (1, 'llama3.1')"))
            conn.commit()

        _migrate_db()

        with legacy_engine.connect() as conn:
            stored = conn.execute(text("SELECT correction_mode FROM app_settings")).scalar_one()
        assert stored == "off"

    def test_is_idempotent_on_a_second_run(self, legacy_engine):
        from app.database import _migrate_db

        _migrate_db()
        _migrate_db()

        assert "correction_mode" in self._table_columns(legacy_engine, "app_settings")


class TestMessageConfidenceMigration:
    """T073b: the two added message columns land on an existing database."""

    @pytest.fixture()
    def legacy_engine(self, tmp_path, monkeypatch):
        return _legacy_engine(tmp_path / "legacy-messages.db", monkeypatch)

    def _message_columns(self, engine) -> set[str]:
        with engine.connect() as conn:
            return _columns(conn, "messages")

    def test_adds_transcription_confidence(self, legacy_engine):
        from app.database import _migrate_db

        _migrate_db()

        assert "transcription_confidence" in self._message_columns(legacy_engine)

    def test_adds_is_low_confidence(self, legacy_engine):
        from app.database import _migrate_db

        _migrate_db()

        assert "is_low_confidence" in self._message_columns(legacy_engine)

    def test_existing_rows_keep_a_null_confidence(self, legacy_engine):
        from app.database import _migrate_db

        with legacy_engine.connect() as conn:
            conn.execute(text("INSERT INTO messages (id, content) VALUES (1, 'hola')"))
            conn.commit()

        _migrate_db()

        with legacy_engine.connect() as conn:
            stored = conn.execute(
                text("SELECT transcription_confidence, is_low_confidence FROM messages")
            ).one()
        assert stored == (None, None)

    def test_is_idempotent_on_a_second_run(self, legacy_engine):
        from app.database import _migrate_db

        _migrate_db()
        _migrate_db()

        assert "is_low_confidence" in self._message_columns(legacy_engine)


class TestMessageRecordExposesConfidence:
    def test_message_record_defaults_both_fields_to_none(self):
        import datetime

        from app.services.storage.base import MessageRecord

        record = MessageRecord(
            id=1,
            conversation_id=1,
            role="user",
            content="hola",
            input_source="keyboard",
            created_at=datetime.datetime.now(datetime.UTC),
            tts_audio_path=None,
        )

        assert record.transcription_confidence is None
        assert record.is_low_confidence is None


class TestLlmProviderMigration:
    """T016: a pre-004 database comes up as Ollama with its saved model untouched."""

    @pytest.fixture()
    def legacy_engine(self, tmp_path, monkeypatch):
        return _legacy_engine(tmp_path / "pre-004.db", monkeypatch)

    def test_pre_004_database_defaults_to_ollama_and_keeps_model(self, legacy_engine):
        from app.database import _migrate_db

        with legacy_engine.connect() as conn:
            conn.execute(text("INSERT INTO app_settings (id, llm_model) VALUES (1, 'llama3.1')"))
            conn.commit()

        _migrate_db()

        with legacy_engine.connect() as conn:
            stored = conn.execute(
                text("SELECT llm_provider, llm_effort, llm_model FROM app_settings")
            ).one()
        assert tuple(stored) == ("ollama", "low", "llama3.1")

    def test_migrate_db_applies_every_additive_column(self, legacy_engine):
        from app.database import _ADDITIVE_COLUMNS, _migrate_db

        _migrate_db()

        with legacy_engine.connect() as conn:
            for table, definition in _ADDITIVE_COLUMNS:
                assert definition.split()[0] in _columns(conn, table), (table, definition)


class TestFreshSchemaHasProviderColumns:
    def _column_info(self, tmp_path) -> dict[str, tuple]:
        import app.models.app_settings  # noqa: F401
        from app.database import Base

        engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["app_settings"]])
        with engine.connect() as conn:
            rows = conn.execute(text("PRAGMA table_info(app_settings)")).fetchall()
        return {row[1]: (row[2], row[3]) for row in rows}

    def test_llm_provider_is_a_required_short_string(self, tmp_path):
        assert self._column_info(tmp_path)["llm_provider"] == ("VARCHAR(20)", 1)

    def test_llm_effort_is_a_required_short_string(self, tmp_path):
        assert self._column_info(tmp_path)["llm_effort"] == ("VARCHAR(10)", 1)

    def test_migration_definitions_default_to_ollama_and_low(self):
        from app.database import _ADDITIVE_COLUMNS

        assert (
            "app_settings",
            "llm_provider VARCHAR(20) NOT NULL DEFAULT 'ollama'",
        ) in _ADDITIVE_COLUMNS
        assert (
            "app_settings",
            "llm_effort VARCHAR(10) NOT NULL DEFAULT 'low'",
        ) in _ADDITIVE_COLUMNS


class TestConversationLevelMigration:
    """005 T006: a pre-005 database comes up at Natural (FR-009)."""

    @pytest.fixture()
    def legacy_engine(self, tmp_path, monkeypatch):
        return _legacy_engine(tmp_path / "pre-005.db", monkeypatch)

    def test_conversation_level_is_an_additive_column(self):
        from app.database import _ADDITIVE_COLUMNS

        assert (
            "app_settings",
            "conversation_level VARCHAR(12) NOT NULL DEFAULT 'natural'",
        ) in _ADDITIVE_COLUMNS

    def test_adds_the_column_to_an_existing_database(self, legacy_engine):
        from app.database import _migrate_db

        _migrate_db()

        with legacy_engine.connect() as conn:
            assert "conversation_level" in _columns(conn, "app_settings")

    def test_the_existing_settings_row_reads_natural(self, legacy_engine):
        from app.database import _migrate_db

        with legacy_engine.connect() as conn:
            conn.execute(text("INSERT INTO app_settings (id, llm_model) VALUES (1, 'llama3.1')"))
            conn.commit()

        _migrate_db()

        with legacy_engine.connect() as conn:
            stored = conn.execute(text("SELECT conversation_level FROM app_settings")).scalar_one()
        assert stored == "natural"


class TestVoiceChoicesTable:
    """006 T011: one remembered voice per language (data-model §4)."""

    def test_init_db_creates_voice_choices(self, tmp_path, monkeypatch):
        from app import database

        engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
        monkeypatch.setattr(database, "_engine", engine)

        database.init_db()

        with engine.connect() as conn:
            rows = conn.execute(text("PRAGMA table_info(voice_choices)")).fetchall()
        assert {row[1]: bool(row[5]) for row in rows} == {
            "target_language": True,
            "voice_key": False,
            "updated_at": False,
        }


class TestVoiceChoiceSeed:
    """006 T011: an upgraded install keeps its voice, remembered for its language."""

    @pytest.fixture()
    def legacy_engine(self, tmp_path, monkeypatch):
        return _legacy_engine(tmp_path / "pre-006.db", monkeypatch)

    def _store_settings(self, engine, target_language: str, tts_voice: str) -> None:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO app_settings (id, llm_model, target_language, tts_voice) "
                    "VALUES (1, 'llama3.1', :language, :voice)"
                ),
                {"language": target_language, "voice": tts_voice},
            )
            conn.commit()

    def _choices(self, engine) -> list[tuple[str, str]]:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT target_language, voice_key FROM voice_choices"))
            return [tuple(row) for row in rows]

    def test_the_stored_voice_is_remembered_for_its_language(self, legacy_engine):
        from app.database import _migrate_db

        self._store_settings(legacy_engine, "es", "es_AR-daniela-high")

        _migrate_db()

        assert self._choices(legacy_engine) == [("es", "es_AR-daniela-high")]

    def test_a_voice_in_another_language_is_not_seeded(self, legacy_engine):
        from app.database import _migrate_db

        self._store_settings(legacy_engine, "de", "es_ES-davefx-medium")

        _migrate_db()

        assert self._choices(legacy_engine) == []

    def test_an_existing_choice_is_not_overwritten(self, legacy_engine):
        from app.database import _migrate_db

        self._store_settings(legacy_engine, "es", "es_AR-daniela-high")
        with legacy_engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO voice_choices (target_language, voice_key, updated_at) "
                    "VALUES ('es', 'es_ES-davefx-medium', CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()

        _migrate_db()

        assert self._choices(legacy_engine) == [("es", "es_ES-davefx-medium")]

    def test_without_a_settings_row_nothing_is_seeded(self, legacy_engine):
        from app.database import _migrate_db

        _migrate_db()

        assert self._choices(legacy_engine) == []

    def test_the_seed_is_idempotent(self, legacy_engine):
        from app.database import _migrate_db

        self._store_settings(legacy_engine, "es", "es_AR-daniela-high")

        _migrate_db()
        _migrate_db()

        assert self._choices(legacy_engine) == [("es", "es_AR-daniela-high")]


class TestFlashcardLanguageColumns:
    """006 T077: existing decks and practice history belong to Spanish (FR-021)."""

    @pytest.fixture()
    def legacy_engine(self, tmp_path, monkeypatch):
        return _legacy_engine(tmp_path / "pre-006-flashcards.db", monkeypatch)

    def test_the_two_language_columns_follow_each_other_in_introduction_order(self):
        from app.database import _ADDITIVE_COLUMNS

        assert _ADDITIVE_COLUMNS[-3:-1] == (
            ("decks", "target_language VARCHAR(20) NOT NULL DEFAULT 'es'"),
            ("practice_sessions", "target_language VARCHAR(20) NOT NULL DEFAULT 'es'"),
        )

    def test_an_existing_deck_and_session_read_spanish(self, legacy_engine):
        from app.database import _migrate_db

        with legacy_engine.connect() as conn:
            conn.execute(text("INSERT INTO decks (id) VALUES (1)"))
            conn.execute(text("INSERT INTO practice_sessions (id) VALUES (1)"))
            conn.commit()

        _migrate_db()

        with legacy_engine.connect() as conn:
            deck = conn.execute(text("SELECT target_language FROM decks")).scalar_one()
            session = conn.execute(
                text("SELECT target_language FROM practice_sessions")
            ).scalar_one()
        assert (deck, session) == ("es", "es")


class TestPodcastTables:
    """007 T011: the four podcast tables (data-model §2.1–§2.4)."""

    EXPECTED = {
        "podcast_episodes": {
            "conversation_id": ("INTEGER", 1),
            "show_source": ("VARCHAR(12)", 1),
            "show_id": ("VARCHAR(100)", 0),
            "premise": ("TEXT", 1),
            "topic": ("VARCHAR(200)", 1),
            "learner_role": ("VARCHAR(12)", 1),
            "format": ("VARCHAR(12)", 1),
            "length": ("VARCHAR(8)", 1),
            "learner_name": ("VARCHAR(40)", 0),
            "created_at": ("DATETIME", 1),
        },
        "podcast_hosts": {
            "id": ("INTEGER", 1),
            "conversation_id": ("INTEGER", 1),
            "slot": ("VARCHAR(8)", 1),
            "name": ("VARCHAR(40)", 1),
            "personality": ("VARCHAR(30)", 1),
            "voice_key": ("VARCHAR(200)", 1),
            "show_role": ("VARCHAR(20)", 1),
            "angle": ("TEXT", 0),
        },
        "podcast_host_lines": {
            "message_id": ("INTEGER", 1),
            "conversation_id": ("INTEGER", 1),
            "host_id": ("INTEGER", 1),
            "intent": ("VARCHAR(10)", 1),
            "invites_learner": ("BOOLEAN", 1),
            "is_passed": ("BOOLEAN", 1),
            "is_revealed": ("BOOLEAN", 1),
            "was_trimmed": ("BOOLEAN", 1),
        },
        "podcast_preferences": {
            "id": ("INTEGER", 1),
            "last_format": ("VARCHAR(12)", 1),
            "is_show_text_on": ("BOOLEAN", 1),
            "interests": ("TEXT", 1),
            "learner_name": ("VARCHAR(40)", 0),
            "updated_at": ("DATETIME", 1),
        },
    }

    @pytest.fixture()
    def fresh_engine(self, tmp_path, monkeypatch):
        from app import database

        engine = create_engine(f"sqlite:///{tmp_path / 'fresh-007.db'}")
        monkeypatch.setattr(database, "_engine", engine)
        return engine

    def _column_info(self, engine, table: str) -> dict[str, tuple]:
        with engine.connect() as conn:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1]: (row[2], row[3] or row[5] > 0) for row in rows}

    @pytest.mark.parametrize("table", list(EXPECTED))
    def test_init_db_creates_the_table_with_its_columns(self, fresh_engine, table):
        from app import database

        database.init_db()

        info = self._column_info(fresh_engine, table)
        assert {name: (kind, int(required)) for name, (kind, required) in info.items()} == (
            self.EXPECTED[table]
        )

    def test_init_db_is_idempotent(self, fresh_engine):
        from app import database

        database.init_db()
        database.init_db()

        with fresh_engine.connect() as conn:
            tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master"))}
        assert set(self.EXPECTED) <= tables


class TestSummaryStorage:
    """007 T083: the summary language column and the summaries table (data-model §2.5, §2.6)."""

    def test_the_summary_language_is_an_additive_column(self):
        from app.database import _ADDITIVE_COLUMNS

        assert (
            "app_settings",
            "summary_language VARCHAR(12) NOT NULL DEFAULT 'conversation'",
        ) in _ADDITIVE_COLUMNS

    def test_init_db_creates_the_summaries_table(self, tmp_path, monkeypatch):
        from app import database

        engine = create_engine(f"sqlite:///{tmp_path / 'summaries.db'}")
        monkeypatch.setattr(database, "_engine", engine)

        database.init_db()

        with engine.connect() as conn:
            rows = conn.execute(text("PRAGMA table_info(conversation_summaries)")).fetchall()
            settings = {row[1] for row in conn.execute(text("PRAGMA table_info(app_settings)"))}
        assert {row[1] for row in rows} == {
            "conversation_id",
            "up_to_message_id",
            "level",
            "points",
            "created_at",
        }
        assert "summary_language" in settings
