"""T052: learner aids follow the level; native-language tools do not (005 contract §4).

FR-017 (suggestions, alternative phrasings and the helper's phrase follow the level), FR-018
(grammar, translation and word lookup are unchanged), research R5 (the learner-text block has no
reply-length or question rule) and R6 (a level change rebuilds the helper session).
"""

import pytest

from app.conversation_levels import ConversationLevel, with_learner_text_rules
from app.practice_languages import language_name
from app.prompts.templates import (
    build_helper_system_prompt,
    build_phrasing_prompt,
    build_suggestion_prompt,
)
from app.services.conversation import SessionKind
from tests.integration.conversation_levels.level_harness import level_harness

LEARNER_MESSAGE = "Quiero una mesa para dos"
HELPER_TARGET = "Spanish"
HELPER_NATIVE = "English"
PARTNER_ONLY_RULES = ("per reply", "Questions to the learner")


@pytest.fixture()
def harness(tmp_path, monkeypatch):
    yield from level_harness(tmp_path, monkeypatch)


def _conversation_with_learner_message(harness) -> tuple[int, int]:
    """A conversation holding one learner message; returns (conversation id, message id)."""
    conversation_id = harness.new_conversation()
    harness.send(conversation_id, LEARNER_MESSAGE)
    messages = harness.storage().get_messages(conversation_id)
    learner = next(message for message in messages if message.role == "user")
    return conversation_id, learner.id


def _suggestion_prompt(harness, conversation_id: int) -> str:
    """What `build_suggestion_prompt` gives this conversation today, before any level."""
    messages = harness.storage().get_messages(conversation_id)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
    settings = harness.storage().get_settings()
    target_language = language_name(harness.conversation(conversation_id).target_language)
    return build_suggestion_prompt(history_text, target_language, settings.suggestion_count)


def _request_suggestions(harness, conversation_id: int) -> str:
    response = harness.client.post(f"/api/chat/{conversation_id}/suggestions")
    assert response.status_code == 200, response.text
    return harness.llm.prompts[-1]


def _request_phrasing(harness, message_id: int) -> str:
    body = {"message_id": message_id, "content": LEARNER_MESSAGE, "target_language": "es"}
    response = harness.client.post("/api/learning/phrasing", json=body)
    assert response.status_code == 200, response.text
    return harness.llm.prompts[-1]


def _phrasing_prompt(harness) -> str:
    target_language = language_name(harness.storage().get_settings().target_language)
    return build_phrasing_prompt(LEARNER_MESSAGE, target_language)


def _helper_prompts(harness) -> list[str]:
    return [r.standing_prompt for r in harness.engine.requests_of(SessionKind.HELPER)]


def _helper_prompt() -> str:
    return build_helper_system_prompt(HELPER_TARGET, HELPER_NATIVE)


class TestNaturalIsTodaysPrompt:
    def test_suggestions_send_the_unchanged_prompt(self, harness):
        conversation_id, _ = _conversation_with_learner_message(harness)

        prompt = _request_suggestions(harness, conversation_id)

        assert prompt == _suggestion_prompt(harness, conversation_id)

    def test_phrasing_sends_the_unchanged_prompt(self, harness):
        _, message_id = _conversation_with_learner_message(harness)

        prompt = _request_phrasing(harness, message_id)

        assert prompt == _phrasing_prompt(harness)

    def test_the_helper_gets_the_unchanged_standing_prompt(self, harness):
        harness.ask_helper("How do I ask for the bill?")

        assert _helper_prompts(harness) == [_helper_prompt()]


class TestBeginnerAppendsTheLearnerTextBlock:
    @pytest.fixture(autouse=True)
    def beginner(self, harness):
        harness.set_level(ConversationLevel.BEGINNER)

    def test_suggestions_carry_the_beginner_rules(self, harness):
        conversation_id, _ = _conversation_with_learner_message(harness)

        prompt = _request_suggestions(harness, conversation_id)

        expected = _suggestion_prompt(harness, conversation_id)
        assert prompt == with_learner_text_rules(expected, ConversationLevel.BEGINNER)

    def test_phrasing_carries_the_beginner_rules(self, harness):
        _, message_id = _conversation_with_learner_message(harness)

        prompt = _request_phrasing(harness, message_id)

        expected = with_learner_text_rules(_phrasing_prompt(harness), ConversationLevel.BEGINNER)
        assert prompt == expected

    def test_the_helper_standing_prompt_carries_the_beginner_rules(self, harness):
        harness.ask_helper("How do I ask for the bill?")

        expected = with_learner_text_rules(_helper_prompt(), ConversationLevel.BEGINNER)
        assert _helper_prompts(harness) == [expected]

    def test_no_aid_carries_the_reply_length_or_question_rules(self, harness):
        conversation_id, message_id = _conversation_with_learner_message(harness)
        harness.ask_helper("How do I ask for the bill?")

        prompts = [
            _request_suggestions(harness, conversation_id),
            _request_phrasing(harness, message_id),
            *_helper_prompts(harness),
        ]

        for prompt in prompts:
            assert not any(rule in prompt for rule in PARTNER_ONLY_RULES), prompt


def test_changing_the_level_between_helper_questions_rebuilds_the_helper_session(harness):
    harness.ask_helper("How do I ask for the bill?")
    harness.set_level(ConversationLevel.ELEMENTARY)

    harness.ask_helper("And how do I say it was delicious?")

    first, rebuilt = harness.provider.opened
    assert first.is_closed
    assert not rebuilt.is_closed
    expected = with_learner_text_rules(_helper_prompt(), ConversationLevel.ELEMENTARY)
    assert _helper_prompts(harness)[-1] == expected


NATIVE_LANGUAGE_TOOLS = (
    ("/api/learning/grammar", {"content": LEARNER_MESSAGE}),
    ("/api/learning/translate", {"content": LEARNER_MESSAGE, "native_language": "en"}),
    (
        "/api/learning/word-lookup",
        {"selection": "mesa", "target_language": "es", "native_language": "en"},
    ),
)


@pytest.mark.parametrize(("url", "body"), NATIVE_LANGUAGE_TOOLS)
def test_native_language_tools_are_unchanged_by_the_level(harness, url, body):
    _, natural_message = _conversation_with_learner_message(harness)
    _, beginner_message = _conversation_with_learner_message(harness)

    harness.client.post(url, json={**body, "message_id": natural_message})
    harness.set_level(ConversationLevel.BEGINNER)
    harness.client.post(url, json={**body, "message_id": beginner_message})

    natural_prompt, beginner_prompt = harness.llm.prompts
    assert natural_prompt == beginner_prompt
