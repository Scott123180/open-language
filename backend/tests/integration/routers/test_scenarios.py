"""Integration tests for the /api/scenarios router."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.factory import get_scenario_provider
from app.services.scenario.static import StaticScenarioProvider


@pytest.fixture
def client():
    provider = StaticScenarioProvider()
    app.dependency_overrides[get_scenario_provider] = lambda: provider
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_current_scenario_returns_required_fields(client: TestClient) -> None:
    response = client.get("/api/scenarios/current")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "title" in data
    assert "description" in data
    assert isinstance(data["id"], str)
    assert isinstance(data["title"], str)
    assert isinstance(data["description"], str)


def test_get_current_scenario_returns_known_scenario(client: TestClient) -> None:
    response = client.get("/api/scenarios/current")
    assert response.status_code == 200
    data = response.json()
    # The static provider has 10 scenarios; id must be one of them
    valid_ids = {
        "buy-train-ticket",
        "check-into-hotel",
        "order-at-restaurant",
        "call-doctors-office",
        "ask-for-directions",
        "job-interview",
        "rent-a-car",
        "visit-pharmacy",
        "report-lost-item",
        "board-airplane",
    }
    assert data["id"] in valid_ids


def test_get_next_scenario_returns_different_scenario(client: TestClient) -> None:
    # First get a scenario to use as exclude_id
    first = client.get("/api/scenarios/current").json()
    exclude_id = first["id"]

    response = client.get(f"/api/scenarios/next?exclude_id={exclude_id}")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "title" in data
    assert "description" in data
    # The returned scenario should differ from the excluded one
    assert data["id"] != exclude_id


def test_get_next_scenario_without_exclude_id(client: TestClient) -> None:
    response = client.get("/api/scenarios/next")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "title" in data
    assert "description" in data
