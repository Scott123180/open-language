"""Builders for series storage tests: kept shows, series, linked episodes and their lines."""

import itertools
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.podcasts.services.series_snapshot import SeriesSnapshot
from app.podcasts.services.series_storage import (
    MemoryReply,
    PointText,
    SeriesHost,
    SeriesRecord,
    ShowContent,
)
from app.podcasts.services.sqlite_series_storage import (
    SQLiteSeriesStorage,
    SQLiteShowLibraryStorage,
)
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from app.podcasts.services.storage import NewHostLine, NewSeriesLink
from app.services.storage.sqlite import SQLiteStorageProvider
from tests.support.podcast_records import new_episode, new_host

READY_MADE_ID = "big-little-questions"
SERIES_HOSTS = (
    SeriesHost("lead", "Hugo", "curious_interviewer", "es_AR-daniela-high", "host", None, 0),
    SeriesHost("second", "Inés", "expert", "es_ES-davefx-medium", "co_host", None, 0),
)
EPISODE_HOSTS = (
    new_host("lead", "Hugo", "curious_interviewer"),
    new_host("second", "Inés", "expert"),
)


class TickingClock:
    """Each read is one minute after the last, so the order of writes is the order of times."""

    def __init__(self) -> None:
        self._ticks = itertools.count()

    def __call__(self) -> datetime:
        return datetime(2026, 10, 17, tzinfo=UTC) + timedelta(minutes=next(self._ticks))


def make_series(session: Session, language: str = "es", show_id: str = READY_MADE_ID):
    """A kept ready-made show with a new series in `language`."""
    kept = SQLiteShowLibraryStorage(session).keep(ShowContent.ready_made(show_id))
    return SQLiteSeriesStorage(session).create(kept.show_row_id, language, SERIES_HOSTS)


def series_episode(
    session: Session, series: SeriesRecord, number: int | None = None, snapshot=None
) -> int:
    """Start an episode linked to `series`, numbered next unless `number` is given."""
    number = number or series.next_episode_number
    link = NewSeriesLink(series.series_id, number, snapshot or SeriesSnapshot(number))
    episode = new_episode(series=link, hosts=EPISODE_HOSTS, target_language=series.language)
    return SQLitePodcastStorage(session).create_episode(episode).conversation_id


def add_host_lines(session: Session, conversation_id: int, *contents: str) -> list[int]:
    podcasts = SQLitePodcastStorage(session)
    lead = podcasts.get_hosts(conversation_id)[0]
    return [
        podcasts.save_host_line(
            NewHostLine(conversation_id, lead.host_id, content, "discuss", False)
        ).message_id
        for content in contents
    ]


def add_learner_lines(session: Session, conversation_id: int, *contents: str) -> list[int]:
    core = SQLiteStorageProvider(session)
    return [core.save_message(conversation_id, "user", content).id for content in contents]


def point(text: str, english: str | None = None) -> PointText:
    return PointText(text, english or f"EN {text}")


def reply(topic: str | None, *learner: str) -> MemoryReply:
    return MemoryReply(point(topic) if topic else None, tuple(point(text) for text in learner))
