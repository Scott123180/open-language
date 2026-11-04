"""HostTalk: how one episode's hosts talk, chosen once per episode (research R1).

`TurnPolicy`, the standing prompt, the cues and the replayed history all ask the episode's
`HostTalk`. An episode with no settings row is pre-011 and gets `LegacyTalk`, which is 007's and
010's behaviour moved here unchanged, so their prompts, cues and histories stay byte for byte
(FR-025). `host_talk_for` is the only place a settings row becomes behaviour.
"""

import random
from abc import ABC, abstractmethod

from app.conversation_levels import (
    ConversationLevel,
    with_partner_speech_rules,
    with_sentence_rules,
)
from app.podcasts.catalog import (
    ADDRESS_ALL,
    BRIEF_INTENTS,
    DISCUSSION_INTENTS,
    INVITE_DEADLINE,
    QUESTION_MARK,
    Personality,
)
from app.podcasts.services.casting import Cast
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.series_snapshot import SeriesBrief
from app.podcasts.services.turn_policy import (
    ANSWER,
    DISCUSS,
    FOLLOW_UP,
    LEARNER,
    SIGN_OFF,
    WRAP_UP,
    Ask,
    EpisodeState,
    InvitePoint,
    LineCue,
    LineFacts,
    ends_with_question,
)
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
FOLLOW_UP_QUESTIONS = 2
"""A learner line with this many questions gets a follow-up after its answer (R4)."""

_CONFIGURED_INSTRUCTIONS = {
    "react": "React to the last line and add something of your own, {phrase}.",
    "explain": (
        "Explain one thing about today's subject step by step, {phrase}: what it is, how it "
        "works, and an everyday example."
    ),
    "story": "Tell a short story or example from your own life about today's subject, {phrase}.",
    "follow_up": "Answer the other question {label} asked before, step by step, {phrase}.",
    "wrap_up": (
        "Start wrapping up {phrase}: tell {label} the show is nearly over, and sum up today's "
        "subject in one sentence."
    ),
    "sign_off": (
        "React briefly to the last line, then close the show {phrase}: thank {label} and say "
        "goodbye."
    ),
}
_ANSWER = "Answer {asker}'s question first, step by step, {phrase}; if there were two, answer one."
_FOR_BOTH = " If it was for you both, answer, then ask {other} too."
_OPEN_WITH_SUBJECT = "introduce today's subject"
_OPEN_WITHOUT_SUBJECT = "name today's subject: one concrete question within the topic"
_NOT_COVERED = ", not in the covered list"
_DO_NOT_ASK = "Don't ask {label} anything this time."


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
    def ask(self, point: InvitePoint, rng: random.Random) -> Ask:
        """The `Ask` of the host line at `point`."""

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
    if settings is None:
        return LegacyTalk()
    return ConfiguredTalk(settings)


class LegacyTalk(HostTalk):
    """007's and 010's host talk, moved here without a change (FR-025)."""

    def ask(self, point: InvitePoint, rng: random.Random) -> Ask:
        podcast_format, run = point.format, point.run
        if not podcast_format.is_learner_speaking:
            return Ask.NONE
        if podcast_format.host_count == 1 or run >= podcast_format.invite_deadline:
            return Ask.REQUIRED
        if point.is_unbalancing:
            return Ask.NONE
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


