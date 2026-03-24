"""Integration tests for POST /api/chat/helper SSE endpoint (T103)."""

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.chat import _helper_sessions
from app.services.factory import get_llm
from app.services.llm.base import ChatMessage, LLMProvider


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
    _helper_sessions.clear()
    yield
    _helper_sessions.clear()


@pytest.fixture
def client_and_llm():
    stub_llm = StubLLMProvider(response="Hola means hello")

    app.dependency_overrides[get_llm] = lambda: stub_llm

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
            "target_language": "Spanish",
            "native_language": "English",
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
            "target_language": "Spanish",
            "native_language": "English",
        },
    ) as r:
        r.read()

    with client.stream(
        "POST",
        "/api/chat/helper",
        json={
            "message": "And goodbye?",
            "helper_session_id": session_id,
            "target_language": "Spanish",
            "native_language": "English",
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
            "target_language": "Spanish",
            "native_language": "English",
        },
    ) as response:
        response.read()
        raw = response.text

    events = _parse_sse(raw)
    tokens = "".join(e["token"] for e in events if "token" in e)
    assert tokens == "Hola means hello"
