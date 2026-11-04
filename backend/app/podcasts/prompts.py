"""What the model is told: one standing prompt per episode, one short cue per line (research R5).

`prompts/templates.py` is not touched, so every roleplay prompt stays byte-identical (FR-034).
Languages are named ("Spanish"), never given as codes. How the hosts talk (line rules, the level
block, speaking styles, cue instructions and closings) comes from the episode's `HostTalk` (011
research R1), so a pre-011 episode keeps 007's and 010's text byte for byte.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.conversation_levels import ConversationLevel
from app.podcasts.catalog import (
    LEARNER_ROLES,
    MAX_POINTS_PER_EPISODE,
    PERSONALITIES,
    REMEMBERED_POINT_MAX_LENGTH,
    SUBJECT_SUGGESTIONS,
    SUGGESTION_SEEDS,
    TODAY_SUBJECT_MAX_LENGTH,
    PodcastFormat,
)
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.host_talk import HostTalk
from app.podcasts.services.series_snapshot import SeriesBrief
from app.podcasts.services.surprise import SurpriseIdea
from app.podcasts.services.turn_policy import LineCue
from app.practice_languages import ConversationLanguages

GUEST_LABEL = "our guest"
LISTENER_LABEL = "our listeners"
PRODUCER_NOTE_MARKER = "[Producer note, not part of the show]"

_LEARNER_ROLE_SENTENCES = {
    "guest": "{label} joins the show as a guest.",
    "co_host": "{label} joins the show as a co-host.",
    "caller": "{label} is a caller who has phoned in to the show.",
}
_LISTENER_SENTENCE = "The hosts talk to each other; {label} are listening."
_SERIES_RULES = (
    "Series rules:",
    "- Choose a subject within the show's topic that is not in the covered list.",
    "- Never claim to remember anything not listed here, such as earlier advice or guests.",
)
_REFER_BACK_RULE = "- Where it fits, refer back to one of these points, accurately."


@dataclass(frozen=True, slots=True)
class ShowIdea:
    """What the learner asked the generator for (research R9)."""

    idea: str
    languages: ConversationLanguages
    interests: tuple[str, ...] = ()
    avoid_titles: tuple[str, ...] = ()
    learner_name: str | None = None


@dataclass(frozen=True, slots=True)
class ShowBrief:
    title: str
    premise: str
    topic: str
    learner_role: str


@dataclass(frozen=True, slots=True)
class CueContext:
    """What every cue of an episode is rendered with."""

    cast: Cast
    learner_label: str
    talk: HostTalk
    series: SeriesBrief | None = None
    """None for a one-off episode."""


@dataclass(frozen=True, slots=True)
class PromptContext:
    """What an episode's standing prompt is rendered with."""

    show: ShowBrief
    languages: ConversationLanguages
    level: ConversationLevel
    cues: CueContext


def learner_label_for(podcast_format: PodcastFormat, learner_name: str | None) -> str:
    """How the hosts refer to the learner: by name, as our guest, or as our listeners."""
    if not podcast_format.is_learner_speaking:
        return LISTENER_LABEL
    return learner_name or GUEST_LABEL


def build_standing_prompt(context: PromptContext) -> str:
    """A one-off's prompt is 007's, byte for byte; a series episode's adds its series section."""
    cues, label = context.cues, context.cues.learner_label
    sections = (
        _language_rule(context.languages),
        _show_section(context.show, label, cues.talk.today_subject),
        _hosts_section(cues.cast, cues.talk),
        _covered_role_section(cues.cast, cues.talk),
        _series_section(cues.series, label, cues.talk) if cues.series is not None else None,
        cues.talk.line_rules(label, context.languages, cues.cast),
    )
    joined = "\n\n".join(section for section in sections if section is not None)
    return cues.talk.speech_rules(joined, context.level)


def render_cue(cue: LineCue, context: CueContext) -> str:
    """The user turn before a host line. Re-rendered from stored facts, never stored itself."""
    talk, label = context.talk, context.learner_label
    instruction = talk.instruction(cue, context.cast, label, context.series)
    parts = [
        PRODUCER_NOTE_MARKER,
        f"Next: {context.cast.host(cue.speaker_slot).name}.",
        instruction,
    ]
    if cue.is_after_pass:
        parts.append(f"Don't wait for {label}.")
    closing = talk.closing(cue, label)
    if closing:
        parts.append(closing)
    return " ".join(parts)


