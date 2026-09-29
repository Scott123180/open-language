"""Podcast formats, lengths, personalities and ready-made shows: the one place each is defined.

Behaviour reads descriptor fields, never ids, so a new format, length, personality or show is a
catalogue entry (FR-004, OCP). Show titles and premises are English interface text, like
scenario titles; hosts' names and voices are cast per language, not stored here.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

PODCAST_SCENARIO_ID = "podcast"
"""The `conversations.scenario_id` of every episode."""

MAX_PARTICIPANTS = 3
LEAD_SLOT = "lead"
SECOND_SLOT = "second"
HOST_SLOTS = (LEAD_SLOT, SECOND_SLOT)
LEARNER_ROLES = ("guest", "co_host", "caller")
SHOW_ROLES = ("host", "co_host", "guest_expert")
SHOW_SOURCES = ("ready_made", "generated", "surprise")
HOST_NAME_MAX_LENGTH = 40


@dataclass(frozen=True, slots=True)
class PodcastFormat:
    format_id: str
    label: str
    description: str
    host_count: int
    is_learner_speaking: bool
    has_jump_in: bool
    max_host_run: int | None
    """The most lines one host may speak in a row (FR-015). None with one host."""
    invite_deadline: int | None
    """The host line, counted since the learner last spoke or passed, that must invite them."""


@dataclass(frozen=True, slots=True)
class EpisodeLength:
    length_id: str
    label: str
    target_host_lines: int


@dataclass(frozen=True, slots=True)
class Personality:
    personality_id: str
    label: str
    description: str
    """Learner-facing: one line."""
    speaking_style: str
    """Prompt-facing: how a host with this personality speaks and reacts."""


@dataclass(frozen=True, slots=True)
class ShowTemplate:
    show_id: str
    title: str
    premise: str
    topic: str
    learner_role: str
    default_personalities: tuple[str, str]
    """The lead host's personality, then the second host's."""


PODCAST_FORMATS: Mapping[str, PodcastFormat] = MappingProxyType(
    {
        "one_host": PodcastFormat(
            "one_host", "One host", "You and one host.", 1, True, False, None, 1
        ),
        "panel": PodcastFormat("panel", "Panel", "You and two hosts.", 2, True, True, 3, 4),
        "listen": PodcastFormat(
            "listen", "Listen", "Two hosts talk; you listen.", 2, False, False, 3, None
        ),
    }
)
DEFAULT_PODCAST_FORMAT = "one_host"

EPISODE_LENGTHS: Mapping[str, EpisodeLength] = MappingProxyType(
    {
        "short": EpisodeLength("short", "Short", 10),
        "medium": EpisodeLength("medium", "Medium", 20),
        "long": EpisodeLength("long", "Long", 40),
    }
)
DEFAULT_EPISODE_LENGTH = "medium"


def _personality(personality_id: str, label: str, description: str, style: str) -> Personality:
    return Personality(personality_id, label, description, style)


PERSONALITIES: Mapping[str, Personality] = MappingProxyType(
    {
        p.personality_id: p
        for p in (
            _personality(
                "enthusiast",
                "Enthusiast",
                "Excited about everything and quick to share.",
                "Speaks with warmth and energy, loves the topic, reacts with delight.",
            ),
            _personality(
                "dry_sceptic",
                "Dry sceptic",
                "Unimpressed until convinced, with a dry sense of humour.",
                "Questions big claims calmly, understates, teases with deadpan wit.",
            ),
            _personality(
                "storyteller",
                "Storyteller",
                "Turns every point into a short story.",
                "Answers with small personal anecdotes, sets a scene, then makes the point.",
            ),
            _personality(
                "curious_interviewer",
                "Curious interviewer",
                "Always asking why and how.",
                "Asks follow-up questions, picks up details others said, digs gently.",
            ),
            _personality(
                "expert",
                "Expert",
                "Knows the facts and likes to explain them.",
                "Gives one clear fact or tip at a time, explains simply, stays precise.",
            ),
            _personality(
                "joker",
                "Joker",
                "Never misses a chance for a joke.",
                "Plays with words, exaggerates for fun, laughs at their own mishaps.",
            ),
            _personality(
                "warm_mentor",
                "Warm mentor",
                "Encouraging and patient with everyone.",
                "Praises good ideas, reassures, offers gentle advice.",
            ),
            _personality(
                "contrarian",
                "Contrarian",
                "Takes the other side, just to see what happens.",
                "Politely disagrees, argues the opposite view, concedes when beaten.",
            ),
            _personality(
                "dreamer",
                "Dreamer",
                "Imagines how things could be.",
                "Speaks of hopes and what-ifs, paints big pictures, gets carried away.",
            ),
            _personality(
                "pragmatist",
                "Pragmatist",
                "Wants to know what actually works.",
                "Brings talk back to practical steps, costs and everyday reality.",
            ),
        )
    }
)


def _show(show_id: str, title: str, premise: str, topic: str, role: str, lead: str, second: str):
    return ShowTemplate(show_id, title, premise, topic, role, (lead, second))


SHOW_TEMPLATES: Mapping[str, ShowTemplate] = MappingProxyType(
    {
        s.show_id: s
        for s in (
            _show(
                "weekend-food-talk",
                "Weekend Food Talk",
                "Two food lovers swap weekend cooking wins and disasters.",
                "food",
                "guest",
                "enthusiast",
                "dry_sceptic",
            ),
            _show(
                "tech-for-normal-people",
                "Tech for Normal People",
                "Gadgets and apps explained without the jargon.",
                "technology",
                "caller",
                "expert",
                "joker",
            ),
            _show(
                "game-day",
                "Game Day",
                "Big matches, local teams and the joy of playing sport.",
                "sport",
                "co_host",
                "enthusiast",
                "contrarian",
            ),
            _show(
                "on-the-road",
                "On the Road",
                "Trips that went right, trips that went wrong, and where to go next.",
                "travel",
                "guest",
                "storyteller",
                "pragmatist",
            ),
            _show(
                "screen-and-sound",
                "Screen & Sound",
                "The films, series and songs everyone is talking about.",
                "film and music",
                "co_host",
                "dreamer",
                "dry_sceptic",
            ),
            _show(
                "nine-to-five",
                "Nine to Five",
                "Jobs, colleagues and the small dramas of working life.",
                "work life",
                "caller",
                "warm_mentor",
                "joker",
            ),
            _show(
                "home-sweet-home",
                "Home Sweet Home",
                "Flats, neighbours, family and making a place your own.",
                "housing and family",
                "guest",
                "pragmatist",
                "storyteller",
            ),
            _show(
                "big-little-questions",
                "Big Little Questions",
                "Everyday curiosities, from why toast lands butter-side down onwards.",
                "everyday curiosities",
                "guest",
                "curious_interviewer",
                "expert",
            ),
        )
    }
)