class ConfiguredTalk(HostTalk):
    """011's host talk, from the episode's frozen settings (research R2–R6, R19–R22)."""

    def __init__(self, settings: EpisodeSettings) -> None:
        self._settings = settings

    @property
    def today_subject(self) -> str | None:
        return self._settings.today_subject

    @property
    def covered_personality(self) -> str | None:
        return self._settings.covered_personality

    def ask(self, point: InvitePoint, rng: random.Random) -> Ask:
        """Allowed on a hazard hit, required at the deadline and on every Often line (R3)."""
        podcast_format, run = point.format, point.run
        if not podcast_format.is_learner_speaking:
            return Ask.NONE
        if podcast_format.host_count == 2 and point.intent in (_OPEN, _GREET):
            return Ask.NEVER
        hazards = self._settings.invite_frequency.hazards
        hazard = hazards[min(run, len(hazards)) - 1]
        if run >= INVITE_DEADLINE or hazard >= 1:
            return Ask.REQUIRED
        if point.is_unbalancing:
            return Ask.NONE
        return Ask.ALLOWED if rng.random() < hazard else Ask.NONE

    def invitation(self, ask: Ask, addressee: str | None) -> bool:
        """A required line always invites; any other invites when it is for the learner (R19)."""
        if ask is Ask.NEVER:
            return False
        return ask is Ask.REQUIRED or addressee == LEARNER

    def stored_addressing(self, ask: Ask, addressee: str | None) -> tuple[str | None, str | None]:
        return ask.value, addressee

    def discussion_intent(self, state: EpisodeState, rng: random.Random) -> str:
        """Questions are answered first; after the wrap-up the hosts sign off (R4, R21)."""
        if any(line.intent == WRAP_UP for line in state.host_lines):
            return ANSWER if _is_learner_question(state.last) else SIGN_OFF
        if _is_learner_question(state.last) or _is_question_to_other_host(state.last):
            return ANSWER
        if _is_follow_up_due(state.lines):
            return FOLLOW_UP
        return self._drawn_intent(rng)

    def _drawn_intent(self, rng: random.Random) -> str:
        draw, cumulative = rng.random(), 0.0
        for intent, weight in zip(DISCUSSION_INTENTS, self._settings.style.weights, strict=True):
            cumulative += weight
            if draw < cumulative:
                return intent
        return DISCUSSION_INTENTS[-1]

    def line_rules(self, label: str, languages: ConversationLanguages, cast: Cast) -> str:
        target, native = languages.target_name, languages.native_name
        count = self._settings.line_length.range_phrase
        rules = (
            "Line rules:",
            "- Write only the words of the host named in the producer note, as that host.",
            "- No name label, no stage directions and no sound effects.",
            f"- Never write lines for another host or for {label}.",
            f"- Address the learner as {label}.",
            f"- If {label} writes in {native}, answer in {target} and invite them, "
            f"in character, to use {target}.",
            f"- Each host line has {count} unless the producer note says otherwise, each "
            "within the rules at the end. Stay in character.",
            *_question_rules(label),
            "- Producer notes are never read aloud or mentioned.",
            _address_rule(label, cast),
        )
        return "\n".join(rules)

    def speech_rules(self, prompt: str, level: ConversationLevel) -> str:
        return with_sentence_rules(prompt, level)

    def speaking_style(self, personality: Personality) -> str:
        return personality.configured_speaking_style or personality.speaking_style

    def instruction(self, cue: LineCue, cast: Cast, label: str, series: SeriesBrief | None) -> str:
        phrase = self._phrase(cue.intent)
        if cue.intent == _OPEN:
            return self._opening(label, series, phrase)
        if cue.intent == _GREET:
            return _greeting(cue, cast, label, series, phrase)
        if cue.intent == ANSWER:
            return _answer(cue, cast, label, phrase)
        return _CONFIGURED_INSTRUCTIONS[cue.intent].format(label=label, phrase=phrase)

    def _phrase(self, intent: str) -> str:
        length = self._settings.line_length
        return length.brief_phrase if intent in BRIEF_INTENTS else length.full_phrase

    def _opening(self, label: str, series: SeriesBrief | None, phrase: str) -> str:
        """The opening names one subject: the learner's, or one the host chooses (R20)."""
        subject = _OPEN_WITH_SUBJECT if self.today_subject else _OPEN_WITHOUT_SUBJECT
        if series is None or series.episode_number == 1:
            return (
                f"Open the show {phrase}: welcome {label}, introduce the show and yourself, "
                f"and {subject}."
            )
        covered = "" if self.today_subject else _NOT_COVERED
        return series_open(label, series, f" {phrase}", f", and {subject}{covered}")

    def closing(self, cue: LineCue, label: str) -> str:
        if not cue.ask.may_invite:
            return _DO_NOT_ASK.format(label=label)
        question = "to settle it" if cue.is_settle_invite else "one question"
        if cue.ask is Ask.ALLOWED:
            return (
                f"If it fits, then end by asking {label} {question}; if not, ask {label} nothing."
            )
        if cue.intent == WRAP_UP:
            return f"Then ask {label} for one last thought on it."
        return f"Then end by asking {label} {question}."

    def replayed_line(self, text: str, addressee: str | None, cast: Cast, label: str) -> str:
        """The stored text with its canonical tag, so a rebuilt session keeps the pattern."""
        return f"{text} [@{_addressee_name(addressee, cast, label)}]"


