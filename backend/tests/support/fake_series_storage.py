"""In-memory show library and series storage, so service tests state only what they need."""

from dataclasses import replace
from datetime import UTC, datetime

from app.podcasts.services.series_storage import (
    EpisodeRef,
    KeptShow,
    MemoryReply,
    PendingEpisode,
    RememberedPoint,
    SeriesAlreadyExists,
    SeriesHost,
    SeriesRecord,
    SeriesStorage,
    ShelfEntry,
    ShowContent,
    ShowLibraryStorage,
    ShowRef,
)

PLAYED_AT = datetime(2026, 10, 17, tzinfo=UTC)


class FakeShowLibraryStorage(ShowLibraryStorage):
    def __init__(self) -> None:
        self.shows: dict[int, KeptShow] = {}
        self.contents: dict[int, ShowContent] = {}
        self.played: list[int] = []

    def keep(self, content: ShowContent) -> KeptShow:
        existing = next((i for i, kept in self.contents.items() if kept == content), None)
        if existing is not None:
            return self.shows[existing]
        row_id = len(self.shows) + 1
        ref = (
            ShowRef(template_id=content.template_id)
            if content.is_ready_made
            else ShowRef(saved_show_id=row_id)
        )
        self.contents[row_id] = content
        self.shows[row_id] = _kept(row_id, ref, content)
        return self.shows[row_id]

    def get(self, ref: ShowRef) -> KeptShow | None:
        return next((show for show in self.shows.values() if show.ref == ref), None)

    def find(self, content: ShowContent) -> KeptShow | None:
        return next((self.shows[i] for i, kept in self.contents.items() if kept == content), None)

    def set_favourite(self, show_row_id: int, is_favourite: bool) -> KeptShow | None:
        self.shows[show_row_id] = replace(self.shows[show_row_id], is_favourite=is_favourite)
        return self.shows[show_row_id]

    def touch_played(self, show_row_id: int) -> None:
        self.played.append(show_row_id)
        self.shows[show_row_id] = replace(self.shows[show_row_id], last_played_at=PLAYED_AT)

    def list_mine(self, language: str) -> list[ShelfEntry]:
        return []

    def forget(self, saved_show_id: int) -> bool:
        return self.shows.pop(saved_show_id, None) is not None


class FakeSeriesStorage(SeriesStorage):
    def __init__(self, library: FakeShowLibraryStorage) -> None:
        self._library = library
        self.series: dict[int, SeriesRecord] = {}
        self.points: dict[int, list[RememberedPoint]] = {}
        self.recasts: list[SeriesHost] = []
        self.resets: list[int] = []

    def add(self, show: KeptShow, language: str, hosts, episode_count: int = 0) -> SeriesRecord:
        series_id = len(self.series) + 1
        self.series[series_id] = SeriesRecord(series_id, show, language, hosts, episode_count, None)
        self.points[series_id] = []
        return self.series[series_id]

    def add_point(self, series_id: int, kind: str, text: str, episode_number: int = 1) -> None:
        point_id = sum(len(points) for points in self.points.values()) + 1
        point = RememberedPoint(point_id, kind, text, f"EN {text}", episode_number)
        self.points[series_id].insert(0, point)

    def find(self, show_row_id: int, language: str) -> SeriesRecord | None:
        return next(
            (
                record
                for record in self.series.values()
                if record.show.show_row_id == show_row_id and record.language == language
            ),
            None,
        )

    def get(self, series_id: int) -> SeriesRecord | None:
        return self.series.get(series_id)

    def create(self, show_row_id: int, language: str, hosts) -> SeriesRecord:
        if self.find(show_row_id, language) is not None:
            raise SeriesAlreadyExists(f"show {show_row_id} has a {language} series")
        return self.add(self._library.shows[show_row_id], language, hosts)

    def recast(self, series_id: int, host: SeriesHost) -> SeriesRecord:
        record = self.series[series_id]
        joined = replace(host, joined_after_episodes=record.episode_count)
        hosts = tuple(joined if h.slot == host.slot else h for h in record.hosts)
        self.recasts.append(joined)
        self.series[series_id] = replace(record, hosts=hosts)
        return self.series[series_id]

    def reset(self, series_id: int) -> bool:
        self.resets.append(series_id)
        return self.series.pop(series_id, None) is not None

    def remembered(self, series_id: int) -> tuple[RememberedPoint, ...]:
        return tuple(self.points.get(series_id, ()))

    def pending_episodes(self, series_id: int) -> tuple[PendingEpisode, ...]:
        return ()

    def remember(self, series_id: int, conversation_id: int, reply: MemoryReply, up_to) -> None:
        raise AssertionError("the series service never writes memory")

    def unfinished(self, series_id: int, ref: EpisodeRef) -> None:
        self.series[series_id] = replace(self.series[series_id], unfinished=ref)


def _kept(row_id: int, ref: ShowRef, content: ShowContent) -> KeptShow:
    return KeptShow(
        show_row_id=row_id,
        ref=ref,
        source=content.source,
        title=content.title,
        premise=content.premise,
        topic=content.topic,
        learner_role=content.learner_role,
        personalities=content.personalities,
        angles=content.angles,
        is_favourite=False,
        last_played_at=None,
    )
