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
