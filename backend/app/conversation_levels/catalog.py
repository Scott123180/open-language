"""The level catalogue: the one place conversation levels and their limits are listed (005).

Every number a level imposes is a named field here; the renderers in `rules.py` turn these
values into instruction text and never hold a limit of their own.
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from types import MappingProxyType


class ConversationLevel(StrEnum):
    """The four levels, easiest first. Declaration order is display order."""

    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    NATURAL = "natural"


DEFAULT_CONVERSATION_LEVEL = ConversationLevel.NATURAL


@dataclass(frozen=True, slots=True)
class SpeechLimits:
    """What a level allows the target-language text to contain (spec FR-003)."""

    max_sentences_per_reply: int
    max_words_per_sentence: int
    sentence_joining: str
    tenses: str
    vocabulary_rank: int
    idioms: str
    questions: str

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, int) and value <= 0:
                raise ValueError(f"{field.name} must be positive, got {value}")


@dataclass(frozen=True, slots=True)
class LevelDescriptor:
    """A level as the learner sees it, plus its limits (`None` only for Natural)."""

    level: ConversationLevel
    label: str
    cefr_label: str
    description: str
    limits: SpeechLimits | None

    def __post_init__(self) -> None:
        is_natural = self.level is ConversationLevel.NATURAL
        if is_natural != (self.limits is None):
            expectation = "no limits" if is_natural else "limits"
            raise ValueError(f"Level {self.level.value!r} must have {expectation}")


_BEGINNER = LevelDescriptor(
    level=ConversationLevel.BEGINNER,
    label="Beginner",
    cefr_label="A1",
    description="Very short, simple sentences — like talking with a young child.",
    limits=SpeechLimits(
        max_sentences_per_reply=2,
        max_words_per_sentence=8,
        sentence_joining="one idea per sentence",
        tenses="present tense only",
        vocabulary_rank=500,
        idioms="none",
        questions="one easy yes/no or either/or question",
    ),
)

_ELEMENTARY = LevelDescriptor(
    level=ConversationLevel.ELEMENTARY,
    label="Elementary",
    cefr_label="A2",
    description="Short, clear sentences with everyday words — like talking with a patient friend.",
    limits=SpeechLimits(
        max_sentences_per_reply=3,
        max_words_per_sentence=12,
        sentence_joining="simple connectors only (and, but, because)",
        tenses='present, simple past, near future ("going to" + verb)',
        vocabulary_rank=1500,
        idioms="none",
        questions="one simple open question",
    ),
)

_INTERMEDIATE = LevelDescriptor(
    level=ConversationLevel.INTERMEDIATE,
    label="Intermediate",
    cefr_label="B1",
    description="Connected, everyday speech from a clear, considerate adult — no rare words.",
    limits=SpeechLimits(
        max_sentences_per_reply=4,
        max_words_per_sentence=20,
        sentence_joining="at most one subordinate clause",
        tenses="all common indicative tenses; subjunctive only in fixed everyday phrases",
        vocabulary_rank=3000,
        idioms="common, widely understood idioms only",
        questions="as the conversation needs",
    ),
)

_NATURAL = LevelDescriptor(
    level=ConversationLevel.NATURAL,
    label="Natural",
    cefr_label="No limit",
    description="Ordinary everyday native speech, with no limits.",
    limits=None,
)

LEVEL_CATALOG: Mapping[ConversationLevel, LevelDescriptor] = MappingProxyType(
    {
        descriptor.level: descriptor
        for descriptor in (_BEGINNER, _ELEMENTARY, _INTERMEDIATE, _NATURAL)
    }
)
