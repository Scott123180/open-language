"""SeriesService: which hosts and memory an episode starts with (010 data-model §5.2).

A series' first episode fixes its hosts from the draft, after any Shuffle. A later episode must
start with the series' hosts: they are checked, never trusted, so a stale draft is refused with
a plain 409 rather than silently overruled (SC-001, research R2). The memory an episode starts
with is frozen into its snapshot here (research R5).
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.podcasts.catalog import (
    LEAD_SLOT,
    LEARNER_POINT,
    PODCAST_FORMATS,
    SERIES_KIND,
    TOPIC_POINT,
)
from app.podcasts.schemas import HostDraftModel, StartEpisodeRequest, show_problem, validate_draft
from app.podcasts.services.library import ShowLibrary
from app.podcasts.services.series_snapshot import SeriesSnapshot
from app.podcasts.services.series_storage import (
    KeptShow,
    SeriesAlreadyExists,
    SeriesHost,
    SeriesRecord,
    SeriesStorage,
)
from app.podcasts.services.storage import NewEpisode, NewHost, NewSeriesLink
from app.services.storage.base import AppSettingsRecord

SERIES_HOSTS_CHANGED = "This show's hosts changed. Open the show again."

InstalledCount = Callable[[str], int]
"""How many voices are installed for a language."""


class StartRefused(ValueError):  # noqa: N818 — reads as what happened to the start
    """The draft cannot start an episode; the message says why and what to do (422)."""


class SeriesHostsChanged(ValueError):  # noqa: N818 — reads as what the learner is told
    """The draft's hosts are not the series' hosts: the screen is stale (409)."""

    def __init__(self) -> None:
        super().__init__(SERIES_HOSTS_CHANGED)


@dataclass(frozen=True)
class PreparedStart:
    """Everything an episode needs beyond the request: its hosts and its series link."""

    request: StartEpisodeRequest
    hosts: tuple[NewHost, ...]
    series: NewSeriesLink | None
    saved_show_id: int | None


class SeriesService:
    def __init__(
        self, library: ShowLibrary, series: SeriesStorage, installed_count: InstalledCount
    ) -> None:
        self._library = library
        self._series = series
        self._installed_count = installed_count

    def prepare(self, req: StartEpisodeRequest, settings: AppSettingsRecord) -> PreparedStart:
        """Check the draft, keep the show and, for a series, find or create it."""
        if req.kind == SERIES_KIND:
            return self._series_start(req, settings.target_language)
        return self._one_off_start(req, settings.target_language)

    def new_episode(self, prepared: PreparedStart, settings: AppSettingsRecord) -> NewEpisode:
        req, show = prepared.request, prepared.request.show
        return NewEpisode(
            show_source=show.source,
            show_id=show.show_id,
            title=show.title,
            premise=show.premise,
            topic=show.topic,
            learner_role=show.learner_role,
            format=req.format,
            length=req.length,
            learner_name=req.learner_name,
            target_language=settings.target_language,
            native_language=settings.native_language,
            llm_model=settings.llm_model,
            hosts=prepared.hosts,
            series=prepared.series,
        )

    def _series_start(self, req: StartEpisodeRequest, language: str) -> PreparedStart:
        known = self._library.resolve(req.show)
        series = self._series.find(known.show_row_id, language) if known else None
        self._check_series_draft(req, series, language)
        kept = self._library.keep(req.show)
        self._library.played(kept)
        series = series or self._create(kept, req, language)
        hosts = _participating(series, req.format)
        return PreparedStart(req, hosts, self._link(series), kept.ref.saved_show_id)

    def _one_off_start(self, req: StartEpisodeRequest, language: str) -> PreparedStart:
        self._refuse(
            validate_draft(req.show, language, req.learner_name, self._installed_count(language))
        )
        return PreparedStart(req, _draft_hosts(req), None, None)

    def _check_series_draft(
        self, req: StartEpisodeRequest, series: SeriesRecord | None, language: str
    ) -> None:
        """Episode 1 is checked as 007 checks a draft; later ones keep the series' hosts."""
        if series is None:
            installed = self._installed_count(language)
            return self._refuse(validate_draft(req.show, language, req.learner_name, installed))
        self._refuse(show_problem(req.show, language))
        if not series.matches(req.show.hosts):
            raise SeriesHostsChanged()

    def _create(self, kept: KeptShow, req: StartEpisodeRequest, language: str) -> SeriesRecord:
        hosts = tuple(_series_host(draft) for draft in _lead_first(req.show.hosts))
        try:
            return self._series.create(kept.show_row_id, language, hosts)
        except SeriesAlreadyExists as raced:
            raise SeriesHostsChanged() from raced

    def _link(self, series: SeriesRecord) -> NewSeriesLink:
        return NewSeriesLink(series.series_id, series.next_episode_number, self._snapshot(series))

    def _snapshot(self, series: SeriesRecord) -> SeriesSnapshot:
        """The bounded memory, newest first, and who joins the series in this episode."""
        points = self._series.remembered(series.series_id)
        count = series.episode_count
        return SeriesSnapshot(
            episode_number=series.next_episode_number,
            topics_covered=tuple(p.conversation_language for p in points if p.kind == TOPIC_POINT),
            about_learner=tuple(p.conversation_language for p in points if p.kind == LEARNER_POINT),
            new_host_slots=tuple(
                host.slot
                for host in series.hosts
                if count >= 1 and host.joined_after_episodes == count
            ),
        )

    @staticmethod
    def _refuse(problem: str | None) -> None:
        if problem is not None:
            raise StartRefused(problem)


def _lead_first(hosts):
    return sorted(hosts, key=lambda host: host.slot != LEAD_SLOT)


def _series_host(draft: HostDraftModel) -> SeriesHost:
    name = draft.name.strip()
    return SeriesHost(
        draft.slot, name, draft.personality_id, draft.voice_key, draft.show_role, draft.angle, 0
    )


def _participating(series: SeriesRecord, format_id: str) -> tuple[NewHost, ...]:
    """The series' hosts for the format's slots: the lead alone in One host (FR-003)."""
    count = PODCAST_FORMATS[format_id].host_count
    return tuple(_new_host(host) for host in series.hosts[:count])


def _new_host(host: SeriesHost) -> NewHost:
    return NewHost(
        host.slot, host.name, host.personality_id, host.voice_key, host.show_role, host.angle
    )


def _draft_hosts(req: StartEpisodeRequest) -> tuple[NewHost, ...]:
    """Every host of the draft, or only the lead in a one-host format (FR-003)."""
    count = PODCAST_FORMATS[req.format].host_count
    return tuple(
        NewHost(h.slot, h.name.strip(), h.personality_id, h.voice_key, h.show_role, h.angle)
        for h in _lead_first(req.show.hosts)[:count]
    )
