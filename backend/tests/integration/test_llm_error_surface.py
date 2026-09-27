"""T019/T037: a provider failure reaches the learner as the provider's own next step.

JSON endpoints answer 503 with `LLMError.user_message`. SSE endpoints send it as an error frame.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.corrections.models  # noqa: F401
import app.flashcards.models  # noqa: F401
import app.models.app_settings  # noqa: F401
import app.models.conversation  # noqa: F401
import app.models.learning_tool_result  # noqa: F401
import app.models.message  # noqa: F401
import app.models.vocabulary_item  # noqa: F401
from app.config import Settings
from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models.vocabulary_item import VocabularyItem
from app.services.factory import get_llm
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.llm.claude_code import ClaudeCodeLLMProvider
from app.services.llm.claude_code.failures import USER_MESSAGES, ClaudeCodeFailure, FailureKind
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.support.claude_fixtures import load_fixture_lines
from tests.support.engine_overrides import install_session_engine_only, install_session_provider
from tests.support.fake_availability import FakeAvailability, unavailable
from tests.support.fake_ollama_client import ScriptedOllamaClient
from tests.support.fake_speech import override_speech
from tests.support.recording_session_provider import RecordingSessionProvider
from tests.support.scripted_claude_runner import ScriptedClaudeCodeRunner

CUSTOM_MESSAGE = "Custom next step"
UNEXPECTED_ERROR_DETAIL = "An unexpected error occurred. Please try again."


class FailingLLMProvider(LLMProvider):
    """Raises the given exception from every call."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    @property
    def model_name(self) -> str:
        return "failing-model"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        raise self._error
        yield  # pragma: no cover — makes this a generator

    def chat(self, messages: list[ChatMessage]) -> str:
        raise self._error


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def failing_client(db_session):
    """Returns a function that builds a client whose provider raises the given error."""

    def _override_get_db():
        yield db_session

    def _build(error: Exception) -> TestClient:
        fastapi_app.dependency_overrides[get_db] = _override_get_db
        fastapi_app.dependency_overrides[get_llm] = lambda: FailingLLMProvider(error)
        return TestClient(fastapi_app, raise_server_exceptions=False)

    yield _build
    fastapi_app.dependency_overrides.clear()


def _conversation_id(db_session) -> int:
    storage = SQLiteStorageProvider(db_session)
    return storage.create_conversation("buy-train-ticket", "Train", "es", "en", "llama3.1").id


def _message_id(db_session) -> int:
    storage = SQLiteStorageProvider(db_session)
    return storage.save_message(_conversation_id(db_session), "user", "Yo es.").id


def _word_id(db_session) -> int:
    item = VocabularyItem(
        word="hola",
        translation="hello",
        target_language="es",
        native_language="en",
        saved_at=datetime.now(UTC),
        classification="not_practiced",
        manual_override=False,
    )
    db_session.add(item)
    db_session.commit()
    return item.id


def _call_json_endpoint(client: TestClient, endpoint: str, db_session):
    if endpoint == "grammar":
        body = {"message_id": _message_id(db_session), "content": "Yo es."}
        return client.post("/api/learning/grammar", json=body)
    if endpoint == "suggestions":
        return client.post(f"/api/chat/{_conversation_id(db_session)}/suggestions")
    return client.get(f"/api/flashcards/words/{_word_id(db_session)}/info/meanings")


_JSON_ENDPOINTS = ["grammar", "suggestions", "word_info"]


@pytest.mark.parametrize("endpoint", _JSON_ENDPOINTS)
def test_json_endpoint_answers_503_with_the_default_message(failing_client, db_session, endpoint):
    response = _call_json_endpoint(failing_client(LLMError("boom")), endpoint, db_session)

    assert response.status_code == 503
    assert response.json() == {"detail": "The AI is not responding. Please try again."}


