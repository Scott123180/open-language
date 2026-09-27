"""T070: a conversation keeps its language after the practice language changes.

FR-006, FR-009, FR-014, FR-019, FR-025; spec US2-2 and US2-3.
"""

import sqlite3
from pathlib import Path

import pytest

from app.services.conversation import SessionKind
from tests.integration.conversation_levels.level_harness import wait_until
from tests.integration.practice_languages.language_harness import language_harness

SNAPSHOT_TABLES = ("conversations", "messages", "vocabulary_items")
NAMES_BY_TOOL = {
    "phrasing": ("Spanish",),
    "word-lookup": ("Spanish", "English"),
    "translate": ("English",),
    "grammar": ("English",),
}


@pytest.fixture
def harness(tmp_path, monkeypatch):
    yield from language_harness(tmp_path, monkeypatch)


@pytest.fixture
def spanish(harness) -> int:
    """A Spanish conversation with an opening line, after which German is selected."""
    harness.put_settings(target_language="es")
    conversation_id = harness.new_conversation()
    harness.open(conversation_id)
    harness.put_settings(target_language="de")
    return conversation_id


def _snapshot(db_file: Path) -> dict[str, list[tuple]]:
    with sqlite3.connect(db_file) as conn:
        return {
            t: conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall() for t in SNAPSHOT_TABLES
        }


def test_the_roleplay_prompts_stay_spanish(harness, spanish):
    harness.engine.requests.clear()

    harness.warm(spanish)
    harness.send(spanish, "Quiero un café")

    for request in harness.engine.requests_of(SessionKind.ROLEPLAY):
        assert "EXCLUSIVELY in Spanish" in request.standing_prompt


def test_the_suggestions_stay_spanish(harness, spanish):
    harness.client.post(f"/api/chat/{spanish}/suggestions")

    assert "next in Spanish" in harness.llm.prompts[-1]


@pytest.mark.parametrize(
    ("tool", "body"),
    [
        ("phrasing", {"content": "Quiero un café"}),
        ("word-lookup", {"selection": "café", "sentence_context": "Quiero un café"}),
        ("translate", {"content": "Quiero un café"}),
        ("grammar", {"content": "Quiero un café"}),
    ],
)
def test_each_learning_aid_stays_with_the_conversation(harness, spanish, tool, body):
    message_id = harness.last_message_id(spanish)

    harness.client.post(f"/api/learning/{tool}", json={"message_id": message_id, **body})

    prompt = harness.llm.prompts[-1]
    assert "German" not in prompt
    assert all(name in prompt for name in NAMES_BY_TOOL[tool])


def test_the_helper_stays_spanish(harness, spanish):
    harness.ask_helper(spanish, "How do I ask for the bill?")

    [request] = harness.engine.requests_of(SessionKind.HELPER)
    assert "Spanish" in request.standing_prompt and "German" not in request.standing_prompt


def test_the_reply_is_spoken_with_a_spanish_voice(harness, spanish):
    harness.send(spanish, "Quiero un café")

    wait_until(lambda: len(harness.speech.voice_keys) >= 2)
    assert all(voice.startswith("es_") for voice in harness.speech.voice_keys)


def test_a_word_saved_from_the_spanish_conversation_is_spanish(harness, spanish):
    body = {"word": "café", "translation": "coffee", "source_conversation_id": spanish}

    saved = harness.client.post("/api/vocabulary", json=body).json()

    assert saved["target_language"] == "es"


def test_a_word_saved_without_a_conversation_takes_the_practice_language(harness, spanish):
    saved = harness.client.post("/api/vocabulary", json={"word": "Haus", "translation": "house"})

    assert saved.json()["target_language"] == "de"


def test_an_unknown_source_conversation_is_404(harness, spanish):
    body = {"word": "Haus", "translation": "house", "source_conversation_id": 9999}

    response = harness.client.post("/api/vocabulary", json=body)

    assert (response.status_code, response.json()) == (404, {"detail": "Conversation not found"})


def test_a_new_conversation_is_german(harness, spanish):
    conversation_id = harness.new_conversation()

    assert harness.storage().get_conversation(conversation_id).target_language == "de"


def test_switching_language_rewrites_nothing(harness, spanish, tmp_path):
    harness.client.post(
        "/api/vocabulary",
        json={"word": "café", "translation": "coffee", "source_conversation_id": spanish},
    )
    db_file = tmp_path / "languages.db"
    before = _snapshot(db_file)

    harness.put_settings(target_language="es")
    harness.put_settings(target_language="de")

    assert _snapshot(db_file) == before
