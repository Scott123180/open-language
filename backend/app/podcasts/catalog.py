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
READY_MADE_SOURCE = "ready_made"
SHOW_SOURCES = (READY_MADE_SOURCE, "generated", "surprise", "suggested")
HOST_NAME_MAX_LENGTH = 40
TITLE_MAX_LENGTH = 200

ONE_OFF_KIND, SERIES_KIND = "one_off", "series"
EPISODE_KINDS = (ONE_OFF_KIND, SERIES_KIND)
"""A one-off episode stands alone; a series episode continues its show (010 research R2)."""

TOPIC_POINT, LEARNER_POINT = "topic", "learner"
"""The two kinds of remembered point: an episode's subject, or something the learner shared."""
MAX_REMEMBERED_TOPICS = 10
MAX_REMEMBERED_ABOUT_LEARNER = 8
MAX_POINTS_PER_EPISODE = 3
"""The most learner points one memory reply may add."""
REMEMBERED_POINT_MAX_LENGTH = 160
REMEMBERED_TEXT_BUDGET = 1200
"""The most conversation-language text a series' points hold together, so the stored list
always fits the series prompt section whole (010 research R7)."""
SERIES_SECTION_MAX_LENGTH = 1800
MIN_LINES_TO_REMEMBER = 2
MEMORY_CHUNK_CHARACTERS = 6000
MEMORY_WAIT_SECONDS = 30
"""The longest a Start waits for the hosts to catch up on the last episode (010 research R6)."""

SUGGESTION_SEEDS = 5
MIN_SUGGESTIONS = 3
INTEREST_SEEDS = 3
"""Find a new show: seeds per request, the fewest suggestions shown, and how many seeds come
from the learner's interests when they have some (010 research R10)."""


