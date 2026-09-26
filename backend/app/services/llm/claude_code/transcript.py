"""Rendering the app's message lists as `claude` prompts (research R-5, R-14).

A one-shot `claude -p` takes a single prompt, so a conversation travels as a transcript with
unambiguous tags. Single-message requests (learning tools, corrections) go through verbatim.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.conversation.session import SavedTurn
from app.services.llm.base import ChatMessage
from app.services.llm.claude_code.command import DEFAULT_SYSTEM_PROMPT

SYSTEM_ROLE = "system"
USER_ROLE = "user"
CONVERSATION_OPEN_TAG = "<conversation>"
CONVERSATION_CLOSE_TAG = "</conversation>"
TURN_TEMPLATE = '<turn role="{role}">{content}</turn>'
GUIDANCE_TEMPLATE = "<turn_guidance>{guidance}</turn_guidance>"
NEXT_TURN_INSTRUCTION = (
    "Write the assistant's next turn only: the words themselves, "
    "with no tag, label, or quotation marks."
)
_SYSTEM_SEPARATOR = "\n\n"
_BLOCK_SEPARATOR = "\n\n"


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    system_prompt: str
    prompt: str


def render_prompt(messages: Sequence[ChatMessage]) -> RenderedPrompt:
    system_parts = [m.content for m in messages if m.role == SYSTEM_ROLE]
    turns = [(m.role, m.content) for m in messages if m.role != SYSTEM_ROLE]
    system_prompt = _SYSTEM_SEPARATOR.join(system_parts) or DEFAULT_SYSTEM_PROMPT
    if len(turns) == 1 and turns[0][0] == USER_ROLE:
        return RenderedPrompt(system_prompt, turns[0][1])
    return RenderedPrompt(system_prompt, _transcript(turns))


def render_rebuild_turn(
    history: Sequence[SavedTurn], pending: Sequence[SavedTurn], guidance: str | None
) -> str:
    """One user message carrying the whole saved conversation, so a rebuild costs one reply."""
    transcript = _transcript([(turn.role, turn.content) for turn in (*history, *pending)])
    return with_guidance(transcript, guidance)


def render_guidance_block(guidance: str) -> str:
    return GUIDANCE_TEMPLATE.format(guidance=guidance)


def with_guidance(text: str, guidance: str | None) -> str:
    """Append this turn's guidance block, if any, after a blank line."""
    if not guidance:
        return text
    return f"{text}{_BLOCK_SEPARATOR}{render_guidance_block(guidance)}"


def _transcript(turns: Sequence[tuple[str, str]]) -> str:
    lines = [CONVERSATION_OPEN_TAG]
    lines += [TURN_TEMPLATE.format(role=role, content=content) for role, content in turns]
    lines += [CONVERSATION_CLOSE_TAG, NEXT_TURN_INSTRUCTION]
    return "\n".join(lines)
