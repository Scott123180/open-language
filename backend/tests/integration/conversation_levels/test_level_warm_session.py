"""T030: a warmed session already carries the level, so the next turn reuses it (research R8)."""

import pytest

from app.conversation_levels import ConversationLevel, with_partner_speech_rules
from app.services.conversation import SessionFingerprint
from tests.integration.conversation_levels.level_harness import level_harness, wait_until


@pytest.fixture()
def harness(tmp_path, monkeypatch):
    yield from level_harness(tmp_path, monkeypatch)


def test_a_session_warmed_at_beginner_serves_the_next_turn_without_a_rebuild(harness):
    harness.set_level(ConversationLevel.BEGINNER)
    conversation_id = harness.new_conversation()
    harness.open(conversation_id)
    harness.engine.close()  # as after a restart: the conversation has no live session

    assert harness.warm(conversation_id) == {"status": "warming"}
    wait_until(lambda: len(harness.provider.opened) == 2 and harness.provider.opened[1].warm_count)
    harness.send(conversation_id, "Hola")

    warmed = harness.provider.opened[1]
    expected = with_partner_speech_rules(
        harness.roleplay_prompt(conversation_id), ConversationLevel.BEGINNER
    )
    assert harness.engine.warmed_prompts == [expected]
    assert warmed.fingerprint.standing_prompt_digest == SessionFingerprint.digest_prompt(expected)
    assert len(harness.provider.opened) == 2
    assert len(warmed.replies) == 1
