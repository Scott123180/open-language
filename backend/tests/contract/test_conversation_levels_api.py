"""Contract for GET /api/settings/conversation-levels (005 contracts/api.md §1)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.conversation_levels import ConversationLevel
from app.main import app
from app.services.factory import get_storage
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session

LEVEL_KEYS = {"level_id", "label", "cefr_label", "description"}


@pytest.fixture
def client(tmp_path: Path):
    session, _engine = make_test_session(str(tmp_path / "contract.db"))
    app.dependency_overrides[get_storage] = lambda: SQLiteStorageProvider(session)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    session.close()


def _levels(client: TestClient) -> list[dict]:
    response = client.get("/api/settings/conversation-levels")
    assert response.status_code == 200
    return response.json()


def test_lists_exactly_the_four_levels_in_declaration_order(client):
    assert [item["level_id"] for item in _levels(client)] == [
        level.value for level in ConversationLevel
    ]


def test_each_item_carries_only_the_public_fields(client):
    assert all(set(item) == LEVEL_KEYS for item in _levels(client))


def test_every_listed_level_is_accepted_by_put_settings(client):
    listed = {item["level_id"] for item in _levels(client)}

    assert listed == {level.value for level in ConversationLevel}
    for level_id in listed:
        response = client.put("/api/settings", json={"conversation_level": level_id})
        assert (response.status_code, response.json()["conversation_level"]) == (200, level_id)


def test_beginner_is_described_in_plain_language(client):
    beginner = _levels(client)[0]

    assert beginner == {
        "level_id": "beginner",
        "label": "Beginner",
        "cefr_label": "A1",
        "description": "Very short, simple sentences — like talking with a young child.",
    }
