"""The learner's shows: which shows are kept, and how each is listed (010 research R1, R9).

A ready-made show is named by its template id and a kept learner-made show by its saved id
(`ShowRef`). `ShowLibrary` turns a draft into a kept show; `ShowShelf` lists shows with the
hosts they open with: the series' hosts once there is a series, the card's hosts before.
"""

from dataclasses import dataclass, replace

from app.podcasts.catalog import LEAD_SLOT, READY_MADE_SOURCE, SHOW_TEMPLATES, ShowTemplate
from app.podcasts.services.casting import Host, HostCaster
from app.podcasts.services.series_storage import (
    KeptShow,
    SeriesRecord,
    SeriesStorage,
    ShelfEntry,
    ShowContent,
    ShowLibraryStorage,
    ShowRef,
)

__all__ = ["ShowLibrary", "ShowNoLongerKept", "ShowRef", "ShowShelf", "ShelfItem"]

SHOW_NO_LONGER_KEPT = "That show isn't kept any more. Pick another one."
STAND_IN_PREFIX = "saved-"
"""A kept learner-made show is cast like a template with this id, so its names are stable."""


class ShowNoLongerKept(LookupError):  # noqa: N818 — reads as what happened to the show
    """A draft names a saved show that is no longer kept (data-model §6)."""

    def __init__(self) -> None:
        super().__init__(SHOW_NO_LONGER_KEPT)


class ShowLibrary:
    def __init__(self, storage: ShowLibraryStorage) -> None:
        self._storage = storage

    def resolve(self, draft) -> KeptShow | None:
        """The draft's kept show, or None when it has never been kept."""
        ref = ShowRef.of(draft)
        if ref is None:
            return None
        kept = self._storage.get(ref)
        if kept is None and ref.saved_show_id is not None:
            raise ShowNoLongerKept()
        return kept

    def keep(self, draft) -> KeptShow:
        if draft.saved_show_id is not None and draft.source != READY_MADE_SOURCE:
            return self.resolve(draft)
        return self._storage.keep(show_content(draft))

    def played(self, kept: KeptShow) -> None:
        self._storage.touch_played(kept.show_row_id)

    def favourite(self, draft, is_favourite: bool) -> KeptShow | None:
        """Mark or unmark a show. None when unfavouriting left nothing to keep (FR-019)."""
        kept = self.keep(draft) if is_favourite else self._kept_for(draft)
        if kept is None:
            return None
        return self._storage.set_favourite(kept.show_row_id, is_favourite)

    def _kept_for(self, draft) -> KeptShow | None:
        """The draft's kept show, found by its content when the draft does not name it (FR-012)."""
        if ShowRef.of(draft) is not None:
            return self.resolve(draft)
        return self._storage.find(show_content(draft))

    def mine(self, language: str) -> list[ShelfEntry]:
        return self._storage.list_mine(language)

    def remove(self, saved_show_id: int) -> None:
        """Remove a kept learner-made show and its series in every language (FR-024)."""
        if not self._storage.forget(saved_show_id):
            raise ShowNoLongerKept()


def show_content(draft) -> ShowContent:
    """What is kept of a draft: a template id, or a learner-made show's own content."""
    if draft.source == READY_MADE_SOURCE:
        return ShowContent.ready_made(draft.show_id)
    lead, second = sorted(draft.hosts, key=lambda host: host.slot != LEAD_SLOT)
    return ShowContent(
        source=draft.source,
        template_id=None,
        title=draft.title,
        premise=draft.premise,
        topic=draft.topic,
        learner_role=draft.learner_role,
        personalities=(lead.personality_id, second.personality_id),
        angles=(lead.angle, second.angle),
    )


@dataclass(frozen=True, slots=True)
class ShelfItem:
    """A show as a list shows it: its content, its hosts, and the learner's state for it."""

    source: str
    show_id: str | None
    saved_show_id: int | None
    title: str
    premise: str
    topic: str
    learner_role: str
    hosts: tuple[Host, Host]
    is_favourite: bool
    series: SeriesRecord | None


class ShowShelf:
    def __init__(
        self, library: ShowLibraryStorage, series: SeriesStorage, caster: HostCaster
    ) -> None:
        self._library = library
        self._series = series
        self._caster = caster

    def ready_made(self, language: str, learner_name: str | None) -> list[ShelfItem]:
        """Every ready-made show, in catalogue order (FR-015)."""
        return [
            self._ready_made(template, language, learner_name)
            for template in SHOW_TEMPLATES.values()
        ]

    def mine(self, language: str, learner_name: str | None) -> list[ShelfItem]:
        """My shows, newest activity first (research R9)."""
        entries = self._library.list_mine(language)
        return [self.item(entry.show, entry.series, learner_name, language) for entry in entries]

    def item(
        self, kept: KeptShow, series: SeriesRecord | None, learner_name: str | None, language: str
    ) -> ShelfItem:
        hosts = (
            _series_hosts(series)
            if series
            else self._caster.cast_template(_template_of(kept), language, learner_name)
        )
        if series is None:
            hosts = tuple(
                replace(host, angle=angle) for host, angle in zip(hosts, kept.angles, strict=True)
            )
        return _shelf_item(kept, hosts, series)

    def _ready_made(
        self, template: ShowTemplate, language: str, learner_name: str | None
    ) -> ShelfItem:
        kept = self._library.get(ShowRef(template_id=template.show_id))
        if kept is None:
            hosts = self._caster.cast_template(template, language, learner_name)
            return _template_item(template, hosts)
        series = self._series.find(kept.show_row_id, language)
        return self.item(kept, series, learner_name, language)


def _template_item(template: ShowTemplate, hosts: tuple[Host, Host]) -> ShelfItem:
    """A ready-made show the learner has no state for: its card's hosts, no series."""
    return ShelfItem(
        source=READY_MADE_SOURCE,
        show_id=template.show_id,
        saved_show_id=None,
        title=template.title,
        premise=template.premise,
        topic=template.topic,
        learner_role=template.learner_role,
        hosts=hosts,
        is_favourite=False,
        series=None,
    )


def _series_hosts(series: SeriesRecord) -> tuple[Host, Host]:
    lead, second = series.hosts
    return lead.to_host(), second.to_host()


def _template_of(kept: KeptShow) -> ShowTemplate:
    """A ready-made show's template, or a stand-in so a kept show's names stay the same."""
    if kept.ref.template_id is not None:
        return SHOW_TEMPLATES[kept.ref.template_id]
    stand_in = f"{STAND_IN_PREFIX}{kept.show_row_id}"
    return ShowTemplate(
        stand_in, kept.title, kept.premise, kept.topic, kept.learner_role, kept.personalities
    )


def _shelf_item(kept: KeptShow, hosts: tuple[Host, Host], series: SeriesRecord | None) -> ShelfItem:
    return ShelfItem(
        source=kept.source,
        show_id=kept.ref.template_id,
        saved_show_id=kept.ref.saved_show_id,
        title=kept.title,
        premise=kept.premise,
        topic=kept.topic,
        learner_role=kept.learner_role,
        hosts=hosts,
        is_favourite=kept.is_favourite,
        series=series,
    )
