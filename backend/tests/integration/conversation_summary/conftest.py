"""Summary fixtures: the podcast harness plus a scripted structured model."""

import pytest

from app.main import app
from app.services.factory import get_structured_llm
from tests.support.podcast_harness import podcast_harness
from tests.support.scripted_summary_llm import ScriptedSummaryLLM


@pytest.fixture
def summary_llm() -> ScriptedSummaryLLM:
    return ScriptedSummaryLLM()


@pytest.fixture
def summary_client(tmp_path, summary_llm):
    with podcast_harness(tmp_path) as harness:
        app.dependency_overrides[get_structured_llm] = lambda: summary_llm
        yield harness


def roleplay_with_lines(harness, count: int, language: str = "es") -> int:
    """A roleplay conversation holding `count` alternating lines."""
    conversations = harness.conversations
    conversation = conversations.create_conversation(
        "order-at-restaurant", "Order", language, "en", "m"
    )
    for index in range(count):
        role = "assistant" if index % 2 == 0 else "user"
        conversations.save_message(conversation.id, role, f"Línea {index}")
    return conversation.id


def summary_of(harness, conversation_id: int):
    return harness.client.get(f"/api/conversations/{conversation_id}/summary")
