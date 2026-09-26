"""T053: alternative phrasings are cached per level (005 data-model §6, research R7).

A phrasing cached at one level must not be served at another, a Beginner phrasing is cached for
Beginner, and rows written before this feature (keyed by the bare message content) are still hits
at Natural.
"""

import pytest
from sqlalchemy import select

from app.conversation_levels import ConversationLevel
from app.models.learning_tool_result import LearningToolResult
from tests.integration.conversation_levels.level_harness import level_harness

LEARNER_MESSAGE = "Quiero una mesa para dos"
PHRASING_TOOL = "alternative_phrasing"
PRE_FEATURE_RESULT = "Una mesa para dos, por favor."


@pytest.fixture()
def harness(tmp_path, monkeypatch):
    yield from level_harness(tmp_path, monkeypatch)


@pytest.fixture()
def message_id(harness) -> int:
    conversation_id = harness.new_conversation()
    harness.send(conversation_id, LEARNER_MESSAGE)
    messages = harness.storage().get_messages(conversation_id)
    return next(message.id for message in messages if message.role == "user")


def _phrase(harness, message_id: int) -> dict:
    body = {"message_id": message_id, "content": LEARNER_MESSAGE, "target_language": "es"}
    response = harness.client.post("/api/learning/phrasing", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _phrasing_keys(harness, message_id: int) -> list[str]:
    query = select(LearningToolResult.input_selection).where(
        LearningToolResult.message_id == message_id
    )
    return list(harness.new_session().scalars(query))


def test_a_phrasing_cached_at_natural_is_not_served_at_beginner(harness, message_id):
    _phrase(harness, message_id)
    harness.set_level(ConversationLevel.BEGINNER)

    result = _phrase(harness, message_id)

    assert result["cached"] is False
    assert len(harness.llm.prompts) == 2


def test_a_second_request_at_beginner_is_served_from_the_cache(harness, message_id):
    harness.set_level(ConversationLevel.BEGINNER)
    _phrase(harness, message_id)

    result = _phrase(harness, message_id)

    assert result["cached"] is True
    assert len(harness.llm.prompts) == 1


def test_a_pre_feature_row_is_still_a_cache_hit_at_natural(harness, message_id):
    harness.storage().get_or_create_learning_result(
        message_id, PHRASING_TOOL, LEARNER_MESSAGE, lambda: PRE_FEATURE_RESULT
    )

    result = _phrase(harness, message_id)

    assert result == {"result": PRE_FEATURE_RESULT, "cached": True}
    assert harness.llm.prompts == []


def test_the_beginner_row_is_keyed_by_the_level_and_the_content(harness, message_id):
    harness.set_level(ConversationLevel.BEGINNER)

    _phrase(harness, message_id)

    assert _phrasing_keys(harness, message_id) == [f"[level:beginner] {LEARNER_MESSAGE}"]
