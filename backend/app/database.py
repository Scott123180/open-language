import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings
from app.conversation_levels import DEFAULT_CONVERSATION_LEVEL
from app.practice_languages import DEFAULT_PRACTICE_LANGUAGE
from app.services.llm.catalog import DEFAULT_PROVIDER_ID
from app.services.llm.selection_types import DEFAULT_EFFORT
from app.services.tts.voices import AVAILABLE_VOICES

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
    import app.conversation_summary.models  # noqa: F401 — registers the summaries table
    import app.corrections.models  # noqa: F401 — registers correction tables with Base
    import app.flashcards.models  # noqa: F401 — registers flashcard tables with Base
    import app.podcasts.models  # noqa: F401 — registers podcast tables with Base
    from app.models import (  # noqa: F401
        app_settings,
        conversation,
        learning_tool_result,
        message,
        vocabulary_item,
        voice_choice,
    )

    Base.metadata.create_all(bind=_engine)
    _migrate_db()


_ADDITIVE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("conversations", "custom_prompt TEXT"),
    ("app_settings", "whisper_model VARCHAR(50) NOT NULL DEFAULT 'base'"),
    ("app_settings", "correction_mode VARCHAR(10) NOT NULL DEFAULT 'off'"),
    ("vocabulary_items", "classification VARCHAR(20) NOT NULL DEFAULT 'not_practiced'"),
    ("vocabulary_items", "manual_override BOOLEAN NOT NULL DEFAULT FALSE"),
    ("vocabulary_items", "tts_cache_path VARCHAR(500)"),
    ("messages", "transcription_confidence FLOAT"),
    ("messages", "is_low_confidence BOOLEAN"),
    ("app_settings", f"llm_provider VARCHAR(20) NOT NULL DEFAULT '{DEFAULT_PROVIDER_ID}'"),
    ("app_settings", f"llm_effort VARCHAR(10) NOT NULL DEFAULT '{DEFAULT_EFFORT}'"),
    (
        "app_settings",
        f"conversation_level VARCHAR(12) NOT NULL DEFAULT '{DEFAULT_CONVERSATION_LEVEL.value}'",
    ),
    # Existing decks and practice history belong to the pre-006 language (FR-021).
    ("decks", f"target_language VARCHAR(20) NOT NULL DEFAULT '{DEFAULT_PRACTICE_LANGUAGE}'"),
    (
        "practice_sessions",
        f"target_language VARCHAR(20) NOT NULL DEFAULT '{DEFAULT_PRACTICE_LANGUAGE}'",
    ),
    ("app_settings", "summary_language VARCHAR(12) NOT NULL DEFAULT 'conversation'"),
)
"""(table, column definition) pairs, in the order they were introduced."""


def _migrate_db() -> None:
    """Apply additive schema migrations for existing databases."""
    with _engine.connect() as conn:
        for table, column_definition in _ADDITIVE_COLUMNS:
            _add_column_if_missing(conn, table, column_definition)
        _seed_voice_choices(conn)


def _seed_voice_choices(conn) -> None:
    """Remember a pre-006 voice for the language it speaks (FR-024). Idempotent."""
    from sqlalchemy import text

    stored = conn.execute(
        text("SELECT target_language, tts_voice FROM app_settings WHERE id = 1")
    ).first()
    if stored is None or not _voice_speaks(stored.tts_voice, stored.target_language):
        return
    conn.execute(
        text(
            "INSERT OR IGNORE INTO voice_choices (target_language, voice_key, updated_at) "
            "VALUES (:language, :voice, CURRENT_TIMESTAMP)"
        ),
        {"language": stored.target_language, "voice": stored.tts_voice},
    )
    conn.commit()


def _voice_speaks(voice_key: str, language_code: str) -> bool:
    return any(v.key == voice_key and v.language == language_code for v in AVAILABLE_VOICES)


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