def _series_section(series: SeriesBrief, learner_label: str, talk: HostTalk) -> str:
    """What the hosts remember, from the episode's snapshot only (010 research R5, R7).

    Every remembered point is listed, newest first: the stored points fit the section whole,
    because their text budget is enforced when they are written."""
    snapshot = series.snapshot
    lines = [_episode_sentence(series.episode_number)]
    if snapshot.topics_covered:
        lines.append(f"Earlier episodes covered: {'; '.join(snapshot.topics_covered)}.")
    if snapshot.about_learner:
        verb = "have" if learner_label == LISTENER_LABEL else "has"
        lines.append(f"What {learner_label} {verb} told you before:")
        lines.extend(f"- {point}" for point in snapshot.about_learner)
    rules = _series_rules(bool(snapshot.topics_covered or snapshot.about_learner))
    lines.extend(_with_chosen_subject(rules, learner_label, talk.today_subject))
    lines.extend(_new_host_rule(name) for name in series.new_host_names)
    return "\n".join(lines)


def _with_chosen_subject(
    rules: tuple[str, ...], learner_label: str, subject: str | None
) -> tuple[str, ...]:
    """Today's subject replaces the covered-list rule: the learner chose it (011 FR-010)."""
    if subject is None:
        return rules
    chosen = f"- Today's subject was chosen by {learner_label}: talk about it even if it was covered before."
    return tuple(chosen if rule == _SERIES_RULES[1] else rule for rule in rules)


def _new_host_rule(name: str) -> str:
    return (
        f"- {name} is new to the show and does not know the earlier episodes: introduce "
        f"{name} as new."
    )


def _episode_sentence(episode_number: int) -> str:
    if episode_number == 1:
        return "This is the first episode of a continuing show."
    return f"This is episode {episode_number} of a continuing show."


def _series_rules(has_points: bool) -> tuple[str, ...]:
    if not has_points:
        return _SERIES_RULES
    return (_SERIES_RULES[0], _REFER_BACK_RULE, *_SERIES_RULES[1:])


def _language_rule(languages: ConversationLanguages) -> str:
    target, native = languages.target_name, languages.native_name
    return (
        f"CRITICAL LANGUAGE RULE: Every line you write must be EXCLUSIVELY in {target}. "
        f"Zero {native} words, zero parenthetical translations like '(word)', "
        f"zero {native} explanations."
    )


def _show_section(show: ShowBrief, learner_label: str, subject: str | None) -> str:
    template = _LEARNER_ROLE_SENTENCES.get(show.learner_role, _LEARNER_ROLE_SENTENCES["guest"])
    if learner_label == LISTENER_LABEL:
        template = _LISTENER_SENTENCE
    role = template.format(label=learner_label)
    section = (
        "You write the lines of the hosts of a podcast, one line at a time.\n"
        f"Show: {show.title} — {show.premise} Topic: {show.topic}.\n"
        f"{role[0].upper()}{role[1:]}"
    )
    return section + _subject_sentence(learner_label, subject)


def _subject_sentence(learner_label: str, subject: str | None) -> str:
    if subject is None:
        return ""
    return (
        f"\nToday's subject, chosen by {learner_label}: {subject}. Talk about it within the "
        "show's topic."
    )


def _hosts_section(cast: Cast, talk: HostTalk) -> str:
    return "Hosts:\n" + "\n".join(_host_line(host, talk) for host in cast.hosts)


def _covered_role_section(cast: Cast, talk: HostTalk) -> str | None:
    """One host stands in for the show's absent second host (011 research R6)."""
    if cast.second is not None or talk.covered_personality is None:
        return None
    covered = PERSONALITIES[talk.covered_personality]
    return (
        f"This show usually has a second host, the {covered.label}: {covered.description} "
        f"Today you play that part too: {talk.speaking_style(covered)}"
    )


def _host_line(host: Host, talk: HostTalk) -> str:
    personality = PERSONALITIES[host.personality_id]
    role = host.show_role.replace("_", "-")
    angle = f" Angle: {host.angle}" if host.angle else ""
    return (
        f"- {host.name}, the {role}: {personality.description} "
        f"{talk.speaking_style(personality)}{angle}"
    )


# --- the show generator (research R9) -----------------------------------------------------

