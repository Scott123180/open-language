"""A throwaway SQLite database with every table registered, foreign keys on."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base


def _configure_sqlite(dbapi_conn, _record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _register_models() -> None:
    import app.corrections.models  # noqa: F401
    import app.flashcards.models  # noqa: F401
    import app.podcasts.models  # noqa: F401
    from app.models import (  # noqa: F401
        app_settings,
        conversation,
        learning_tool_result,
        message,
        vocabulary_item,
        voice_choice,
    )


def make_sessions(db_file: Path) -> sessionmaker:
    """A session factory on a new database at `db_file` holding the full current schema.

    Give each request its own session, as `get_db` does: speech is synthesised on a worker
    thread, and one session shared across threads races.
    """
    _register_models()
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _configure_sqlite)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def make_session(db_file: Path) -> Session:
    """One session on a new database at `db_file` holding the full current schema."""
    return make_sessions(db_file)()
