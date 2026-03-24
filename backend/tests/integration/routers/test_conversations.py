"""Integration tests for the /api/conversations router."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_app_settings, get_scenario_provider, get_storage
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import AppSettingsRecord
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session

_VALID_SCENARIO_ID = "buy-train-ticket"

_DEFAULT_SETTINGS = AppSettingsRecord(
    llm_model="llama3.1",
    target_language="es",
    native_language="en",
    tts_voice="es_ES-mls-medium",
    suggestion_count=3,
    whisper_model="base",
    updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
)


@pytest.fixture
def client(tmp_path: Path):
    db_file = tmp_path / "test.db"
    session, _engine = make_test_session(str(db_file))
    storage_instance = SQLiteStorageProvider(session)

    app.dependency_overrides[get_scenario_provider] = lambda: StaticScenarioProvider()
    app.dependency_overrides[get_storage] = lambda: storage_instance
    app.dependency_overrides[get_app_settings] = lambda: _DEFAULT_SETTINGS

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    session.close()


def test_create_conversation_returns_201_with_correct_shape(client: TestClient) -> None:
    response = client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], int)
    assert data["scenario_id"] == _VALID_SCENARIO_ID
    assert "scenario_title" in data
    assert data["target_language"] == "es"
    assert data["native_language"] == "en"
    assert data["status"] == "active"
    assert "started_at" in data
    assert data["ended_at"] is None
    assert data["llm_model"] == "llama3.1"


def test_create_conversation_with_invalid_scenario_returns_404(client: TestClient) -> None:
    response = client.post("/api/conversations", json={"scenario_id": "non-existent-scenario"})
    assert response.status_code == 404
    assert "detail" in response.json()


def test_create_conversation_stores_scenario_title(client: TestClient) -> None:
    response = client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})
    assert response.status_code == 201
    data = response.json()
    assert data["scenario_title"] == "Buy a Train Ticket"


def test_list_conversations_returns_created_conversation(client: TestClient) -> None:
    client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})
    response = client.get("/api/conversations")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert items[0]["scenario_id"] == _VALID_SCENARIO_ID


# T108 — PATCH sets ended_at to non-null timestamp
def test_patch_status_completed_sets_ended_at(client: TestClient) -> None:
    create_resp = client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/api/conversations/{conv_id}", json={"status": "completed"})
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["status"] == "completed"
    assert data["ended_at"] is not None


# T109 — GET /api/conversations returns list ordered by started_at DESC with correct shape
def test_list_conversations_ordered_newest_first_with_correct_shape(client: TestClient) -> None:
    import time

    client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})
    time.sleep(0.01)
    client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})

    response = client.get("/api/conversations")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2

    # Verify shape of each item
    for item in items:
        assert "id" in item
        assert "scenario_title" in item
        assert "status" in item
        assert "started_at" in item
        assert "ended_at" in item

    # Verify descending order by started_at
    from datetime import datetime

    dates = [datetime.fromisoformat(item["started_at"].replace("Z", "+00:00")) for item in items]
    assert dates == sorted(dates, reverse=True)


# T110 — GET /api/conversations/{id}/messages returns messages in created_at ASC order
def test_get_conversation_messages_ordered_asc(client: TestClient) -> None:
    import time

    # Create conversation via API first
    create_resp = client.post("/api/conversations", json={"scenario_id": _VALID_SCENARIO_ID})
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    # Access storage directly to save two messages with a time gap
    # We need to reach the same storage the client uses, so patch via the override
    storage_instance = client.app.dependency_overrides[get_storage]()
    storage_instance.save_message(conv_id, "user", "First message", "keyboard")
    time.sleep(0.05)
    storage_instance.save_message(conv_id, "assistant", "Second message")

    response = client.get(f"/api/conversations/{conv_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 2

    from datetime import datetime

    dates = [datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")) for m in messages]
    assert dates[0] <= dates[1]
    assert messages[0]["content"] == "First message"
    assert messages[1]["content"] == "Second message"