_HOST_SCHEMA = {
    "type": "object",
    "properties": {
        "personality": {"type": "string", "enum": list(PERSONALITIES)},
        "angle": {"type": "string"},
    },
    "required": ["personality", "angle"],
}
SHOW_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_suitable": {"type": "boolean"},
        "decline_reason": {"type": "string"},
        "title": {"type": "string"},
        "premise": {"type": "string"},
        "topic": {"type": "string"},
        "learner_role": {"type": "string", "enum": list(LEARNER_ROLES)},
        "hosts": {"type": "array", "minItems": 2, "maxItems": 2, "items": _HOST_SCHEMA},
    },
    "required": [
        "is_suitable",
        "decline_reason",
        "title",
        "premise",
        "topic",
        "learner_role",
        "hosts",
    ],
}
_SHOW_FIELDS = (
    "If it is suitable, fill in:",
    "- title: a short, catchy show title of at most eight words.",
    "- premise: one sentence on what the show is about.",
    "- topic: a few words naming the topic.",
    "- learner_role: how the learner joins the show: guest, co_host or caller.",
    "- hosts: exactly two hosts, each with a different personality from the list below and a "
    "one-line angle: that host's own view of the idea.",
)


_SUITABILITY_RULE = (
    "First decide whether the idea is suitable. An idea that asks for hateful, sexual or "
    "dangerous content is not: set is_suitable to false, give a short decline_reason, and "
    "leave the other text fields empty."
)


def build_generator_prompt(idea: ShowIdea) -> str:
    """One structured request: judge the idea, then describe the show. Names are cast by code."""
    sections = (
        _creator_intro(idea.languages, "The show is"),
        f"Idea: {idea.idea}",
        *_personal_sections(idea),
        _SUITABILITY_RULE,
        "\n".join(_SHOW_FIELDS),
        "Personalities:\n" + "\n".join(_personality_lines()),
    )
    return "\n\n".join(sections)


def _creator_intro(languages: ConversationLanguages, spoken: str) -> str:
    target, native = languages.target_name, languages.native_name
    return (
        f"You create podcast shows for a learner practising {target}. {spoken} spoken in "
        f"{target}, but write the title, premise, topic and angles in {native}."
    )


def _personal_sections(idea: ShowIdea) -> tuple[str, ...]:
    sections = []
    if idea.interests:
        sections.append(
            f"The learner is interested in: {', '.join(idea.interests)}. Where it fits the "
            "idea, let the hosts' angles draw on these."
        )
    if idea.avoid_titles:
        titles = ", ".join(f'"{title}"' for title in idea.avoid_titles)
        sections.append(f"Make a clearly different version: do not reuse these titles: {titles}.")
    return tuple(sections)


def _personality_lines() -> list[str]:
    return [f"- {key}: {p.description}" for key, p in PERSONALITIES.items()]


# --- series memory (010 research R6) --------------------------------------------------------

_POINT_SCHEMA = {
    "type": "object",
    "properties": {
        "conversation_language": {"type": "string"},
        "english": {"type": "string"},
    },
    "required": ["conversation_language", "english"],
}
MEMORY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": _POINT_SCHEMA,
        "about_learner": {
            "type": "array",
            "maxItems": MAX_POINTS_PER_EPISODE,
            "items": _POINT_SCHEMA,
        },
    },
    "required": ["topic", "about_learner"],
}
LEARNER_SPEAKER = "Learner"


def memory_prompt(
    chunk: str,
    host_names: Sequence[str],
    remembered: Sequence[str],
    languages: ConversationLanguages,
) -> str:
    """One structured request: what to remember from part of an episode (contracts §9)."""
    target = languages.target_name
    sections = (
        f"You keep the notes of a podcast's hosts, so they can remember a learner of {target} "
        f"in later episodes. Below is part of one episode, in {target}. The hosts are "
        f"{' and '.join(host_names)}; the learner's lines are labelled {LEARNER_SPEAKER}.",
        f"Transcript:\n{chunk}",
        _already_remembered(remembered),
        _memory_rules(target),
    )
    return "\n\n".join(sections)


def _already_remembered(remembered: Sequence[str]) -> str:
    if not remembered:
        return "Already remembered: nothing yet."
    listed = "\n".join(f"- {point}" for point in remembered)
    return f"Already remembered (do not repeat these):\n{listed}"


