import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

_DUPLICATE_COLUMN_MESSAGE = "duplicate column name"


class Base(DeclarativeBase):
    pass


def _configure_sqlite(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine():
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{settings.db_path}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _configure_sqlite)
    return engine


_engine = create_db_engine()
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import app.flashcards.models  # noqa: F401 — registers flashcard tables with Base
    from app.models import (  # noqa: F401
        app_settings,
        conversation,
        learning_tool_result,
        message,
        vocabulary_item,
    )

    Base.metadata.create_all(bind=_engine)
    _migrate_db()


def _migrate_db() -> None:
    """Apply additive schema migrations for existing databases."""
    with _engine.connect() as conn:
        _add_column_if_missing(conn, "conversations", "custom_prompt TEXT")
        _add_column_if_missing(
            conn, "app_settings", "whisper_model VARCHAR(50) NOT NULL DEFAULT 'base'"
        )
        _add_column_if_missing(
            conn, "vocabulary_items", "classification VARCHAR(20) NOT NULL DEFAULT 'not_practiced'"
        )
        _add_column_if_missing(
            conn, "vocabulary_items", "manual_override BOOLEAN NOT NULL DEFAULT FALSE"
        )
        _add_column_if_missing(conn, "vocabulary_items", "tts_cache_path VARCHAR(500)")


def _add_column_if_missing(conn, table: str, column_definition: str) -> None:
    """Add a column, treating an existing column as success.

    Only the duplicate-column case is tolerated. Every other failure — a missing
    table, a malformed definition — is a real migration defect and must surface
    rather than leave the schema silently wrong.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_definition}"))
        conn.commit()
    except OperationalError as exc:
        conn.rollback()
        if _DUPLICATE_COLUMN_MESSAGE not in str(exc).lower():
            raise
        logger.debug("Column already present on %s: %s", table, column_definition)
