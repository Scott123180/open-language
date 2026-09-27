"""T029: the level reaches the roleplay standing prompt, and nothing else (005 contract §3)."""

import pytest

from app.conversation_levels import ConversationLevel, with_partner_speech_rules
from app.corrections.services.strategies import TurnPlan
from app.services.conversation import SessionKind
from tests.integration.conversation_levels.level_harness import (
    level_harness,
    wait_until,
)

GENTLE_SUFFIX = " Recast any mistake naturally."
CUSTOM_CHARACTER = "A university professor lecturing on the history of Spain."


@pytest.fixture()
def harness(tmp_path, monkeypatch):
    yield from level_harness(tmp_path, monkeypatch)


def _roleplay_prompts(harness) -> list[str]:
    return [r.standing_prompt for r in harness.engine.requests_of(SessionKind.ROLEPLAY)]


class TestNaturalIsTodaysPrompt:
    def test_open_and_message_send_the_unchanged_roleplay_prompt(self, harness):
        conversation_id = harness.new_conversation()

        harness.open(conversation_id)
        harness.send(conversation_id, "Hola")

        assert _roleplay_prompts(harness) == [harness.roleplay_prompt(conversation_id)] * 2


class TestBeginnerAppendsThePartnerBlock:
    def test_open_and_message_carry_the_beginner_rules(self, harness):
        harness.set_level(ConversationLevel.BEGINNER)
        conversation_id = harness.new_conversation()

        harness.open(conversation_id)
        harness.send(conversation_id, "Hola")

        expected = with_partner_speech_rules(
            harness.roleplay_prompt(conversation_id), ConversationLevel.BEGINNER
        )
        assert _roleplay_prompts(harness) == [expected] * 2

    def test_the_language_rule_still_comes_first(self, harness):
        harness.set_level(ConversationLevel.BEGINNER)
        conversation_id = harness.new_conversation()

        harness.open(conversation_id)

        [prompt] = _roleplay_prompts(harness)
        assert prompt.startswith(harness.roleplay_prompt(conversation_id))
        assert prompt.index("CRITICAL LANGUAGE RULE") < prompt.index("These rules about how")

    def test_the_opening_request_carries_the_level(self, harness):
        harness.set_level(ConversationLevel.BEGINNER)
        conversation_id = harness.new_conversation()

        harness.open(conversation_id)

        [opening] = harness.engine.requests
        assert opening.opening_instruction is not None
        assert opening.standing_prompt.endswith(
            with_partner_speech_rules("", ConversationLevel.BEGINNER)
        )

    def test_a_custom_prompt_gets_the_block_after_the_character_text(self, harness):
        harness.set_level(ConversationLevel.ELEMENTARY)
        conversation_id = harness.new_custom_conversation(CUSTOM_CHARACTER)

        harness.open(conversation_id)

        [prompt] = _roleplay_prompts(harness)
        assert prompt.index(CUSTOM_CHARACTER) < prompt.index("These rules about how")
        assert prompt == with_partner_speech_rules(
            harness.roleplay_prompt(conversation_id), ConversationLevel.ELEMENTARY
        )


class TestTheLevelTouchesNothingElse:
    @pytest.mark.parametrize("level", [ConversationLevel.NATURAL, ConversationLevel.BEGINNER])
    def test_gentle_guidance_arrives_unchanged(self, harness, level):
        harness.strategy.plan = TurnPlan(reply_prompt_suffix=GENTLE_SUFFIX)
        harness.set_level(level)
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)

        harness.send(conversation_id, "Yo quiero un mesa")

        assert harness.engine.requests[-1].guidance == GENTLE_SUFFIX

    def test_the_prompt_is_the_same_whichever_provider_is_selected(self, harness):
        harness.set_level(ConversationLevel.BEGINNER)
        conversation_id = harness.new_conversation()
        harness.open(conversation_id)

        switched = harness.client.put("/api/settings", json={"llm_provider": "claude"}).json()
        harness.send(conversation_id, "Hola")

        assert switched["conversation_level"] == "beginner"
        first, second = _roleplay_prompts(harness)
        assert first == second

    def test_the_voice_and_spoken_text_do_not_depend_on_the_level(self, harness):
        voices = []
        for level in (ConversationLevel.NATURAL, ConversationLevel.BEGINNER):
            harness.set_level(level)
            conversation_id = harness.new_conversation()
            events = harness.open(conversation_id)
            wait_until(lambda: len(harness.speech.synthesized) == len(voices) + 1)
            voice, text, path = harness.speech.synthesized[-1]
            assert text == "".join(e["token"] for e in events if "token" in e)
            assert path.name == f"{events[-1]['message_id']}.wav"
            voices.append(voice)

        assert voices[0] == voices[1]