def series_open(label: str, series: SeriesBrief, phrase: str = "", subject: str = "") -> str:
    """010's opening of a series episode after the first; 011 adds a length and a subject."""
    snapshot = series.snapshot
    recall = snapshot.topics_covered or snapshot.about_learner
    recollection = ", and bring up one thing from earlier episodes" if recall else ""
    opening = (
        f"Open the show{phrase}: welcome {label} back, say the show is continuing with episode "
        f"{series.episode_number}{recollection}{subject}."
    )
    if series.is_new_host(_LEAD):
        return f"{opening} Introduce yourself as the show's new host."
    if series.guest_name is not None and series.guest_slot != _LEAD:
        return f"{opening} Introduce {series.guest_name} as today's guest."
    return opening


def _greeting(cue: LineCue, cast: Cast, label: str, series: SeriesBrief | None, phrase: str) -> str:
    return f"Greet {cast.lead.name} and {label} {phrase}, then {_yourself(cue, series)}."


def _yourself(cue: LineCue, series: SeriesBrief | None) -> str:
    if series is not None and series.guest_slot == cue.speaker_slot:
        return "introduce yourself as today's guest"
    if series is not None and series.is_new_host(cue.speaker_slot):
        return "introduce yourself as new to the show"
    return "introduce yourself"


def _answer(cue: LineCue, cast: Cast, label: str, phrase: str) -> str:
    asker = _addressee_name(cue.asker, cast, label)
    answer = _ANSWER.format(asker=asker, phrase=phrase)
    if not cue.is_for_both or cast.second is None:
        return answer
    other = next(host.name for host in cast.hosts if host.slot != cue.speaker_slot)
    return answer + _FOR_BOTH.format(other=other)


def _question_rules(label: str) -> tuple[str, ...]:
    return (
        f"- When {label} asks a question, answer it first; never answer only with a question.",
        f"- Ask {label} something only when the producer note says so, after the line's "
        "sentences, and never what they have already answered.",
        "- The episode has one subject, named in the opening: stay on it until the wrap-up.",
    )


def _address_rule(label: str, cast: Cast) -> str:
    """The last line rule: every line ends with who it is for (research R19)."""
    hosts = ""
    if cast.second is not None:
        hosts = f" [@{cast.lead.name}] or [@{cast.second.name}] for the other host,"
    return (
        f"- End every line with who it is for: [@{label}],{hosts} or [@{ADDRESS_ALL}] for no "
        "one in particular. The brackets are never read aloud."
    )


def _addressee_name(addressee: str | None, cast: Cast, label: str) -> str:
    if addressee == LEARNER:
        return label
    names = {host.slot: host.name for host in cast.hosts}
    return names.get(addressee, ADDRESS_ALL)


def _is_learner_question(line: LineFacts | None) -> bool:
    return line is not None and not line.is_host and QUESTION_MARK in line.text


def _is_question_to_other_host(line: LineFacts | None) -> bool:
    if line is None or not line.is_host or line.addressee in (None, LEARNER):
        return False
    return line.addressee != line.speaker and ends_with_question(line.text)


def _is_follow_up_due(lines: tuple[LineFacts, ...]) -> bool:
    """The one host line since a learner line with two questions answered the first (R4)."""
    if len(lines) < 2 or not lines[-1].is_host or lines[-1].intent != ANSWER:
        return False
    asked = lines[-2]
    return not asked.is_host and asked.text.count(QUESTION_MARK) >= FOLLOW_UP_QUESTIONS
