"""Shared fixtures for flashcard integration tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.flashcards.models  # noqa: F401
import app.models.app_settings  # noqa: F401

# Import all models at module level so Base.metadata is complete
# before any fixture creates an engine.
# IMPORTANT: these `import app.*` bindings are overwritten below by
# `from app.main import app as fastapi_app`, so use explicit module access.
import app.models.conversation  # noqa: F401
import app.models.learning_tool_result  # noqa: F401
import app.models.message  # noqa: F401
import app.models.vocabulary_item  # noqa: F401
from app.database import Base, get_db
from app.main import app as fastapi_app


def _configure_sqlite(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def db_session():
    """In-memory SQLite session with all tables created.

    Uses StaticPool so all connections share the same in-memory database
    (SQLite :memory: is per-connection by default which causes tables to
    disappear between create_all and the test query).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _configure_sqlite)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)  # noqa: N806
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """TestClient with database dependency overridden to use in-memory session."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
