"""Integration tests for POST /api/chat/{id}/message SSE endpoint."""

import datetime
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

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
from tests.integration.conversation_levels.level_harness import wait_until
from tests.support.engine_overrides import override_conversation_engine
from tests.support.fake_speech import override_speech
from tests.support.scratch_database import make_sessions

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


class _SessionPerCall:
    """Storage whose every call opens its own session, as each request's `get_db` does.

    The reply is spoken on a worker thread that writes its audio path with the request's
    storage after the response has gone, so one session shared with the test would race.
    """

    def __init__(self, sessions: sessionmaker, opened: list[Session]) -> None:
        self._sessions = sessions
        self._opened = opened

    def __call__(self) -> SQLiteStorageProvider:
        self._opened.append(self._sessions())
        return SQLiteStorageProvider(self._opened[-1])

    def __getattr__(self, name: str):
        return getattr(self(), name)


@pytest.fixture
def client_and_storage(tmp_path: Path):
    opened: list[Session] = []
    storage = _SessionPerCall(make_sessions(tmp_path / "test.db"), opened)

    stub_llm = StubLLMProvider(tokens=["Buenos", " dias"])

    app.dependency_overrides[get_scenario_provider] = lambda: StaticScenarioProvider()
    app.dependency_overrides[get_storage] = storage
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS
    app.dependency_overrides[get_llm] = lambda: stub_llm
    override_conversation_engine(app, stub_llm)
    override_speech(app)

    with TestClient(app) as c:
        yield c, storage

    app.dependency_overrides.clear()
    for session in opened:
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


def test_send_message_streams_user_message_saved_first(client_and_storage) -> None:
    client, _storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream(
        "POST",
        f"/api/chat/{conv_id}/message",
        json={"content": "Hola", "input_source": "keyboard"},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    assert len(events) >= 1
    first = events[0]
    assert first.get("event") == "user_message_saved"
    assert "message_id" in first
    assert isinstance(first["message_id"], int)


def test_send_message_streams_token_events(client_and_storage) -> None:
    client, _storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream(
        "POST",
        f"/api/chat/{conv_id}/message",
        json={"content": "Hola", "input_source": "keyboard"},
    ) as response:
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    token_events = [e for e in events if "token" in e]
    assert len(token_events) >= 1
    combined = "".join(e["token"] for e in token_events)
    assert combined == "Buenos dias"


def test_send_message_done_event_is_last(client_and_storage) -> None:
    client, _storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream(
        "POST",
        f"/api/chat/{conv_id}/message",
        json={"content": "Hola", "input_source": "keyboard"},
    ) as response:
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    assert events[-1].get("done") is True
    assert "message_id" in events[-1]
    assert isinstance(events[-1]["message_id"], int)


def test_send_message_done_event_contains_assistant_message_id(client_and_storage) -> None:
    client, storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream(
        "POST",
        f"/api/chat/{conv_id}/message",
        json={"content": "Hola", "input_source": "keyboard"},
    ) as response:
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    done_event = events[-1]
    assert done_event.get("done") is True

    # Verify the message_id corresponds to a real assistant message
    assistant_msg_id = done_event["message_id"]
    msg = storage.get_message(assistant_msg_id)
    assert msg is not None
    assert msg.role == "assistant"
    assert msg.content == "Buenos dias"


def test_send_message_unknown_conversation_returns_404(client_and_storage) -> None:
    client, _storage = client_and_storage
    response = client.post(
        "/api/chat/99999/message",
        json={"content": "Hola", "input_source": "keyboard"},
    )
    assert response.status_code == 404


def test_send_message_user_message_persisted(client_and_storage) -> None:
    client, storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream(
        "POST",
        f"/api/chat/{conv_id}/message",
        json={"content": "Buenos dias", "input_source": "keyboard"},
    ) as response:
        response.read()
        _raw = response.text  # noqa: F841

    messages = storage.get_messages(conv_id)
    user_messages = [m for m in messages if m.role == "user"]
    assert any(m.content == "Buenos dias" for m in user_messages)


def test_send_message_event_order(client_and_storage) -> None:
    """user_message_saved → token(s) → done."""
    client, _storage = client_and_storage
    conv_id = _create_conversation(client)

    with client.stream(
        "POST",
        f"/api/chat/{conv_id}/message",
        json={"content": "Hola", "input_source": "keyboard"},
    ) as response:
        response.read()
        raw = response.text

    events = _parse_sse_lines(raw)
    assert events[0].get("event") == "user_message_saved"
    assert events[-1].get("done") is True
    middle = events[1:-1]
    assert all("token" in e for e in middle)


# --- 006: replies are spoken in the conversation's language (T046) ----------------------


@pytest.fixture
def speaking_client(tmp_path: Path):
    """Returns a builder: `speaking_client(installed=…)` → (client, storage, tts builder)."""
    opened: list[Session] = []
    storage = _SessionPerCall(make_sessions(tmp_path / "speaking.db"), opened)
    stub_llm = StubLLMProvider(tokens=["Guten", " Tag"])
    app.dependency_overrides[get_storage] = storage
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS
    override_conversation_engine(app, stub_llm)
    clients: list[TestClient] = []

    def build(installed=None):
        builder = override_speech(app, installed=installed)
        clients.append(TestClient(app))
        return clients[-1].__enter__(), storage, builder

    yield build
    for client in clients:
        client.__exit__(None, None, None)
    app.dependency_overrides.clear()
    for session in opened:
        session.close()


def _send_in_german(client: TestClient, storage: SQLiteStorageProvider) -> int:
    conversation = storage.create_conversation("buy-train-ticket", "S", "de", "en", "llama3.1")
    with client.stream(
        "POST", f"/api/chat/{conversation.id}/message", json={"content": "Hallo"}
    ) as response:
        response.read()
    return _parse_sse_lines(response.text)[-1]["message_id"]


def test_a_german_reply_is_synthesised_with_a_german_voice(speaking_client) -> None:
    client, storage, builder = speaking_client()

    _send_in_german(client, storage)

    wait_until(lambda: builder.synthesized)
    assert builder.voice_keys == ["de_DE-thorsten-medium"]


def test_without_the_german_voice_the_reply_streams_and_nothing_is_spoken(
    speaking_client, caplog
) -> None:
    client, storage, builder = speaking_client(installed={"es_ES-davefx-medium"})

    with caplog.at_level("WARNING", logger="app.routers.chat"):
        reply_id = _send_in_german(client, storage)

    assert storage.get_message(reply_id).content == "Guten Tag"
    assert builder.synthesized == []
    assert storage.get_message(reply_id).tts_audio_path is None
    warnings = [r for r in caplog.records if r.name == "app.routers.chat"]
    assert len(warnings) == 1
    assert "German" in warnings[0].getMessage()
    assert "Guten Tag" not in warnings[0].getMessage()
