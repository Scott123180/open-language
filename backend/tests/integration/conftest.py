"""Shared fixtures for integration tests."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base


def _configure_sqlite(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(autouse=True)
def isolated_tts_cache(tmp_path, monkeypatch):
    """Speech a test synthesises lands in its own tmp_path, never the learner's audio cache."""
    from app.flashcards import router as flashcards_router
    from app.routers import audio, chat

    for module in (audio, chat, flashcards_router):
        monkeypatch.setattr(module, "_tts_cache_dir", lambda: tmp_path / "tts_cache")


def make_test_session(db_path: str):
    """Create a SQLAlchemy session bound to the given SQLite path."""
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _configure_sqlite)
    # Import all models so metadata is populated
    import app.corrections.models  # noqa: F401
    import app.models.app_settings  # noqa: F401
    import app.models.conversation  # noqa: F401
    import app.models.learning_tool_result  # noqa: F401
    import app.models.message  # noqa: F401
    import app.models.vocabulary_item  # noqa: F401

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)  # noqa: N806
    return Session(), engine
