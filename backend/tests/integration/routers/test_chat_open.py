"""Integration tests for POST /api/chat/{id}/open SSE endpoint."""

import datetime
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import (
    get_app_settings,
    get_llm,
    get_scenario_provider,
    get_storage,
)
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session
from tests.support.engine_overrides import override_conversation_engine
from tests.support.fake_speech import override_speech

_DEFAULT_SETTINGS = AppSettingsRecord(
    llm_model="llama3.1",
    target_language="es",
    native_language="en",
    suggestion_count=3,
    whisper_model="base",
    updated_at=datetime.datetime.now(datetime.UTC),
)

_VALID_SCENARIO_ID = "buy-train-ticket"


class StubLLMProvider(LLMProvider):
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    @property
    def model_name(self) -> str:
        return "stub-model"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        yield from self._tokens

    def chat(self, messages: list[ChatMessage]) -> str:
        return "".join(self._tokens)


@pytest.fixture
def client_and_storage(tmp_path: Path):
    db_file = tmp_path / "test.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)

    stub_llm = StubLLMProvider(tokens=["Hello", " world"])

    app.dependency_overrides[get_scenario_provider] = lambda: StaticScenarioProvider()
    app.dependency_overrides[get_storage] = lambda: storage_instance
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS
    app.dependency_overrides[get_llm] = lambda: stub_llm
    override_conversation_engine(app, stub_llm)
    override_speech(app)

    with TestClient(app) as c:
        yield c, storage_instance

    app.dependency_overrides.clear()
    session.close()


def _create_conversation(client: TestClient) -> int:
    response = client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})
    assert response.status_code == 201
    return response.json()["id"]


def _parse_sse_lines(raw_text: str) -> list[dict]:
    """Parse SSE response text into a list of parsed JSON dicts."""
    events = []
    for line in raw_text.splitlines():
        if line.startswith("data: "):
            payload = line[len("data: ") :]
            events.append(json.loads(payload))
    return events


def test_open_chat_streams_tokens_then_done(client_and_storage) -> None:
    client, _storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream("POST", f"/api/chat/{conv_id}/open") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    assert len(events) >= 2

    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if e.get("done") is True]

    assert len(token_events) >= 1
    assert len(done_events) == 1
    assert "message_id" in done_events[0]
    assert isinstance(done_events[0]["message_id"], int)


def test_open_chat_tokens_contain_expected_content(client_and_storage) -> None:
    client, _storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream("POST", f"/api/chat/{conv_id}/open") as response:
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    token_events = [e for e in events if "token" in e]
    combined = "".join(e["token"] for e in token_events)
    assert combined == "Hello world"


def test_open_chat_done_event_is_last(client_and_storage) -> None:
    client, _storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream("POST", f"/api/chat/{conv_id}/open") as response:
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    assert events[-1].get("done") is True


def test_open_chat_nonexistent_conversation_returns_404(client_and_storage) -> None:
    client, _storage = client_and_storage
    response = client.post("/api/chat/99999/open")
    assert response.status_code == 404