def _memory_rules(target: str) -> str:
    rules = (
        "Rules:",
        "- topic: what this part of the episode was mostly about, as one short phrase of at "
        "most six words. Always fill it in.",
        f"- about_learner: at most {MAX_POINTS_PER_EPISODE} things the learner said about "
        "themselves (likes, plans, experiences, opinions), only from lines labelled "
        f"{LEARNER_SPEAKER}.",
        "- Never note anything a host said, nor the learner agreeing, greeting, reacting or "
        "asking a question: only facts about the learner's own life.",
        "- No guesses: note only what was clearly said. Use an empty list when there is "
        "nothing.",
        f"- Write every point twice: conversation_language in {target}, about the learner in "
        'the third person; english in English, speaking to the learner as "You".',
        f"- Keep each text under {REMEMBERED_POINT_MAX_LENGTH} characters.",
    )
    return "\n".join(rules)


# --- Find a new show (010 research R10) ---------------------------------------------------

DISCOVERY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "shows": {
            "type": "array",
            "minItems": 1,
            "maxItems": SUGGESTION_SEEDS,
            "items": SHOW_JSON_SCHEMA,
        }
    },
    "required": ["shows"],
}


def discovery_prompt(
    seeds: Sequence[SurpriseIdea], avoid_titles: Sequence[str], languages: ConversationLanguages
) -> str:
    """One structured request for one show per seed, judged and described as the generator does."""
    ideas = "\n".join(f"{number}. {seed.idea}" for number, seed in enumerate(seeds, start=1))
    sections = [
        _creator_intro(languages, "Every show is"),
        f"Make one show for each idea below, in this order:\n{ideas}",
        _SUITABILITY_RULE.replace("the idea is", "each idea is"),
        "\n".join(_SHOW_FIELDS),
        "Personalities:\n" + "\n".join(_personality_lines()),
    ]
    if avoid_titles:
        titles = ", ".join(f'"{title}"' for title in avoid_titles)
        sections.insert(2, f"Do not reuse these titles, or anything close to them: {titles}.")
    return "\n\n".join(sections)


# --- Today's subject (011 research R14, R20) ----------------------------------------------

SUBJECT_CHECK_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_suitable": {"type": "boolean"},
        "decline_reason": {"type": "string"},
    },
    "required": ["is_suitable", "decline_reason"],
}
SUBJECT_SUGGESTIONS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "subjects": {
            "type": "array",
            "minItems": 1,
            "maxItems": SUBJECT_SUGGESTIONS,
            "items": {"type": "string"},
        }
    },
    "required": ["subjects"],
}
_SUBJECT_SUITABILITY_RULE = (
    "Decide whether the subject is suitable. A subject that asks for hateful, sexual or "
    "dangerous content is not: set is_suitable to false and give a short decline_reason. "
    "Otherwise set is_suitable to true and leave decline_reason empty."
)


def subject_check_prompt(subject: str, languages: ConversationLanguages) -> str:
    """One structured request: is the learner's subject suitable for an episode (R14)?"""
    sections = (
        f"A learner practising {languages.target_name} chose the subject of one episode of a "
        "podcast.",
        f"Subject: {subject}",
        _SUBJECT_SUITABILITY_RULE,
    )
    return "\n\n".join(sections)


def subject_suggestion_prompt(request: "SubjectPromptRequest") -> str:
    """One structured request for up to three new subjects for an episode (R20)."""
    show, native = request.show, request.languages.native_name
    sections = [
        f"You suggest subjects for one episode of a podcast for a learner practising "
        f"{request.languages.target_name}. Write each subject in {native}, at most "
        f"{TODAY_SUBJECT_MAX_LENGTH} characters.",
        f"Show: {show.title} — {show.premise} Topic: {show.topic}.",
        *_subject_context(request),
        "Every subject must be suitable: never hateful, sexual or dangerous content.",
        f"Give up to {SUBJECT_SUGGESTIONS} subjects, each one concrete question or thing "
        "within the show's topic.",
    ]
    return "\n\n".join(sections)


def _subject_context(request: "SubjectPromptRequest") -> list[str]:
    sections = []
    if request.interests:
        sections.append(
            f"The learner is interested in: {', '.join(request.interests)}. Where it fits the "
            "show, let a subject draw on these."
        )
    if request.covered:
        sections.append(f"Earlier episodes covered (do not repeat): {'; '.join(request.covered)}.")
    if request.avoid:
        sections.append(f"Already suggested (do not repeat): {'; '.join(request.avoid)}.")
    return sections


class SubjectPromptRequest(Protocol):
    """What a subject suggestion prompt reads; `SubjectRequest` provides it."""

    show: ShowBrief
    languages: ConversationLanguages
    interests: tuple[str, ...]
    covered: tuple[str, ...]
    avoid: tuple[str, ...]