@pytest.mark.parametrize("endpoint", _JSON_ENDPOINTS)
def test_json_endpoint_carries_the_providers_own_message(failing_client, db_session, endpoint):
    error = LLMError("boom", user_message=CUSTOM_MESSAGE)

    response = _call_json_endpoint(failing_client(error), endpoint, db_session)

    assert response.status_code == 503
    assert response.json() == {"detail": CUSTOM_MESSAGE}


@pytest.mark.parametrize("endpoint", _JSON_ENDPOINTS)
def test_a_non_llm_failure_is_still_an_unexpected_error(failing_client, db_session, endpoint):
    response = _call_json_endpoint(failing_client(RuntimeError("bug")), endpoint, db_session)

    assert response.status_code == 500
    assert response.json() == {"detail": UNEXPECTED_ERROR_DETAIL}


# --- SSE (T037) -------------------------------------------------------------------------


@pytest.fixture()
def failing_session_client(db_session):
    """Returns a function that builds a client whose every session turn raises `error`."""

    def _override_get_db():
        yield db_session

    def _build(error: LLMError) -> TestClient:
        provider = RecordingSessionProvider()
        provider.errors = [error, error]  # the original attempt and the pool's one retry
        install_session_provider(fastapi_app, provider)
        fastapi_app.dependency_overrides[get_db] = _override_get_db
        override_speech(fastapi_app)
        return TestClient(fastapi_app, raise_server_exceptions=False)

    yield _build
    fastapi_app.dependency_overrides.clear()


def _sse_frames(client: TestClient, url: str, body: dict | None = None) -> list[dict]:
    with client.stream("POST", url, json=body) as response:
        response.read()
        return [
            json.loads(line[len("data: ") :])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]


def _call_sse_endpoint(client: TestClient, endpoint: str, db_session) -> list[dict]:
    if endpoint == "helper":
        body = {
            "message": "How do I say hello?",
            "helper_session_id": "h-err",
            "conversation_id": _conversation_id(db_session),
        }
        return _sse_frames(client, "/api/chat/helper", body)
    conversation_id = _conversation_id(db_session)
    if endpoint == "open":
        return _sse_frames(client, f"/api/chat/{conversation_id}/open")
    body = {"content": "Hola", "input_source": "keyboard"}
    return _sse_frames(client, f"/api/chat/{conversation_id}/message", body)


_SSE_ENDPOINTS = ["open", "message", "helper"]


@pytest.mark.parametrize("endpoint", _SSE_ENDPOINTS)
def test_sse_endpoint_sends_the_providers_own_message(failing_session_client, db_session, endpoint):
    client = failing_session_client(LLMError("boom", user_message=CUSTOM_MESSAGE))

    frames = _call_sse_endpoint(client, endpoint, db_session)

    assert frames[-1] == {"error": CUSTOM_MESSAGE}


@pytest.mark.parametrize("endpoint", _SSE_ENDPOINTS)
def test_sse_endpoint_default_message_is_unchanged(failing_session_client, db_session, endpoint):
    client = failing_session_client(LLMError("boom"))

    frames = _call_sse_endpoint(client, endpoint, db_session)

    assert frames[-1] == {"error": "The AI is not responding. Please try again."}


def test_message_error_follows_the_saved_learner_message(failing_session_client, db_session):
    client = failing_session_client(LLMError("boom"))

    frames = _call_sse_endpoint(client, "message", db_session)

    assert [frame.get("event") for frame in frames] == ["user_message_saved", None]
    assert "error" in frames[1]


# --- Claude failure kinds (T088) --------------------------------------------------------

PRE_FLIGHT_KINDS = {"not_installed", "not_signed_in", "not_on_plan"}
FIXTURE_FOR_KIND = {
    "usage_limit": "rate_limit_rejected.ndjson",
    "model_unavailable": "model_404.ndjson",
    "unexpected_response": "garbage.ndjson",
}
SESSION_RETRY_KINDS = {"unreachable", "unexpected_response"}


