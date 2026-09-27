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
    target_language="es",
    native_language="en",
    suggestion_count=3,
    whisper_model="base",
    updated_at=datetime.datetime.now(datetime.UTC),
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
        target_language="es",
        native_language="en",
        llm_model="llama3.1",
    )
    msg = storage.save_message(conv.id, "user", "Tengo hambre")
    return msg.id


# ---- Grammar ----


def test_grammar_returns_result_and_not_cached(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    response = client.post(
        "/api/learning/grammar", json={"message_id": msg_id, "content": "Tengo hambre"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Grammar OK"
    assert data["cached"] is False


def test_grammar_second_call_returns_cached(client_and_deps) -> None:
    client, storage, stub_llm = client_and_deps
    msg_id = _create_message(storage)

    client.post("/api/learning/grammar", json={"message_id": msg_id, "content": "Tengo hambre"})
    assert stub_llm.call_count == 1

    response = client.post(
        "/api/learning/grammar", json={"message_id": msg_id, "content": "Tengo hambre"}
    )

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
        json={
            "message_id": msg_id,
            "selection": "hambre",
            "target_language": "Spanish",
            "native_language": "English",
        },
    )
    response = client.post(
        "/api/learning/word-lookup",
        json={
            "message_id": msg_id,
            "selection": "sed",
            "target_language": "Spanish",
            "native_language": "English",
        },
    )

    assert response.status_code == 200
    assert response.json()["cached"] is False
    assert stub_llm.call_count == 2


# ---- 006: languages come from the message's conversation (T042) ----

REQUESTS = {
    "grammar": lambda message_id: {
        "message_id": message_id,
        "content": "Ich habe Hunger",
        "preceding_message": "Guten Tag",
    },
    "translate": lambda message_id: {"message_id": message_id, "content": "Ich habe Hunger"},
    "phrasing": lambda message_id: {"message_id": message_id, "content": "Ich habe Hunger"},
    "word-lookup": lambda message_id: {
        "message_id": message_id,
        "selection": "Hunger",
        "sentence_context": "Ich habe Hunger",
    },
}
NAMES_IN_PROMPT = {
    "grammar": ("English",),
    "translate": ("English",),
    "phrasing": ("German",),
    "word-lookup": ("German", "English"),
}


class PromptRecordingLLM(StubLLMProvider):
    def __init__(self) -> None:
        super().__init__(response="OK")
        self.prompts: list[str] = []

    def chat(self, messages: list[ChatMessage]) -> str:
        self.prompts.append(messages[-1].content)
        return super().chat(messages)


@pytest.fixture
def recording_llm():
    llm = PromptRecordingLLM()
    app.dependency_overrides[get_llm] = lambda: llm
    return llm


def _german_message(storage: SQLiteStorageProvider) -> int:
    conv = storage.create_conversation("s", "S", "de", "en", "llama3.1")
    return storage.save_message(conv.id, "assistant", "Ich habe Hunger").id


@pytest.mark.parametrize("tool", list(REQUESTS))
def test_the_trimmed_request_builds_its_prompt_from_the_conversation(
    client_and_deps, recording_llm, tool
) -> None:
    client, storage, _ = client_and_deps
    message_id = _german_message(storage)

    response = client.post(f"/api/learning/{tool}", json=REQUESTS[tool](message_id))

    assert response.status_code == 200, response.text
    assert all(name in recording_llm.prompts[-1] for name in NAMES_IN_PROMPT[tool])


@pytest.mark.parametrize("tool", list(REQUESTS))
def test_an_unknown_message_is_404(client_and_deps, tool) -> None:
    client, _storage, stub_llm = client_and_deps

    response = client.post(f"/api/learning/{tool}", json=REQUESTS[tool](9999))

    assert (response.status_code, response.json()) == (404, {"detail": "Message not found"})
    assert stub_llm.call_count == 0


@pytest.mark.parametrize("tool", list(REQUESTS))
def test_client_sent_languages_are_ignored(client_and_deps, recording_llm, tool) -> None:
    client, storage, _ = client_and_deps
    body = {**REQUESTS[tool](_german_message(storage)), "target_language": "fr"}
    body["native_language"] = "fr"

    response = client.post(f"/api/learning/{tool}", json=body)

    assert response.status_code == 200, response.text
    assert "fr" not in recording_llm.prompts[-1].split()
    assert all(name in recording_llm.prompts[-1] for name in NAMES_IN_PROMPT[tool])


@pytest.mark.parametrize("tool", list(REQUESTS))
def test_a_second_request_is_served_from_the_cache(client_and_deps, tool) -> None:
    client, storage, stub_llm = client_and_deps
    body = REQUESTS[tool](_german_message(storage))

    first = client.post(f"/api/learning/{tool}", json=body).json()
    second = client.post(f"/api/learning/{tool}", json=body).json()

    assert (first["cached"], second["cached"], stub_llm.call_count) == (False, True, 1)


def test_the_phrasing_cache_key_still_carries_the_level(client_and_deps) -> None:
    from dataclasses import replace

    client, storage, stub_llm = client_and_deps
    app.dependency_overrides[get_app_settings] = lambda: replace(
        _DEFAULT_SETTINGS, conversation_level="beginner"
    )
    body = REQUESTS["phrasing"](_german_message(storage))

    client.post("/api/learning/phrasing", json=body)
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS
    natural = client.post("/api/learning/phrasing", json=body).json()

    assert (natural["cached"], stub_llm.call_count) == (False, 2)
