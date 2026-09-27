"""T047: a flashcard word is spoken in its own language's voice, or not at all (FR-014, FR-018)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.practice_languages import voice_unavailable_message
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.integration.conftest import _configure_sqlite
from tests.support.fake_speech import override_speech, write_silent_wav

SPANISH_ONLY = {"es_ES-davefx-medium", "es_AR-daniela-high"}


@pytest.fixture
def storage():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    event.listen(engine, "connect", _configure_sqlite)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db] = lambda: session
    yield SQLiteStorageProvider(session)
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def speak(storage, tmp_path: Path, monkeypatch):
    """Returns a builder: `speak(installed=…)` → (client, tts builder)."""
    clients: list[TestClient] = []

    def build(installed=None):
        builder = override_speech(app, installed=installed)
        clients.append(TestClient(app))
        return clients[-1].__enter__(), builder

    yield build
    for client in clients:
        client.__exit__(None, None, None)


def _word(storage: SQLiteStorageProvider, word: str, language: str) -> int:
    return storage.save_vocabulary_item(word, "translation", language, "en").id


def test_a_german_word_uses_a_german_voice_while_spanish_is_selected(storage, speak):
    storage.update_settings(target_language="es")
    client, builder = speak()
    word_id = _word(storage, "Straße", "de")

    assert client.get(f"/api/flashcards/tts/{word_id}").status_code == 200
    assert builder.synthesized[0][:2] == ("de_DE-thorsten-medium", "Straße")


def test_a_spanish_word_uses_the_spanish_choice_while_german_is_selected(storage, speak):
    storage.update_settings(target_language="de")
    storage.save_voice_choice("es", "es_AR-daniela-high")
    client, builder = speak()
    word_id = _word(storage, "año", "es")

    assert client.get(f"/api/flashcards/tts/{word_id}").status_code == 200
    assert builder.voice_keys == ["es_AR-daniela-high"]


def test_an_uninstalled_german_voice_is_503_and_nothing_is_spoken(storage, speak):
    client, builder = speak(installed=SPANISH_ONLY)
    word_id = _word(storage, "Haus", "de")

    response = client.get(f"/api/flashcards/tts/{word_id}")

    assert (response.status_code, response.json()) == (
        503,
        {"detail": voice_unavailable_message("de")},
    )
    assert builder.synthesized == []


def test_a_cached_word_is_served_without_a_voice_check(storage, speak, tmp_path: Path):
    client, builder = speak(installed=set())
    word_id = _word(storage, "Haus", "de")
    cached = tmp_path / "haus.wav"
    write_silent_wav(cached)
    storage._db.execute(text("UPDATE vocabulary_items SET tts_cache_path = :p"), {"p": str(cached)})
    storage._db.commit()

    assert client.get(f"/api/flashcards/tts/{word_id}").status_code == 200
    assert builder.synthesized == []
