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
from app.services.factory import get_llm, get_tts
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.tts.base import TTSProvider

STUB_LLM_RESPONSE = "Stubbed model output."


class StubLLMProvider(LLMProvider):
    """Deterministic LLM stand-in so tests never reach a real Ollama daemon."""

    @property
    def model_name(self) -> str:
        return "stub-model"

    def chat(self, messages: list[ChatMessage]) -> str:
        return STUB_LLM_RESPONSE

    def chat_stream(self, messages: list[ChatMessage]):
        yield STUB_LLM_RESPONSE


class UnavailableLLMProvider(LLMProvider):
    """Stands in for a local model that is not running."""

    @property
    def model_name(self) -> str:
        return "unavailable-model"

    def chat(self, messages: list[ChatMessage]) -> str:
        raise LLMError("Ollama is not reachable")

    def chat_stream(self, messages: list[ChatMessage]):
        raise LLMError("Ollama is not reachable")


class StubTTSProvider(TTSProvider):
    """Writes a minimal valid WAV so tests never need a Piper voice file."""

    _EMPTY_WAV = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    @property
    def voice_name(self) -> str:
        return "stub-voice"

    def synthesize(self, text: str, output_path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self._EMPTY_WAV)


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
    """TestClient with the database and both local AI providers stubbed.

    The AI providers are overridden by default so results never depend on whether
    an Ollama daemon or a Piper voice happens to be installed on the machine
    running the suite.
    """

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    fastapi_app.dependency_overrides[get_llm] = StubLLMProvider
    fastapi_app.dependency_overrides[get_tts] = StubTTSProvider
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def client_without_llm(client):
    """Client whose LLM provider behaves as if the local model is not running."""
    fastapi_app.dependency_overrides[get_llm] = UnavailableLLMProvider
    return client
