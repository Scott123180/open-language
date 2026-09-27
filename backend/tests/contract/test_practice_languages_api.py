"""T015: GET /api/settings/practice-languages (contracts §1)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.practice_languages import DEFAULT_PRACTICE_LANGUAGE, PRACTICE_LANGUAGES
from app.services.factory import get_storage, get_voice_installation
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import make_test_session
from tests.support.fake_speech import FakeVoiceInstallation

ENDPOINT = "/api/settings/practice-languages"
ITEM_KEYS = {
    "language_id",
    "display_name",
    "is_default",
    "default_voice",
    "selected_voice",
    "is_voice_installed",
    "voice_unavailable_message",
}
SPANISH_ONLY = {"es_ES-davefx-medium", "es_AR-daniela-high"}


@pytest.fixture
def storage(tmp_path: Path):
    session, _engine = make_test_session(str(tmp_path / "test.db"))
    yield SQLiteStorageProvider(session)
    session.close()


@pytest.fixture
def client(storage):
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_voice_installation] = lambda: FakeVoiceInstallation(SPANISH_ONLY)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _by_id(client) -> dict[str, dict]:
    return {item["language_id"]: item for item in client.get(ENDPOINT).json()}


def test_lists_the_catalogue_in_order(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert [item["language_id"] for item in response.json()] == list(PRACTICE_LANGUAGES)
    assert [item["display_name"] for item in response.json()] == [
        language.name for language in PRACTICE_LANGUAGES.values()
    ]


def test_each_item_has_exactly_the_contract_keys(client):
    assert all(set(item) == ITEM_KEYS for item in client.get(ENDPOINT).json())


def test_exactly_one_item_is_the_default(client):
    defaults = [item["language_id"] for item in client.get(ENDPOINT).json() if item["is_default"]]

    assert defaults == [DEFAULT_PRACTICE_LANGUAGE]


def test_every_listed_language_is_accepted_by_put_settings(client):
    for language_id in _by_id(client):
        response = client.put("/api/settings", json={"target_language": language_id})
        assert response.status_code == 200, language_id


def test_a_message_is_present_exactly_when_the_voice_is_missing(client):
    items = _by_id(client)

    assert (items["es"]["is_voice_installed"], items["es"]["voice_unavailable_message"]) == (
        True,
        None,
    )
    assert items["de"]["is_voice_installed"] is False
    assert "German voice isn't installed" in items["de"]["voice_unavailable_message"]


def test_a_mismatched_stored_choice_resolves_to_the_default(client, storage):
    storage.save_voice_choice("de", "es_ES-davefx-medium")

    german = _by_id(client)["de"]

    assert german["selected_voice"] == german["default_voice"] == "de_DE-thorsten-medium"


def test_the_selected_voice_is_the_remembered_choice(client, storage):
    storage.save_voice_choice("es", "es_AR-daniela-high")

    assert _by_id(client)["es"]["selected_voice"] == "es_AR-daniela-high"
