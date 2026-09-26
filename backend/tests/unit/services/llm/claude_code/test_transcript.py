"""T060: translating the app's message lists into one `claude -p` prompt (research R-5, R-14)."""

from app.services.conversation import SavedTurn
from app.services.llm.base import ChatMessage
from app.services.llm.claude_code.command import DEFAULT_SYSTEM_PROMPT
from app.services.llm.claude_code.transcript import (
    NEXT_TURN_INSTRUCTION,
    render_guidance_block,
    render_prompt,
    render_rebuild_turn,
)

SYSTEM = ChatMessage("system", "Eres Lucía.")
EXTRA_SYSTEM = ChatMessage("system", "Habla despacio.")
GREETING = ChatMessage("assistant", "¡Hola! ¿Qué desea?")
ASK = ChatMessage("user", "Un billete a Sevilla.")


def test_system_messages_are_joined_with_a_blank_line():
    rendered = render_prompt([SYSTEM, EXTRA_SYSTEM, ASK])

    assert rendered.system_prompt == "Eres Lucía.\n\nHabla despacio."


def test_no_system_message_uses_the_default_prompt():
    assert render_prompt([ASK]).system_prompt == DEFAULT_SYSTEM_PROMPT


def test_a_single_user_message_is_the_prompt_verbatim():
    assert render_prompt([SYSTEM, ASK]).prompt == "Un billete a Sevilla."


def test_several_turns_become_a_transcript_then_the_next_turn_instruction():
    prompt = render_prompt([SYSTEM, GREETING, ASK]).prompt

    assert prompt == (
        "<conversation>\n"
        '<turn role="assistant">¡Hola! ¿Qué desea?</turn>\n'
        '<turn role="user">Un billete a Sevilla.</turn>\n'
        "</conversation>\n"
        f"{NEXT_TURN_INSTRUCTION}"
    )


def test_the_next_turn_instruction_asks_for_bare_words():
    assert NEXT_TURN_INSTRUCTION == (
        "Write the assistant's next turn only: the words themselves, "
        "with no tag, label, or quotation marks."
    )


def test_a_history_opening_with_the_assistant_needs_no_special_case():
    prompt = render_prompt([GREETING]).prompt

    assert prompt.startswith('<conversation>\n<turn role="assistant">')


def test_guidance_block_wraps_the_guidance():
    assert (
        render_guidance_block("Recast gently.") == "<turn_guidance>Recast gently.</turn_guidance>"
    )


class TestRebuildTurn:
    history = (SavedTurn("m1", "assistant", "¡Hola!"), SavedTurn("m2", "user", "Hola."))
    pending = (SavedTurn("m3", "user", "Un billete."),)

    def test_holds_the_transcript_of_history_and_pending(self):
        text = render_rebuild_turn(self.history, self.pending, None)

        assert text.startswith("<conversation>\n")
        for turn in (*self.history, *self.pending):
            assert f'<turn role="{turn.role}">{turn.content}</turn>' in text
        assert NEXT_TURN_INSTRUCTION in text
        assert "<turn_guidance>" not in text

    def test_carries_the_guidance_block_when_given(self):
        text = render_rebuild_turn(self.history, self.pending, "Recast gently.")

        assert text.endswith(render_guidance_block("Recast gently."))
