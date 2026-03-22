"""Integration tests for POST /api/chat/{id}/suggestions endpoint (T097)."""
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
    suggestion_count=1,
    whisper_model="base",
    updated_at=datetime.datetime.now(datetime.timezone.utc),
)


class StubLLMProvider(LLMProvider):
    def __init__(self, response: str) -> None:
        self._response = response

    @property
    def model_name(self) -> str:
        return "stub-model"

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        yield self._response

    def chat(self, messages: list[ChatMessage]) -> str:
        return self._response


def _make_client_fixture(tmp_path: Path, settings: AppSettingsRecord, llm_response: str):
    db_file = tmp_path / "test_suggestions.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)
    stub_llm = StubLLMProvider(response=llm_response)

    app.dependency_overrides[get_storage] = lambda: storage_instance
    app.dependency_overrides[get_app_settings] = lambda: settings
    app.dependency_overrides[get_llm] = lambda: stub_llm

    return session, storage_instance, stub_llm


@pytest.fixture
def client_and_storage(tmp_path: Path):
    session, storage_instance, stub_llm = _make_client_fixture(
        tmp_path,
        _DEFAULT_SETTINGS,
        "1. Buenas tardes\n2. Hola\n",
    )

    with TestClient(app) as c:
        yield c, storage_instance, stub_llm

    app.dependency_overrides.clear()
    session.close()


def _create_conversation(storage: SQLiteStorageProvider) -> int:
    conv = storage.create_conversation(
        scenario_id="test-scenario",
        scenario_title="Test",
        target_language="Spanish",
        native_language="English",
        llm_model="llama3.1",
    )
    return conv.id


def test_suggestions_returns_list_with_suggestion_count(client_and_storage) -> None:
    client, storage, _llm = client_and_storage
    conv_id = _create_conversation(storage)

    response = client.post(f"/api/chat/{conv_id}/suggestions")

    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    assert len(data["suggestions"]) == _DEFAULT_SETTINGS.suggestion_count


def test_suggestions_parses_numbered_lines(tmp_path: Path) -> None:
    settings = AppSettingsRecord(
        llm_model="llama3.1",
        target_language="Spanish",
        native_language="English",
        tts_voice="es_ES-mls-medium",
        suggestion_count=2,
    whisper_model="base",
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    session, storage_instance, _stub_llm = _make_client_fixture(
        tmp_path, settings, "1. Buenas tardes\n2. Hola\n"
    )

    with TestClient(app) as client:
        conv_id = _create_conversation(storage_instance)
        response = client.post(f"/api/chat/{conv_id}/suggestions")

    app.dependency_overrides.clear()
    session.close()

    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) == 2
    assert "Buenas tardes" in data["suggestions"]
    assert "Hola" in data["suggestions"]


def test_suggestions_unknown_conversation_returns_404(client_and_storage) -> None:
    client, _storage, _llm = client_and_storage

    response = client.post("/api/chat/99999/suggestions")

    assert response.status_code == 404
