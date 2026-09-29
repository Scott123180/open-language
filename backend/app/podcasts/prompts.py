"""What the model is told: one standing prompt per episode, one short cue per line (research R5).

`prompts/templates.py` is not touched, so every roleplay prompt stays byte-identical (FR-034).
Languages are named ("Spanish"), never given as codes. The level's rules come last, through the
same renderer the roleplay partner uses, so a host line is held to the same limits (FR-026).
"""

from dataclasses import dataclass

from app.conversation_levels import ConversationLevel, with_partner_speech_rules
from app.podcasts.catalog import LEARNER_ROLES, PERSONALITIES, PodcastFormat
from app.podcasts.services.casting import Cast, Host
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
_INTENT_INSTRUCTIONS = {
    "open": "Open the show: welcome {label}, introduce the show and yourself.",
    "greet": "Greet {lead} and {label}, then introduce yourself.",
    "discuss": "React to the last line, in character.",
    "wrap_up": "Start wrapping up the topic, in character.",
    "sign_off": "Close the show: thank {label} and say goodbye.",
}


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


def learner_label_for(podcast_format: PodcastFormat, learner_name: str | None) -> str:
    """How the hosts refer to the learner: by name, as our guest, or as our listeners."""
    if not podcast_format.is_learner_speaking:
        return LISTENER_LABEL
    return learner_name or GUEST_LABEL


def build_standing_prompt(
    show: ShowBrief,
    cast: Cast,
    learner_label: str,
    languages: ConversationLanguages,
    level: ConversationLevel,
) -> str:
    sections = (
        _language_rule(languages),
        _show_section(show, learner_label),
        _hosts_section(cast),
        _line_rules(learner_label, languages),
    )
    return with_partner_speech_rules("\n\n".join(sections), level)


def render_cue(cue: LineCue, cast: Cast, learner_label: str) -> str:
    """The user turn before a host line. Re-rendered from stored facts, never stored itself."""
    instruction = _INTENT_INSTRUCTIONS[cue.intent].format(label=learner_label, lead=cast.lead.name)
    parts = [PRODUCER_NOTE_MARKER, f"Next: {cast.host(cue.speaker_slot).name}.", instruction]
    if cue.is_after_pass:
        parts.append(f"Don't wait for {learner_label}.")
    if cue.invites_learner:
        ask = "to settle it" if cue.is_settle_invite else "a question"
        parts.append(f"End by asking {learner_label} {ask}.")
    return " ".join(parts)


def _language_rule(languages: ConversationLanguages) -> str:
    target, native = languages.target_name, languages.native_name
    return (
        f"CRITICAL LANGUAGE RULE: Every line you write must be EXCLUSIVELY in {target}. "
        f"Zero {native} words, zero parenthetical translations like '(word)', "
        f"zero {native} explanations."
    )


def _show_section(show: ShowBrief, learner_label: str) -> str:
    template = _LEARNER_ROLE_SENTENCES.get(show.learner_role, _LEARNER_ROLE_SENTENCES["guest"])
    if learner_label == LISTENER_LABEL:
        template = _LISTENER_SENTENCE
    role = template.format(label=learner_label)
    return (
        "You write the lines of the hosts of a podcast, one line at a time.\n"
        f"Show: {show.title} — {show.premise} Topic: {show.topic}.\n"
        f"{role[0].upper()}{role[1:]}"
    )


def _hosts_section(cast: Cast) -> str:
    return "Hosts:\n" + "\n".join(_host_line(host) for host in cast.hosts)


def _host_line(host: Host) -> str:
    personality = PERSONALITIES[host.personality_id]
    role = host.show_role.replace("_", "-")
    angle = f" Angle: {host.angle}" if host.angle else ""
    return (
        f"- {host.name}, the {role}: {personality.description} "
        f"{personality.speaking_style}{angle}"
    )


def _line_rules(learner_label: str, languages: ConversationLanguages) -> str:
    target, native = languages.target_name, languages.native_name
    rules = (
        "Line rules:",
        "- Write only the words of the host named in the producer note, as that host.",
        "- No name label, no stage directions and no sound effects.",
        f"- Never write lines for another host or for {learner_label}.",
        f"- Address the learner as {learner_label}.",
        f"- If {learner_label} writes in {native}, answer in {target} and invite them, "
        f"in character, to use {target}.",
        "- Keep each line to a few sentences, in character, and on the show's topic.",
        "- Producer notes are never read aloud or mentioned.",
    )
    return "\n".join(rules)


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


def build_generator_prompt(idea: ShowIdea) -> str:
    """One structured request: judge the idea, then describe the show. Names are cast by code."""
    target, native = idea.languages.target_name, idea.languages.native_name
    sections = (
        f"You create podcast shows for a learner practising {target}. The show is spoken in "
        f"{target}, but write the title, premise, topic and angles in {native}.",
        f"Idea: {idea.idea}",
        *_personal_sections(idea),
        "First decide whether the idea is suitable. An idea that asks for hateful, sexual or "
        "dangerous content is not: set is_suitable to false, give a short decline_reason, and "
        "leave the other text fields empty.",
        "\n".join(_SHOW_FIELDS),
        "Personalities:\n" + "\n".join(_personality_lines()),
    )
    return "\n\n".join(sections)


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
