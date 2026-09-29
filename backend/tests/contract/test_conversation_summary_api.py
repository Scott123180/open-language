"""T080: GET /api/conversations/{id}/summary (contracts §9)."""

import pytest

from app.main import app
from app.services.factory import get_structured_llm
from app.services.llm.base import LLMError
from tests.support.podcast_harness import podcast_harness
from tests.support.scripted_summary_llm import ScriptedSummaryLLM

READY_KEYS = {
    "status",
    "conversation_id",
    "up_to_message_id",
    "conversation_language",
    "conversation_language_name",
    "native_language_name",
    "points",
}
TOO_EARLY = "There's nothing to summarise yet. Come back after the next line."


@pytest.fixture
def llm() -> ScriptedSummaryLLM:
    return ScriptedSummaryLLM()


@pytest.fixture
def harness(tmp_path, llm):
    with podcast_harness(tmp_path) as podcast:
        app.dependency_overrides[get_structured_llm] = lambda: llm
        yield podcast


def _conversation(harness, lines: int, language: str = "de") -> tuple[int, int | None]:
    storage = harness.conversations
    conversation = storage.create_conversation("order-at-restaurant", "Order", language, "en", "m")
    last = None
    for index in range(lines):
        last = storage.save_message(
            conversation.id, "assistant" if index % 2 == 0 else "user", "Hallo"
        ).id
    return conversation.id, last


def test_a_ready_summary_has_the_contract_shape(harness):
    conversation_id, last = _conversation(harness, 4)

    body = harness.client.get(f"/api/conversations/{conversation_id}/summary").json()

    assert set(body) == READY_KEYS
    assert body["status"] == "ready"
    assert (body["conversation_id"], body["up_to_message_id"]) == (conversation_id, last)
    assert 1 <= len(body["points"]) <= 5
    assert all(set(point) == {"conversation_language", "english"} for point in body["points"])


def test_the_summary_uses_the_conversations_language_not_the_setting(harness):
    conversation_id, _last = _conversation(harness, 4, language="de")
    harness.client.put("/api/settings", json={"target_language": "es"})

    body = harness.client.get(f"/api/conversations/{conversation_id}/summary").json()

    assert (body["conversation_language"], body["conversation_language_name"]) == ("de", "German")
    assert body["native_language_name"] == "English"


def test_too_early_says_so_without_asking_the_model(harness, llm):
    conversation_id, _last = _conversation(harness, 1)

    body = harness.client.get(f"/api/conversations/{conversation_id}/summary").json()

    assert body == {"status": "too_early", "message": TOO_EARLY}
    assert llm.calls == []


def test_an_unknown_conversation_is_not_found(harness):
    response = harness.client.get("/api/conversations/999/summary")

    assert response.status_code == 404


def test_a_provider_failure_is_503_with_its_message(harness, llm):
    conversation_id, _last = _conversation(harness, 4)
    llm.error = LLMError("down", "The AI is not responding. Please try again.")

    response = harness.client.get(f"/api/conversations/{conversation_id}/summary")

    assert (response.status_code, response.json()) == (
        503,
        {"detail": "The AI is not responding. Please try again."},
    )


def test_an_unusable_reply_is_503_with_a_retry_message(harness, llm):
    conversation_id, _last = _conversation(harness, 4)
    llm.raw_reply = '{"points": []}'

    response = harness.client.get(f"/api/conversations/{conversation_id}/summary")

    assert response.status_code == 503
    assert "try again" in response.json()["detail"].lower()
