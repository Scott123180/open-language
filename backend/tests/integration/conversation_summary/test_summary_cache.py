"""T081: a summary is reused until a line is added or the level changes (FR-042, data-model §2.5)."""

from tests.integration.conversation_summary.conftest import roleplay_with_lines, summary_of


def test_a_second_request_with_nothing_new_is_served_from_the_cache(summary_client, summary_llm):
    conversation_id = roleplay_with_lines(summary_client, 4)
    first = summary_of(summary_client, conversation_id).json()

    second = summary_of(summary_client, conversation_id).json()

    assert second == first
    assert len(summary_llm.calls) == 1


def test_a_new_line_regenerates_the_summary(summary_client, summary_llm):
    conversation_id = roleplay_with_lines(summary_client, 4)
    summary_of(summary_client, conversation_id)
    added = summary_client.conversations.save_message(conversation_id, "user", "Una más.")

    body = summary_of(summary_client, conversation_id).json()

    assert body["up_to_message_id"] == added.id
    assert len(summary_llm.calls) == 2
    assert "Una más." in summary_llm.last_prompt


def test_a_level_change_regenerates_the_summary(summary_client, summary_llm):
    conversation_id = roleplay_with_lines(summary_client, 4)
    summary_of(summary_client, conversation_id)
    summary_client.client.put("/api/settings", json={"conversation_level": "beginner"})

    summary_of(summary_client, conversation_id)

    assert len(summary_llm.calls) == 2
    assert "Línea 0" in summary_llm.last_prompt