def _scripted_claude(kind: str) -> tuple[ClaudeCodeLLMProvider, ScriptedClaudeCodeRunner]:
    """A Claude provider whose every request ends in `kind`."""
    runner = ScriptedClaudeCodeRunner()
    availability = FakeAvailability()
    if kind in PRE_FLIGHT_KINDS:
        availability.answer = unavailable(kind)
    elif kind == "unreachable":
        runner.error = ClaudeCodeFailure(FailureKind.UNREACHABLE, "timed out")
        runner.is_dead = True
    else:
        fixture = FIXTURE_FOR_KIND[kind]
        runner.fixtures = {mode: fixture for mode in ("stream", "json", "schema")}
        runner.session_turns = [load_fixture_lines(fixture), load_fixture_lines(fixture)]
    settings = Settings(_env_file=None)
    return ClaudeCodeLLMProvider(runner, availability, settings, "sonnet", "low"), runner


@pytest.fixture()
def claude_failing_client(db_session):
    def _override_get_db():
        yield db_session

    def _build(kind: str):
        provider, runner = _scripted_claude(kind)
        install_session_provider(fastapi_app, provider)
        fastapi_app.dependency_overrides[get_db] = _override_get_db
        fastapi_app.dependency_overrides[get_llm] = lambda: provider
        override_speech(fastapi_app)
        return TestClient(fastapi_app, raise_server_exceptions=False), runner

    yield _build
    fastapi_app.dependency_overrides.clear()


@pytest.mark.parametrize("kind", [kind.value for kind in FailureKind])
def test_one_shot_claude_failure_is_503_with_its_next_step(claude_failing_client, db_session, kind):
    client, runner = claude_failing_client(kind)

    response = _call_json_endpoint(client, "grammar", db_session)

    assert (response.status_code, response.json()) == (503, {"detail": USER_MESSAGES[kind]})
    assert len(runner.calls) == (0 if kind in PRE_FLIGHT_KINDS else 1)


@pytest.mark.parametrize("kind", [kind.value for kind in FailureKind])
def test_session_claude_failure_is_an_error_frame_with_its_next_step(
    claude_failing_client, db_session, kind
):
    client, runner = claude_failing_client(kind)

    frames = _call_sse_endpoint(client, "message", db_session)

    assert frames[-1] == {"error": USER_MESSAGES[kind]}
    if kind in PRE_FLIGHT_KINDS:
        assert runner.spawns == []
    elif kind in SESSION_RETRY_KINDS:
        assert len(runner.spawns) == 2
    else:
        assert len(runner.spawns) == 1


@pytest.fixture()
def signed_out_claude_selected(db_session, monkeypatch) -> ScriptedOllamaClient:
    """Claude is the saved choice but signed out; Ollama is reachable. Returns Ollama's client."""
    from app.services.llm import registry

    SQLiteStorageProvider(db_session).update_settings(llm_provider="claude", llm_model="sonnet")
    ollama_client = ScriptedOllamaClient()
    signed_out_checker = FakeAvailability(unavailable("not_signed_in"))
    monkeypatch.setattr(registry, "_ollama_client_factory", lambda host: ollama_client)
    monkeypatch.setattr(registry, "ClaudeCodeAvailability", lambda *_: signed_out_checker)

    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    override_speech(fastapi_app)
    install_session_engine_only(fastapi_app)
    yield ollama_client
    fastapi_app.dependency_overrides.clear()


def test_a_signed_out_claude_never_falls_back_to_ollama(signed_out_claude_selected, db_session):
    """FR-029: with Claude selected, a Claude failure is reported, never silently rerouted."""
    client = TestClient(fastapi_app, raise_server_exceptions=False)

    grammar = _call_json_endpoint(client, "grammar", db_session)
    frames = _call_sse_endpoint(client, "message", db_session)

    assert grammar.json() == {"detail": USER_MESSAGES["not_signed_in"]}
    assert frames[-1] == {"error": USER_MESSAGES["not_signed_in"]}
    assert signed_out_claude_selected.chat_calls == []
    assert signed_out_claude_selected.generate_calls == []
