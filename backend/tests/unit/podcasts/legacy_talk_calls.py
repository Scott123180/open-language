"""011 T005: the one way the legacy pins render a prompt, a cue or a cue value.

The 007 one-off golden and the 010 series prompt tests call only these helpers, so 011's change
to `prompts.py` touches the pins in one place, never their expected text. Every render runs on
`LegacyTalk`, the talk of an episode with no settings row (research R1).
"""

from app.conversation_levels import ConversationLevel
from app.podcasts.prompts import (
    CueContext,
    PromptContext,
    ShowBrief,
    build_standing_prompt,
    render_cue,
)
from app.podcasts.services.casting import Cast
from app.podcasts.services.host_talk import LegacyTalk
from app.podcasts.services.series_snapshot import SeriesBrief
from app.podcasts.services.turn_policy import Ask, LineCue
from app.practice_languages import ConversationLanguages


def legacy_line_cue(
    speaker: str, intent: str, invites: bool, after_pass: bool, settle: bool
) -> LineCue:
    """A cue as 007 described it: who speaks, why, and whether the line invites the learner."""
    ask = Ask.REQUIRED if invites else Ask.NONE
    return LineCue(speaker, intent, ask, after_pass, settle)


def legacy_standing_prompt(
    *,
    show: ShowBrief,
    cast: Cast,
    learner_label: str,
    languages: ConversationLanguages,
    level: ConversationLevel,
    series: SeriesBrief | None = None,
) -> str:
    cues = CueContext(cast, learner_label, LegacyTalk(), series)
    return build_standing_prompt(PromptContext(show, languages, level, cues))


def legacy_cue(
    *, cue: LineCue, cast: Cast, learner_label: str, series: SeriesBrief | None = None
) -> str:
    return render_cue(cue, CueContext(cast, learner_label, LegacyTalk(), series))


def legacy_cue_context(
    cast: Cast, learner_label: str, series: SeriesBrief | None = None
) -> CueContext:
    """The cue context of an episode with no settings row."""
    return CueContext(cast, learner_label, LegacyTalk(), series)
