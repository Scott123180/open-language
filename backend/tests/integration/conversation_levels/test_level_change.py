"""T043: a level change applies from the next reply, with no restart and no lost history.

FR-008, SC-005, US2 AS3 and the "change while a reply is being written" edge case. Nothing here
needs new engine code: the session fingerprint's standing-prompt digest triggers the rebuild
(research R2).
"""

import pytest

from app.conversation_levels import ConversationLevel, with_partner_speech_rules
from app.services.conversation import SessionKind
from tests.integration.conversation_levels.level_harness import level_harness


@pytest.fixture()
def harness(tmp_path, monkeypatch):
    yield from level_harness(tmp_path, monkeypatch)


def _expected(harness, conversation_id: int, level: ConversationLevel) -> str:
    return with_partner_speech_rules(harness.roleplay_prompt(conversation_id), level)


def _stored_messages(harness, conversation_id: int) -> list[tuple[int, str, str]]:
    messages = harness.storage().get_messages(conversation_id)
    return [(m.id, m.role, m.content) for m in messages]


def _roleplay_requests(harness):
    return harness.engine.requests_of(SessionKind.ROLEPLAY)


class TestChangingTheLevelMidConversation:
    @pytest.fixture()
    def changed(self, harness):
        """Opening plus two turns at Intermediate, then a change to Beginner and a third turn."""
        harness.set_level(ConversationLevel.INTERMEDIATE)
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)
        harness.send(conversation_id, "Hola")
        harness.send(conversation_id, "Quiero una mesa")
        before = _stored_messages(harness, conversation_id)
        harness.set_level(ConversationLevel.BEGINNER)
        harness.send(conversation_id, "¿Qué hay de comer?")
        return conversation_id, before

    def test_the_next_request_carries_the_beginner_rules(self, harness, changed):
        conversation_id, _ = changed

        *earlier, last = _roleplay_requests(harness)

        intermediate = _expected(harness, conversation_id, ConversationLevel.INTERMEDIATE)
        assert [request.standing_prompt for request in earlier] == [intermediate] * 3
        assert last.standing_prompt == _expected(
            harness, conversation_id, ConversationLevel.BEGINNER
        )

    def test_the_old_session_is_closed_and_a_new_one_opened(self, harness, changed):
        first, rebuilt = harness.provider.opened

        assert first.is_closed
        assert not rebuilt.is_closed
        assert len(rebuilt.replies) == 1

    def test_the_rebuilt_session_starts_from_the_saved_history(self, harness, changed):
        conversation_id, before = changed

        rebuilt = harness.provider.opened[-1]
        [(pending, _guidance)] = rebuilt.replies

        restored = [(turn.role, turn.content) for turn in (*rebuilt.history, *pending)]
        saved = [(role, content) for _id, role, content in before]
        assert restored == [*saved, ("user", "¿Qué hay de comer?")]

    def test_earlier_messages_are_unchanged_and_nothing_restarted(self, harness, changed):
        conversation_id, before = changed

        after = _stored_messages(harness, conversation_id)

        assert after[: len(before)] == before
        assert len(harness.storage().list_conversations()) == 1


def test_a_reopened_conversation_uses_the_current_level(harness):
    harness.set_level(ConversationLevel.NATURAL)
    conversation_id = harness.new_conversation()
    harness.open(conversation_id)
    harness.send(conversation_id, "Hola")
    harness.engine.close()  # the conversation is closed, as when the learner leaves it

    harness.set_level(ConversationLevel.ELEMENTARY)
    harness.send(conversation_id, "Estoy de vuelta")

    last = _roleplay_requests(harness)[-1]
    assert last.standing_prompt == _expected(harness, conversation_id, ConversationLevel.ELEMENTARY)


def test_a_reply_in_progress_finishes_at_the_level_it_started_with(harness):
    harness.set_level(ConversationLevel.NATURAL)
    conversation_id = harness.new_conversation()
    harness.open(conversation_id)

    def change_level_mid_reply() -> None:
        harness.storage().update_settings(conversation_level=ConversationLevel.BEGINNER.value)

    harness.provider.during_next_reply = change_level_mid_reply
    events = harness.send(conversation_id, "Hola")
    harness.send(conversation_id, "¿Y ahora?")

    *_, in_progress, following = _roleplay_requests(harness)
    assert events[-1]["done"] is True
    assert in_progress.standing_prompt == harness.roleplay_prompt(conversation_id)
    assert following.standing_prompt == _expected(
        harness, conversation_id, ConversationLevel.BEGINNER
    )
