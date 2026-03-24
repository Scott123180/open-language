"""Integration tests for vocabulary endpoints (T088, T089)."""

import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_app_settings, get_storage
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session

_DEFAULT_SETTINGS = AppSettingsRecord(
    llm_model="llama3.1",
    target_language="Spanish",
    native_language="English",
    tts_voice="es_ES-mls-medium",
    suggestion_count=3,
    whisper_model="base",
    updated_at=datetime.datetime.now(datetime.UTC),
)


@pytest.fixture
def client_and_storage(tmp_path: Path):
    db_file = tmp_path / "test_vocab.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)

    app.dependency_overrides[get_storage] = lambda: storage_instance
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS

    with TestClient(app) as c:
        yield c, storage_instance

    app.dependency_overrides.clear()
    session.close()


def test_save_vocabulary_item_and_retrieve(client_and_storage) -> None:
    client, _storage = client_and_storage

    response = client.post(
        "/api/vocabulary",
        json={"word": "perro", "translation": "dog"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["word"] == "perro"
    assert data["translation"] == "dog"

    list_response = client.get("/api/vocabulary")
    assert list_response.status_code == 200
    items = list_response.json()
    assert any(item["word"] == "perro" for item in items)


def test_save_vocabulary_duplicate_merges_and_flags(client_and_storage) -> None:
    client, _storage = client_and_storage

    first = client.post(
        "/api/vocabulary",
        json={"word": "gato", "translation": "cat"},
    )
    assert first.status_code == 201
    assert first.json()["already_saved"] is False

    second = client.post(
        "/api/vocabulary",
        json={"word": "gato", "translation": "cat"},
    )
    assert second.status_code == 200
    assert second.json()["already_saved"] is True

    list_response = client.get("/api/vocabulary")
    items = list_response.json()
    gato_items = [i for i in items if i["word"] == "gato"]
    assert len(gato_items) == 1


def test_list_vocabulary_most_recently_saved_first(client_and_storage) -> None:
    client, _storage = client_and_storage

    client.post("/api/vocabulary", json={"word": "uno", "translation": "one"})
    client.post("/api/vocabulary", json={"word": "dos", "translation": "two"})
    client.post("/api/vocabulary", json={"word": "tres", "translation": "three"})

    list_response = client.get("/api/vocabulary")
    assert list_response.status_code == 200
    items = list_response.json()
    words = [i["word"] for i in items]
    assert words.index("tres") < words.index("dos") < words.index("uno")
