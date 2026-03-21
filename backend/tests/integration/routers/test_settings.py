"""Integration tests for the /api/settings router."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_storage
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session


@pytest.fixture
def client(tmp_path: Path):
    db_file = tmp_path / "test.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)

    app.dependency_overrides[get_storage] = lambda: storage_instance

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    session.close()


def test_get_settings_returns_correct_shape(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "llm_model" in data
    assert "target_language" in data
    assert "native_language" in data
    assert "tts_voice" in data
    assert "suggestion_count" in data
    assert "updated_at" in data


def test_put_settings_updates_suggestion_count(client: TestClient) -> None:
    response = client.put("/api/settings", json={"suggestion_count": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["suggestion_count"] == 3


def test_put_settings_updates_llm_model_only(client: TestClient) -> None:
    # First get baseline
    get_resp = client.get("/api/settings")
    original_target_language = get_resp.json()["target_language"]

    response = client.put("/api/settings", json={"llm_model": "llama3.2"})
    assert response.status_code == 200
    data = response.json()
    assert data["llm_model"] == "llama3.2"
    # Other fields should remain unchanged
    assert data["target_language"] == original_target_language


def test_put_settings_suggestion_count_below_1_returns_422(client: TestClient) -> None:
    response = client.put("/api/settings", json={"suggestion_count": 0})
    assert response.status_code == 422


def test_put_settings_suggestion_count_above_5_returns_422(client: TestClient) -> None:
    response = client.put("/api/settings", json={"suggestion_count": 6})
    assert response.status_code == 422


def test_get_voices_returns_200(client: TestClient) -> None:
    response = client.get("/api/settings/voices")
    assert response.status_code == 200


def test_get_voices_returns_list_with_at_least_one_item(client: TestClient) -> None:
    response = client.get("/api/settings/voices")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_voices_each_item_has_required_fields(client: TestClient) -> None:
    response = client.get("/api/settings/voices")
    data = response.json()
    for item in data:
        assert "key" in item
        assert "display_name" in item
        assert "gender" in item
        assert "locale" in item


def test_get_voices_includes_default_voice(client: TestClient) -> None:
    response = client.get("/api/settings/voices")
    data = response.json()
    keys = [item["key"] for item in data]
    assert "es_ES-davefx-medium" in keys


def test_get_voices_includes_at_least_one_female_voice(client: TestClient) -> None:
    response = client.get("/api/settings/voices")
    data = response.json()
    female_voices = [item for item in data if item["gender"] == "female"]
    assert len(female_voices) >= 1
