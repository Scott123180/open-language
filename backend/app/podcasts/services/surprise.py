"""Surprise me: an idea built in code, then handed to the generator (research R9, FR-022, FR-023).

The seed topic is one of the learner's interests two presses in three when they have some,
otherwise one of the built-in topics, and an angle is added. The last ten (topic, angle) pairs
are never repeated, so twenty presses give at least fifteen different ideas (SC-008).
"""

import random
import threading
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import product

SURPRISE_HISTORY_SIZE = 10
INTEREST_SHARE = 2 / 3
MAX_REDRAWS = 50

SURPRISE_TOPICS = (
    "street food",
    "football",
    "learning to cook",
    "city cycling",
    "houseplants",
    "board games",
    "night trains",
    "coffee culture",
    "moving to a new city",
    "first jobs",
    "pets",
    "mountain hiking",
    "flea markets",
    "old films",
    "music festivals",
    "family recipes",
    "working from home",
    "public libraries",
    "the seaside in winter",
    "weddings",
    "running a small shop",
    "space travel",
    "museums",
    "gardening",
    "photography",
    "learning an instrument",
    "school memories",
    "camping",
    "video games",
    "bread baking",
    "neighbours",
    "rainy days",
    "second-hand fashion",
    "island life",
    "road trips",
    "birthdays",
    "sleep",
    "chess",
    "local legends",
    "saving money",
)
SURPRISE_ANGLES = (
    "a beginner's guide to",
    "a friendly debate about",
    "funny disasters with",
    "the history of",
    "myths and facts about",
    "a day in the life around",
    "tips from experts on",
    "childhood memories of",
    "the future of",
    "a quiz show about",
    "unpopular opinions on",
    "a listener's problem with",
)


@dataclass(frozen=True, slots=True)
class SurpriseIdea:
    topic: str
    angle: str

    @property
    def idea(self) -> str:
        return f"{self.angle} {self.topic}"


class SurpriseTopics:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def draw(self, interests: Sequence[str]) -> SurpriseIdea:
        """A (topic, angle) pair, leaning on the learner's interests when there are some."""
        return SurpriseIdea(self._topic(interests), self._rng.choice(SURPRISE_ANGLES))

    def _topic(self, interests: Sequence[str]) -> str:
        if interests and self._rng.random() < INTEREST_SHARE:
            return self._rng.choice(list(interests))
        return self._rng.choice(SURPRISE_TOPICS)


class RecentSurprises:
    """The last pairs Surprise me gave, process-wide, so a press never repeats one of them."""

    def __init__(self, size: int = SURPRISE_HISTORY_SIZE) -> None:
        self._recent: deque[SurpriseIdea] = deque(maxlen=size)
        self._lock = threading.Lock()

    def fresh(self, draw: Callable[[], SurpriseIdea]) -> SurpriseIdea:
        """Draw until the pair is not a recent one, remember it, and return it."""
        with self._lock:
            idea = self._first_fresh(draw)
            self._recent.append(idea)
            return idea

    def _first_fresh(self, draw: Callable[[], SurpriseIdea]) -> SurpriseIdea:
        for _ in range(MAX_REDRAWS):
            idea = draw()
            if idea not in self._recent:
                return idea
        return self._unused_built_in()

    def _unused_built_in(self) -> SurpriseIdea:
        pairs = (
            SurpriseIdea(topic, angle) for topic, angle in product(SURPRISE_TOPICS, SURPRISE_ANGLES)
        )
        return next(pair for pair in pairs if pair not in self._recent)
