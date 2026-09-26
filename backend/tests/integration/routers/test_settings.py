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
    assert "whisper_model" in data
    assert "updated_at" in data


def test_get_settings_returns_default_whisper_model(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["whisper_model"] == "base"


def test_put_settings_updates_whisper_model(client: TestClient) -> None:
    response = client.put("/api/settings", json={"whisper_model": "small"})
    assert response.status_code == 200
    assert response.json()["whisper_model"] == "small"


def test_put_settings_invalid_whisper_model_returns_422(client: TestClient) -> None:
    response = client.put("/api/settings", json={"whisper_model": "large-v3"})
    assert response.status_code == 422


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
        assert "quality" in item
        assert "speaking_rate" in item


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


def test_get_settings_defaults_correction_mode_to_off(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["correction_mode"] == "off"


def test_put_settings_round_trips_correction_mode(client: TestClient) -> None:
    put_response = client.put("/api/settings", json={"correction_mode": "strict"})
    assert put_response.status_code == 200
    assert put_response.json()["correction_mode"] == "strict"

    assert client.get("/api/settings").json()["correction_mode"] == "strict"


def test_put_settings_accepts_gentle_correction_mode(client: TestClient) -> None:
    response = client.put("/api/settings", json={"correction_mode": "gentle"})
    assert response.status_code == 200
    assert response.json()["correction_mode"] == "gentle"


def test_put_settings_invalid_correction_mode_returns_422(client: TestClient) -> None:
    response = client.put("/api/settings", json={"correction_mode": "harsh"})
    assert response.status_code == 422


def test_put_settings_leaves_correction_mode_untouched_when_omitted(client: TestClient) -> None:
    client.put("/api/settings", json={"correction_mode": "gentle"})

    response = client.put("/api/settings", json={"suggestion_count": 2})

    assert response.status_code == 200
    assert response.json()["correction_mode"] == "gentle"


def test_get_settings_reports_ollama_at_low_effort_on_a_fresh_db(client: TestClient) -> None:
    data = client.get("/api/settings").json()

    assert data["llm_provider"] == "ollama"
    assert data["llm_effort"] == "low"


def test_get_settings_keeps_every_existing_field(client: TestClient) -> None:
    data = client.get("/api/settings").json()

    assert {
        "llm_model",
        "target_language",
        "native_language",
        "tts_voice",
        "suggestion_count",
        "whisper_model",
        "correction_mode",
        "updated_at",
    } <= set(data)


# --- 004: provider selection (T068) ---------------------------------------------------


@pytest.fixture
def claude_availability():
    from tests.support.fake_availability import FakeAvailability

    availability = FakeAvailability()
    from app.services.factory import get_availability_checkers
    from app.services.llm.availability import AlwaysAvailable

    app.dependency_overrides[get_availability_checkers] = lambda: {
        "ollama": AlwaysAvailable(),
        "claude": availability,
    }
    return availability


def _make_claude_unavailable(availability, reason: str) -> str:
    from tests.support.fake_availability import unavailable

    availability.answer = unavailable(reason)
    return availability.answer.message


OLLAMA_ENTRY = {
    "provider_id": "ollama",
    "display_name": "Ollama (local)",
    "is_local": True,
    "models": [
        {"model_id": "llama3.1:8b", "label": "llama3.1:8b"},
        {"model_id": "llama3.2", "label": "llama3.2"},
        {"model_id": "mistral", "label": "mistral"},
    ],
    "default_model": "llama3.1:8b",
    "effort_levels": [],
    "default_effort": None,
    "is_available": True,
    "unavailable_reason": None,
    "unavailable_message": None,
}


def test_llm_providers_lists_the_catalogue_in_order(client, claude_availability) -> None:
    body = client.get("/api/settings/llm-providers").json()

    assert [p["provider_id"] for p in body] == ["ollama", "claude"]
    ollama, claude = body
    assert ollama == OLLAMA_ENTRY
    assert claude["default_model"] == "sonnet"
    assert claude["default_effort"] == "low"
    assert [e["effort_id"] for e in claude["effort_levels"]] == ["low", "medium", "high"]


def test_llm_providers_reports_why_claude_is_unavailable(client, claude_availability) -> None:
    message = _make_claude_unavailable(claude_availability, "not_signed_in")

    claude = client.get("/api/settings/llm-providers").json()[1]

    assert claude["is_available"] is False
    assert claude["unavailable_reason"] == "not_signed_in"
    assert claude["unavailable_message"] == message


def test_llm_providers_never_exposes_account_fields(client, claude_availability) -> None:
    raw = client.get("/api/settings/llm-providers").text.lower()

    assert "email" not in raw and "org" not in raw and "subscription" not in raw


def test_switching_to_claude_takes_its_default_model_and_keeps_effort(
    client, claude_availability
) -> None:
    client.put("/api/settings", json={"llm_effort": "high"})

    response = client.put("/api/settings", json={"llm_provider": "claude"})

    assert response.status_code == 200
    data = response.json()
    assert (data["llm_provider"], data["llm_model"], data["llm_effort"]) == (
        "claude",
        "sonnet",
        "high",
    )


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        (
            {"llm_provider": "claude", "llm_model": "llama3.2"},
            "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus.",
        ),
        (
            {"llm_provider": "ollama", "llm_model": "sonnet"},
            "That model belongs to Claude. Choose a local model, or switch the provider to Claude.",
        ),
    ],
)
def test_a_model_provider_mismatch_is_422_and_changes_nothing(
    client, claude_availability, body, detail
) -> None:
    before = client.get("/api/settings").json()

    response = client.put("/api/settings", json=body)

    assert (response.status_code, response.json()) == (422, {"detail": detail})
    assert client.get("/api/settings").json() == before


def test_selecting_an_unavailable_claude_is_422_with_its_message(
    client, claude_availability
) -> None:
    message = _make_claude_unavailable(claude_availability, "not_on_plan")
    before = client.get("/api/settings").json()

    response = client.put("/api/settings", json={"llm_provider": "claude"})

    assert (response.status_code, response.json()) == (422, {"detail": message})
    assert client.get("/api/settings").json() == before


@pytest.mark.parametrize("body", [{"llm_provider": "gpt"}, {"llm_effort": "max"}])
def test_out_of_pattern_values_are_422(client, claude_availability, body) -> None:
    before = client.get("/api/settings").json()

    assert client.put("/api/settings", json=body).status_code == 422
    assert client.get("/api/settings").json() == before


def test_effort_alone_is_saved(client, claude_availability) -> None:
    response = client.put("/api/settings", json={"llm_effort": "high"})

    assert (response.status_code, response.json()["llm_effort"]) == (200, "high")


def test_switching_back_to_ollama_resets_the_model_and_keeps_effort(
    client, claude_availability
) -> None:
    client.put("/api/settings", json={"llm_provider": "claude", "llm_effort": "medium"})

    data = client.put("/api/settings", json={"llm_provider": "ollama"}).json()

    assert (data["llm_provider"], data["llm_model"], data["llm_effort"]) == (
        "ollama",
        "llama3.1:8b",
        "medium",
    )


def test_other_settings_still_save_after_claude_sign_in_is_lost(
    client, claude_availability
) -> None:
    client.put("/api/settings", json={"llm_provider": "claude"})
    _make_claude_unavailable(claude_availability, "not_signed_in")

    response = client.put(
        "/api/settings",
        json={"llm_provider": "claude", "llm_model": "sonnet", "whisper_model": "small"},
    )

    assert response.status_code == 200
    assert response.json()["whisper_model"] == "small"
