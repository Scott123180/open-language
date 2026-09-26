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
        from app import database

        engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE app_settings ("
                    "id INTEGER PRIMARY KEY, llm_model VARCHAR(100) NOT NULL)"
                )
            )
            conn.execute(
                text(
                    "CREATE TABLE conversations (id INTEGER PRIMARY KEY, scenario_id VARCHAR(100))"
                )
            )
            conn.execute(
                text("CREATE TABLE messages (id INTEGER PRIMARY KEY, content TEXT NOT NULL)")
            )
            conn.execute(text("CREATE TABLE vocabulary_items (id INTEGER PRIMARY KEY)"))
            conn.commit()
        monkeypatch.setattr(database, "_engine", engine)
        return engine

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
        from app import database

        engine = create_engine(f"sqlite:///{tmp_path / 'legacy-messages.db'}")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE app_settings (id INTEGER PRIMARY KEY)"))
            conn.execute(text("CREATE TABLE conversations (id INTEGER PRIMARY KEY)"))
            conn.execute(
                text("CREATE TABLE messages (id INTEGER PRIMARY KEY, content TEXT NOT NULL)")
            )
            conn.execute(text("CREATE TABLE vocabulary_items (id INTEGER PRIMARY KEY)"))
            conn.commit()
        monkeypatch.setattr(database, "_engine", engine)
        return engine

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
