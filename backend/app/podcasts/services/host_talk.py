"""HostTalk: how one episode's hosts talk, chosen once per episode (research R1).

`TurnPolicy`, the standing prompt, the cues and the replayed history all ask the episode's
`HostTalk`. An episode with no settings row is pre-011 and gets `LegacyTalk`, which is 007's and
010's behaviour moved here unchanged, so their prompts, cues and histories stay byte for byte
(FR-025). `host_talk_for` is the only place a settings row becomes behaviour.
"""

import random
from abc import ABC, abstractmethod

from app.conversation_levels import ConversationLevel, with_partner_speech_rules
from app.podcasts.catalog import Personality, PodcastFormat
from app.podcasts.services.casting import Cast
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.series_snapshot import SeriesBrief
from app.podcasts.services.turn_policy import DISCUSS, Ask, EpisodeState, LineCue
from app.practice_languages import ConversationLanguages

LEGACY_PANEL_HAZARDS = (0.25, 0.45, 0.6)
"""Panel before 011: the chance the 1st, 2nd and 3rd host line since the learner invites them."""

_LEGACY_INSTRUCTIONS = {
    "open": "Open the show: welcome {label}, introduce the show and yourself.",
    "greet": "Greet {lead} and {label}, then introduce yourself.",
    "discuss": "React to the last line, in character.",
    "wrap_up": "Start wrapping up the topic, in character.",
    "sign_off": "Close the show: thank {label} and say goodbye.",
}
_OPEN, _GREET, _LEAD = "open", "greet", "lead"


class HostTalk(ABC):
    """What the policy, the prompt and the history need to know about how hosts talk."""

    @property
    def today_subject(self) -> str | None:
        """The subject the learner chose for this episode, if any (FR-010)."""
        return None

    @property
    def covered_personality(self) -> str | None:
        """One host: the absent second host's personality the one host covers (R6)."""
        return None

    @abstractmethod
    def ask(self, run: int, podcast_format: PodcastFormat, rng: random.Random, intent: str) -> Ask:
        """The `Ask` of the host line at position `run` since the learner last spoke."""

    @abstractmethod
    def invitation(self, ask: Ask, addressee: str | None) -> bool:
        """Whether the written line hands the turn to the learner (R19)."""

    @abstractmethod
    def stored_addressing(self, ask: Ask, addressee: str | None) -> tuple[str | None, str | None]:
        """The ask and addressee a written line stores; legacy lines store neither."""

    @abstractmethod
    def discussion_intent(self, state: EpisodeState, rng: random.Random) -> str:
        """Which kind of line the next discussion line is (R4, R21)."""

    @abstractmethod
    def line_rules(self, label: str, languages: ConversationLanguages, cast: Cast) -> str:
        """The standing prompt's line rules."""

    @abstractmethod
    def speech_rules(self, prompt: str, level: ConversationLevel) -> str:
        """The prompt with the level's speech block appended (R2)."""

    @abstractmethod
    def speaking_style(self, personality: Personality) -> str:
        """How a host of this personality speaks, in the hosts section (R22)."""

    @abstractmethod
    def instruction(self, cue: LineCue, cast: Cast, label: str, series: SeriesBrief | None) -> str:
        """What the host is asked to do in this line."""

    @abstractmethod
    def closing(self, cue: LineCue, label: str) -> str:
        """The cue's last sentence, from its `Ask`; empty when there is none."""

    @abstractmethod
    def replayed_line(self, text: str, addressee: str | None, cast: Cast, label: str) -> str:
        """A stored host line as the rebuilt history gives it back to the model (R19)."""


def host_talk_for(settings: EpisodeSettings | None) -> HostTalk:
    """The one place an episode's settings become behaviour: none means a pre-011 episode."""
    return LegacyTalk()


class LegacyTalk(HostTalk):
    """007's and 010's host talk, moved here without a change (FR-025)."""

    def ask(self, run: int, podcast_format: PodcastFormat, rng: random.Random, intent: str) -> Ask:
        if not podcast_format.is_learner_speaking:
            return Ask.NONE
        if podcast_format.host_count == 1 or run >= podcast_format.invite_deadline:
            return Ask.REQUIRED
        hazard = LEGACY_PANEL_HAZARDS[min(run, len(LEGACY_PANEL_HAZARDS)) - 1]
        return Ask.REQUIRED if rng.random() < hazard else Ask.NONE

    def invitation(self, ask: Ask, addressee: str | None) -> bool:
        return ask is Ask.REQUIRED

    def stored_addressing(self, ask: Ask, addressee: str | None) -> tuple[str | None, str | None]:
        """Lines are stored as 010 stored them: their ask is read back from the invitation."""
        return None, None

    def discussion_intent(self, state: EpisodeState, rng: random.Random) -> str:
        return DISCUSS

    def line_rules(self, label: str, languages: ConversationLanguages, cast: Cast) -> str:
        target, native = languages.target_name, languages.native_name
        rules = (
            "Line rules:",
            "- Write only the words of the host named in the producer note, as that host.",
            "- No name label, no stage directions and no sound effects.",
            f"- Never write lines for another host or for {label}.",
            f"- Address the learner as {label}.",
            f"- If {label} writes in {native}, answer in {target} and invite them, "
            f"in character, to use {target}.",
            "- Keep each line to a few sentences, in character, and on the show's topic.",
            "- Producer notes are never read aloud or mentioned.",
        )
        return "\n".join(rules)

    def speech_rules(self, prompt: str, level: ConversationLevel) -> str:
        return with_partner_speech_rules(prompt, level)

    def speaking_style(self, personality: Personality) -> str:
        return personality.speaking_style

    def instruction(self, cue: LineCue, cast: Cast, label: str, series: SeriesBrief | None) -> str:
        """007's instruction, or a series episode's variant (010)."""
        plain = _LEGACY_INSTRUCTIONS[cue.intent].format(label=label, lead=cast.lead.name)
        if series is None:
            return plain
        if cue.intent == _OPEN and series.episode_number > 1:
            return series_open(label, series)
        if cue.intent == _GREET and series.is_new_host(cue.speaker_slot):
            return (
                f"Greet {cast.lead.name} and {label}, then introduce yourself as new to the show."
            )
        return plain

    def closing(self, cue: LineCue, label: str) -> str:
        if cue.ask is not Ask.REQUIRED:
            return ""
        ask = "to settle it" if cue.is_settle_invite else "a question"
        return f"End by asking {label} {ask}."

    def replayed_line(self, text: str, addressee: str | None, cast: Cast, label: str) -> str:
        return text


def series_open(label: str, series: SeriesBrief) -> str:
    """010's opening of a series episode after the first."""
    snapshot = series.snapshot
    recall = snapshot.topics_covered or snapshot.about_learner
    recollection = ", and bring up one thing from earlier episodes" if recall else ""
    opening = (
        f"Open the show: welcome {label} back, say the show is continuing with episode "
        f"{series.episode_number}{recollection}."
    )
    if series.is_new_host(_LEAD):
        return f"{opening} Introduce yourself as the show's new host."
    return opening
