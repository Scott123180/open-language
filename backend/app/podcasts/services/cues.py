"""An episode's saved history for the conversation engine (research R3).

Host lines are assistant turns, learner lines are user turns, and before every host line sits the
producer cue that asked for it. Cues are re-rendered from the stored facts by the same
`render_cue` that wrote them, so a rebuilt session sees the history byte for byte.
"""

from collections.abc import Sequence

from app.podcasts.prompts import CueContext, render_cue
from app.podcasts.services.turn_policy import (
    LineCue,
    LineFacts,
    follows_pass,
    is_settle_moment,
)
from app.services.conversation import SavedTurn

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
LINE_TURN_PREFIX = "p"
CUE_TURN_PREFIX = "c"


def line_turn_id(message_id: int) -> str:
    return f"{LINE_TURN_PREFIX}{message_id}"


def stored_cue(lines: Sequence[LineFacts], index: int) -> LineCue:
    """The cue that produced the host line at `index`, rebuilt from what was stored."""
    line, previous = lines[index], lines[:index]
    return LineCue(
        speaker_slot=line.speaker,
        intent=line.intent,
        ask=line.ask,
        is_after_pass=follows_pass(previous),
        is_settle_invite=line.ask.may_invite and is_settle_moment(previous),
    )


def episode_history(lines: Sequence[LineFacts], context: CueContext) -> tuple[SavedTurn, ...]:
    turns: list[SavedTurn] = []
    for index, line in enumerate(lines):
        if line.is_host:
            turns.append(_cue_turn(index, stored_cue(lines, index), context))
            turns.append(_host_turn(line, context))
        else:
            text = f"{context.learner_label}: {line.text}"
            turns.append(SavedTurn(line_turn_id(line.message_id), USER_ROLE, text))
    return tuple(turns)


def next_turn_history(
    lines: Sequence[LineFacts], context: CueContext, cue: LineCue
) -> tuple[SavedTurn, ...]:
    """The saved history, ending with a fresh cue for the next line (a user turn)."""
    return (*episode_history(lines, context), _cue_turn(len(lines), cue, context))


def _host_turn(line: LineFacts, context: CueContext) -> SavedTurn:
    replayed = context.talk.replayed_line(
        line.text, line.addressee, context.cast, context.learner_label
    )
    return SavedTurn(line_turn_id(line.message_id), ASSISTANT_ROLE, replayed)


def _cue_turn(position: int, cue: LineCue, context: CueContext) -> SavedTurn:
    return SavedTurn(f"{CUE_TURN_PREFIX}{position}", USER_ROLE, render_cue(cue, context))
