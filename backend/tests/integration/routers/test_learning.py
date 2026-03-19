"""Integration tests for learning tool endpoints (T077, T078, T087)."""
import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_app_settings, get_llm, get_storage
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session


_DEFAULT_SETTINGS = AppSettingsRecord(
    llm_model="llama3.1",
    target_language="Spanish",
    native_language="English",
    tts_voice="es_ES-mls-medium",
    suggestion_count=3,
    updated_at=datetime.datetime.now(datetime.timezone.utc),
)


class StubLLMProvider(LLMProvider):
    def __init__(self, response: str = "Grammar OK") -> None:
        self._response = response
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "stub-model"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        yield self._response

    def chat(self, messages: list[ChatMessage]) -> str:
        self.call_count += 1
        return self._response


@pytest.fixture
def client_and_deps(tmp_path: Path):
    db_file = tmp_path / "test_learning.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)
    stub_llm = StubLLMProvider(response="Grammar OK")

    app.dependency_overrides[get_storage] = lambda: storage_instance
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS
    app.dependency_overrides[get_llm] = lambda: stub_llm

    with TestClient(app) as c:
        yield c, storage_instance, stub_llm

    app.dependency_overrides.clear()
    session.close()


def _create_message(storage: SQLiteStorageProvider) -> int:
    """Create a conversation and message, return the message id."""
    conv = storage.create_conversation(
        scenario_id="test-scenario",
        scenario_title="Test",
        target_language="Spanish",
        native_language="English",
        llm_model="llama3.1",
    )
    msg = storage.save_message(conv.id, "user", "Tengo hambre")
    return msg.id


# ---- Grammar ----

def test_grammar_returns_result_and_not_cached(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    response = client.post("/api/learning/grammar", json={"message_id": msg_id, "content": "Tengo hambre"})

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Grammar OK"
    assert data["cached"] is False


def test_grammar_second_call_returns_cached(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    client.post("/api/learning/grammar", json={"message_id": msg_id, "content": "Tengo hambre"})
    assert stub_llm.call_count == 1

    response = client.post("/api/learning/grammar", json={"message_id": msg_id, "content": "Tengo hambre"})

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Grammar OK"
    assert data["cached"] is True
    # LLM was NOT called a second time
    assert stub_llm.call_count == 1


# ---- Translate ----

def test_translate_returns_result(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    response = client.post(
        "/api/learning/translate",
        json={"message_id": msg_id, "content": "Tengo hambre", "native_language": "English"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Grammar OK"
    assert "cached" in data


# ---- Phrasing ----

def test_phrasing_returns_result(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    response = client.post(
        "/api/learning/phrasing",
        json={"message_id": msg_id, "content": "Tengo hambre", "target_language": "Spanish"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Grammar OK"
    assert "cached" in data


# ---- Word Lookup (T087) ----

def test_word_lookup_returns_result(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    response = client.post(
        "/api/learning/word-lookup",
        json={
            "message_id": msg_id,
            "selection": "hambre",
            "target_language": "Spanish",
            "native_language": "English",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Grammar OK"
    assert data["cached"] is False


def test_word_lookup_second_call_uses_cache(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)
    payload = {
        "message_id": msg_id,
        "selection": "hambre",
        "target_language": "Spanish",
        "native_language": "English",
    }

    client.post("/api/learning/word-lookup", json=payload)
    calls_after_first = stub_llm.call_count

    response = client.post("/api/learning/word-lookup", json=payload)

    assert response.status_code == 200
    assert response.json()["cached"] is True
    assert stub_llm.call_count == calls_after_first


def test_word_lookup_different_selections_are_separate(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    client.post(
        "/api/learning/word-lookup",
        json={"message_id": msg_id, "selection": "hambre", "target_language": "Spanish", "native_language": "English"},
    )
    response = client.post(
        "/api/learning/word-lookup",
        json={"message_id": msg_id, "selection": "sed", "target_language": "Spanish", "native_language": "English"},
    )

    assert response.status_code == 200
    assert response.json()["cached"] is False
    assert stub_llm.call_count == 2
