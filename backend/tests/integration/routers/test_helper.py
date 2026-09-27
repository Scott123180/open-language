"""Integration tests for POST /api/chat/helper SSE endpoint (T103)."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_helper_sessions, get_llm, get_storage
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session
from tests.support.engine_overrides import override_conversation_engine

CONVERSATION_ID = 1


class StubLLMProvider(LLMProvider):
    def __init__(self, response: str) -> None:
        self._response = response
        self.received_messages: list[list[ChatMessage]] = []

    @property
    def model_name(self) -> str:
        return "stub-model"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        self.received_messages.append(list(messages))
        yield self._response

    def chat(self, messages: list[ChatMessage]) -> str:
        self.received_messages.append(list(messages))
        return self._response


def _parse_sse(raw: str) -> list[dict]:
    events = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


@pytest.fixture(autouse=True)
def clear_helper_sessions():
    """Ensure helper session state is clean for each test."""
    store = get_helper_sessions()
    store.clear()
    yield
    store.clear()


@pytest.fixture
def storage(tmp_path: Path):
    session, _engine = make_test_session(str(tmp_path / "helper.db"))
    storage = SQLiteStorageProvider(session)
    conversation = storage.create_conversation("s", "S", "es", "en", "llama3.1")
    assert conversation.id == CONVERSATION_ID
    yield storage
    session.close()


@pytest.fixture
def client_and_llm(storage):
    stub_llm = StubLLMProvider(response="Hola means hello")

    app.dependency_overrides[get_llm] = lambda: stub_llm
    app.dependency_overrides[get_storage] = lambda: storage
    override_conversation_engine(app, stub_llm)

    with TestClient(app) as c:
        yield c, stub_llm

    app.dependency_overrides.clear()


def test_helper_streams_tokens_and_done(client_and_llm) -> None:
    client, _llm = client_and_llm

    with client.stream(
        "POST",
        "/api/chat/helper",
        json={
            "message": "How do I say hello?",
            "helper_session_id": "abc123",
            "conversation_id": CONVERSATION_ID,
        },
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        response.read()
        raw = response.text

    events = _parse_sse(raw)
    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if e.get("done") is True]

    assert len(token_events) >= 1
    assert len(done_events) == 1
    assert done_events[0] == events[-1]


def test_helper_second_call_preserves_session_context(client_and_llm) -> None:
    client, stub_llm = client_and_llm
    session_id = "session-ctx-test"

    with client.stream(
        "POST",
        "/api/chat/helper",
        json={
            "message": "How do I say hello?",
            "helper_session_id": session_id,
            "conversation_id": CONVERSATION_ID,
        },
    ) as r:
        r.read()

    with client.stream(
        "POST",
        "/api/chat/helper",
        json={
            "message": "And goodbye?",
            "helper_session_id": session_id,
            "conversation_id": CONVERSATION_ID,
        },
    ) as r:
        r.read()

    assert len(stub_llm.received_messages) == 2

    first_call_messages = stub_llm.received_messages[0]
    second_call_messages = stub_llm.received_messages[1]

    # Second call should have more messages (session history carried over)
    assert len(second_call_messages) > len(first_call_messages)

    # Verify previous user message and assistant response appear in the second call
    roles_and_contents = [(m.role, m.content) for m in second_call_messages]
    assert ("user", "How do I say hello?") in roles_and_contents
    assert ("assistant", "Hola means hello") in roles_and_contents
    assert ("user", "And goodbye?") in roles_and_contents


def test_helper_token_content_is_correct(client_and_llm) -> None:
    client, _llm = client_and_llm

    with client.stream(
        "POST",
        "/api/chat/helper",
        json={
            "message": "How do I say hello?",
            "helper_session_id": "token-test",
            "conversation_id": CONVERSATION_ID,
        },
    ) as response:
        response.read()
        raw = response.text

    events = _parse_sse(raw)
    tokens = "".join(e["token"] for e in events if "token" in e)
    assert tokens == "Hola means hello"


# --- 006: the helper names its conversation's languages (T043) -------------------------


def _ask(client, conversation_id: int, session_id: str = "lang-test"):
    body = {"message": "How do I say hello?", "helper_session_id": session_id}
    return client.post("/api/chat/helper", json={**body, "conversation_id": conversation_id})


def _standing_prompt(stub_llm: StubLLMProvider) -> str:
    return stub_llm.received_messages[-1][0].content


def test_a_german_conversation_names_german_and_english(client_and_llm, storage) -> None:
    client, stub_llm = client_and_llm
    german = storage.create_conversation("s", "S", "de", "en", "llama3.1")

    _ask(client, german.id)

    prompt = _standing_prompt(stub_llm)
    assert "German" in prompt and "English" in prompt


def test_an_unknown_conversation_is_404(client_and_llm) -> None:
    client, stub_llm = client_and_llm

    response = _ask(client, 9999)

    assert (response.status_code, response.json()) == (404, {"detail": "Conversation not found"})
    assert stub_llm.received_messages == []


def test_the_level_rules_are_still_appended(client_and_llm, storage) -> None:
    client, stub_llm = client_and_llm
    _ask(client, CONVERSATION_ID, "natural")
    natural = _standing_prompt(stub_llm)
    storage.update_settings(conversation_level="beginner")

    _ask(client, CONVERSATION_ID, "beginner")

    beginner = _standing_prompt(stub_llm)
    assert beginner.startswith(natural) and beginner != natural