@dataclass(frozen=True, slots=True)
class PodcastFormat:
    format_id: str
    label: str
    description: str
    host_count: int
    is_learner_speaking: bool
    has_jump_in: bool
    """The learner can speak while the hosts have the floor (FR-017; One host too since 011)."""
    has_pass: bool
    """The learner can pass on an invitation (011 research R15: Panel only)."""
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
    configured_speaking_style: str | None = None
    """011: the style a configured episode uses instead, when set (research R22)."""


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
            "one_host", "One host", "You and one host.", 1, True, True, False, None, 1
        ),
        "panel": PodcastFormat("panel", "Panel", "You and two hosts.", 2, True, True, True, 3, 4),
        "listen": PodcastFormat(
            "listen", "Listen", "Two hosts talk; you listen.", 2, False, False, False, 3, None
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


def _personality(
    personality_id: str, label: str, description: str, style: str, configured: str | None = None
) -> Personality:
    return Personality(personality_id, label, description, style, configured)


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
                "Asks how and why, picks up details others said, and says what they think too.",
            ),
            _personality(
                "expert",
                "Expert",
                "Knows the facts and likes to explain them.",
                "Gives one clear fact or tip at a time, explains simply, stays precise.",
                "Explains how and why step by step, with simple facts and an everyday example, "
                "and stays precise.",
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


# --- 011: how an episode sounds (data-model §1.1–§1.4) ----------------------------------------

TODAY_SUBJECT_MAX_LENGTH = 120
SERIES_SETTING_NAMES = (
    "format",
    "length",
    "style",
    "line_length",
    "invite_frequency",
    "learner_role",
)
"""The settings a series episode may keep for later episodes (`from_now_on`)."""
ANSWER_INTENTS = ("answer", "follow_up")
DISCUSSION_INTENTS = ("react", "explain", "story")
"""The kinds of discussion line a Style draws from, in the order of its weights."""
BRIEF_INTENTS = ("greet", "react", "wrap_up", "sign_off")
"""The line kinds that take a Host lines value's brief phrase; every other takes its full one."""
QUESTION_MARK = "?"
ASKS = ("required", "allowed", "none", "never")
ADDRESSEES = ("learner", LEAD_SLOT, SECOND_SLOT)
"""Who a host line is for. A stored None means no one in particular."""
ADDRESS_ALL = "all"
ADDRESS_TAG_MAX_LENGTH = 60
INVITE_DEADLINE = 4
"""The 4th host line in a row since the learner spoke always invites them (FR-003)."""
SUBJECT_SUGGESTIONS = 3
SUBJECT_AVOID_MAX = 10
MIN_SENTENCE_CHARACTERS = 12
"""A shorter sentence is joined to the next, so "Sr." never stands alone (research R13)."""
PART_WAIT_SECONDS = 30
PART_TTL_SECONDS = 600

_WEIGHT_TOLERANCE = 1e-9
_NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight")


@dataclass(frozen=True, slots=True)
class EpisodeStyle:
    style_id: str
    label: str
    description: str
    """Learner-facing: one line."""
    weights: tuple[float, float, float]
    """The chance of a react, an explain and a story line, in `DISCUSSION_INTENTS` order."""

    def __post_init__(self) -> None:
        if any(weight <= 0 for weight in self.weights):
            raise ValueError(f"Every weight of the {self.label} style must be positive.")
        if abs(sum(self.weights) - 1) > _WEIGHT_TOLERANCE:
            raise ValueError(f"The weights of the {self.label} style must sum to 1.")


@dataclass(frozen=True, slots=True)
class HostLineLength:
    line_length_id: str
    label: str
    min_sentences: int
    max_sentences: int
    brief_phrase: str
    """How a brief line kind is asked for (`BRIEF_INTENTS`), inside the range."""
    full_phrase: str
    """How every other line kind is asked for, inside the range."""

    def __post_init__(self) -> None:
        if not 1 <= self.min_sentences <= self.max_sentences:
            raise ValueError(f"{self.label} lines need 1 ≤ min ≤ max sentences.")

    @property
    def range_phrase(self) -> str:
        low, high = _NUMBER_WORDS[self.min_sentences], _NUMBER_WORDS[self.max_sentences]
        return f"{low} to {high} sentences"


@dataclass(frozen=True, slots=True)
class InviteFrequency:
    invite_frequency_id: str
    label: str
    hazards: tuple[float, float, float]
    """The chance the 1st, 2nd and 3rd host line since the learner may invite them."""

    def __post_init__(self) -> None:
        if any(not 0 <= hazard <= 1 for hazard in self.hazards):
            raise ValueError(f"Every hazard of {self.label} must be between 0 and 1.")


EPISODE_STYLES: Mapping[str, EpisodeStyle] = MappingProxyType(
    {
        s.style_id: s
        for s in (
            EpisodeStyle(
                "conversation", "Conversation", "Lots of back-and-forth.", (0.90, 0.07, 0.03)
            ),
            EpisodeStyle("balanced", "Balanced", "Some talk, some explaining.", (0.55, 0.30, 0.15)),
            EpisodeStyle(
                "presented",
                "Presented",
                "The hosts mostly explain and tell stories, like a radio show.",
                (0.35, 0.40, 0.25),
            ),
        )
    }
)
DEFAULT_EPISODE_STYLE = "balanced"

HOST_LINE_LENGTHS: Mapping[str, HostLineLength] = MappingProxyType(
    {
        length.line_length_id: length
        for length in (
            HostLineLength("short", "Short", 1, 2, "in one or two sentences", "in two sentences"),
            HostLineLength(
                "medium", "Medium", 3, 5, "in three sentences", "in four or five sentences"
            ),
            HostLineLength(
                "long", "Long", 5, 8, "in five or six sentences", "in six to eight sentences"
            ),
        )
    }
)
DEFAULT_HOST_LINE_LENGTH = "medium"

INVITE_FREQUENCIES: Mapping[str, InviteFrequency] = MappingProxyType(
    {
        f.invite_frequency_id: f
        for f in (
            InviteFrequency("often", "Often", (1.0, 1.0, 1.0)),
            InviteFrequency("sometimes", "Sometimes", (0.35, 0.45, 0.55)),
            InviteFrequency("rarely", "Rarely", (0.0, 0.05, 0.10)),
        )
    }
)
DEFAULT_INVITE_FREQUENCY = "sometimes"
