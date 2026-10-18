"""010 T035: memory stays bounded over any sequence of catch-ups (FR-006, FR-011, research R7).

Each seeded sequence writes random replies across random episodes and chunks. After every write
the stored points must equal a reference model of "newest wins within the caps, then within the
text budget", and the series section rendered from them must fit and contain every point.
"""

import random
from pathlib import Path

import pytest

from app.conversation_levels import ConversationLevel
from app.podcasts.catalog import (
    LEARNER_POINT,
    MAX_POINTS_PER_EPISODE,
    MAX_REMEMBERED_ABOUT_LEARNER,
    MAX_REMEMBERED_TOPICS,
    PODCAST_FORMATS,
    REMEMBERED_POINT_MAX_LENGTH,
    REMEMBERED_TEXT_BUDGET,
    SERIES_SECTION_MAX_LENGTH,
    TOPIC_POINT,
)
from app.podcasts.prompts import ShowBrief, build_standing_prompt
from app.podcasts.services.casting import Cast, Host
from app.podcasts.services.series_snapshot import SeriesBrief, SeriesSnapshot
from app.podcasts.services.series_storage import MemoryReply, PointText
from app.podcasts.services.sqlite_series_storage import SQLiteSeriesStorage
from app.practice_languages import ConversationLanguages
from tests.support.scratch_database import make_session
from tests.support.series_records import TickingClock, make_series, series_episode

SEQUENCES = 200
CAPS = {TOPIC_POINT: MAX_REMEMBERED_TOPICS, LEARNER_POINT: MAX_REMEMBERED_ABOUT_LEARNER}
CAST = Cast.for_format(
    PODCAST_FORMATS["panel"],
    Host("lead", "Hugo", "curious_interviewer", "es_ES-davefx-medium", "host"),
    Host("second", "Inés", "expert", "es_AR-daniela-high", "co_host"),
)
SHOW = ShowBrief("Big Little Questions", "Everyday curiosities.", "everyday curiosities", "guest")
SPANISH = ConversationLanguages.of("es", "en")

Entry = tuple[str, str, int]
"""A remembered point in the reference model: kind, text and source episode, oldest first."""


class ReferenceMemory:
    def __init__(self) -> None:
        self.entries: list[Entry] = []

    def remember(self, number: int, reply: MemoryReply) -> None:
        if reply.topic is not None:
            self.entries = [e for e in self.entries if not (e[0] == TOPIC_POINT and e[2] == number)]
            self.entries.append((TOPIC_POINT, reply.topic.conversation_language, number))
        self.entries.extend(
            (LEARNER_POINT, p.conversation_language, number) for p in reply.about_learner
        )
        for kind, cap in CAPS.items():
            self._cap(kind, cap)
        while sum(len(text) for _kind, text, _n in self.entries) > REMEMBERED_TEXT_BUDGET:
            self.entries.pop(0)

    def _cap(self, kind: str, cap: int) -> None:
        excess = sum(1 for entry in self.entries if entry[0] == kind) - cap
        for entry in [entry for entry in self.entries if entry[0] == kind][: max(excess, 0)]:
            self.entries.remove(entry)

    def newest_first(self) -> list[tuple[str, str]]:
        return [(kind, text) for kind, text, _n in reversed(self.entries)]


def _text(rng: random.Random) -> str:
    return (
        "".join(
            rng.choice("abcdeñ ") for _ in range(rng.randint(1, REMEMBERED_POINT_MAX_LENGTH))
        ).strip()
        or "z"
    )


def _reply(rng: random.Random) -> MemoryReply:
    topic = PointText(_text(rng), "t") if rng.random() < 0.8 else None
    count = rng.randint(0, MAX_POINTS_PER_EPISODE)
    return MemoryReply(topic, tuple(PointText(_text(rng), "l") for _ in range(count)))


def _section(points) -> str:
    topics = tuple(p.conversation_language for p in points if p.kind == TOPIC_POINT)
    learner = tuple(p.conversation_language for p in points if p.kind == LEARNER_POINT)
    brief = SeriesBrief.of(SeriesSnapshot(12, topics, learner, ("second",)), CAST)
    prompt = build_standing_prompt(
        SHOW, CAST, "Sam", SPANISH, ConversationLevel.NATURAL, series=brief
    )
    return prompt[prompt.index("This is ") : prompt.index("Line rules:")].strip()


def _check(storage: SQLiteSeriesStorage, series_id: int, model: ReferenceMemory) -> None:
    points = storage.remembered(series_id)
    topics = [p for p in points if p.kind == TOPIC_POINT]
    assert [(p.kind, p.conversation_language) for p in points] == model.newest_first()
    assert len(topics) <= MAX_REMEMBERED_TOPICS
    assert len(points) - len(topics) <= MAX_REMEMBERED_ABOUT_LEARNER
    assert sum(len(p.conversation_language) for p in points) <= REMEMBERED_TEXT_BUDGET
    assert len({p.episode_number for p in topics}) == len(topics)
    section = _section(points)
    assert len(section) <= SERIES_SECTION_MAX_LENGTH
    assert all(p.conversation_language in section for p in points)


@pytest.mark.parametrize("seed", range(SEQUENCES))
def test_any_sequence_of_catch_ups_keeps_the_newest_points_within_the_bounds(tmp_path: Path, seed):
    rng = random.Random(seed)
    session = make_session(tmp_path / "bounded.db")
    storage, series, model = (
        SQLiteSeriesStorage(session, clock=TickingClock()),
        make_series(session),
        ReferenceMemory(),
    )
    for number in range(1, rng.randint(2, 14)):
        episode_id = series_episode(session, series, number)
        for _chunk in range(rng.randint(1, 3)):
            memory = _reply(rng)
            storage.remember(series.series_id, episode_id, memory, None)
            model.remember(number, memory)
            _check(storage, series.series_id, model)
    session.close()
