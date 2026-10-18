"""What the podcast module stores about shows and series (010 data-model §3–§4).

Two small interfaces beside `PodcastStorage`, which gains no method (ISP): the show library
(which shows are the learner's) and the series storage (a show's episodes, hosts and memory in
one language). Only the composition root builds their implementations.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.podcasts.catalog import READY_MADE_SOURCE, SHOW_TEMPLATES
from app.podcasts.services.casting import Host


class SeriesAlreadyExists(ValueError):  # noqa: N818 — reads as the invariant it guards
    """The show already has a series in that language (one per show and language)."""


@dataclass(frozen=True, slots=True)
class ShowRef:
    """A ready-made show by its template id, or a kept learner-made show by its saved id."""

    template_id: str | None = None
    saved_show_id: int | None = None

    def __post_init__(self) -> None:
        if (self.template_id is None) == (self.saved_show_id is None):
            raise ValueError("A show ref names exactly one of a template id and a saved id.")

    @classmethod
    def of(cls, draft) -> "ShowRef | None":
        """The draft's show, or None for a learner-made draft that has not been kept."""
        if draft.source == READY_MADE_SOURCE:
            return cls(template_id=draft.show_id)
        if draft.saved_show_id is not None:
            return cls(saved_show_id=draft.saved_show_id)
        return None


@dataclass(frozen=True, slots=True)
class ShowContent:
    """What is kept of a show: a template id, or a learner-made show's own content."""

    source: str
    template_id: str | None
    title: str
    premise: str
    topic: str
    learner_role: str
    personalities: tuple[str, str]
    angles: tuple[str | None, str | None]

    @classmethod
    def ready_made(cls, template_id: str) -> "ShowContent":
        template = SHOW_TEMPLATES[template_id]
        return cls(
            source=READY_MADE_SOURCE,
            template_id=template_id,
            title=template.title,
            premise=template.premise,
            topic=template.topic,
            learner_role=template.learner_role,
            personalities=template.default_personalities,
            angles=(None, None),
        )

    @property
    def is_ready_made(self) -> bool:
        return self.template_id is not None


@dataclass(frozen=True, slots=True)
class KeptShow:
    show_row_id: int
    ref: ShowRef
    source: str
    title: str
    premise: str
    topic: str
    learner_role: str
    personalities: tuple[str, str]
    angles: tuple[str | None, str | None]
    is_favourite: bool
    last_played_at: datetime | None

    @property
    def is_ready_made(self) -> bool:
        return self.ref.template_id is not None


class _HostDraft(Protocol):
    slot: str
    name: str
    personality_id: str
    voice_key: str


@dataclass(frozen=True, slots=True)
class SeriesHost:
    slot: str
    name: str
    personality_id: str
    voice_key: str
    show_role: str
    angle: str | None
    joined_after_episodes: int
    """The episode count when this host joined: 0 for an original host."""

    def to_host(self) -> Host:
        return Host(
            self.slot, self.name, self.personality_id, self.voice_key, self.show_role, self.angle
        )

    def is_new_in(self, episode_number: int) -> bool:
        return episode_number > 1 and self.joined_after_episodes == episode_number - 1

    def has_history(self, episode_count: int) -> bool:
        return self.joined_after_episodes < episode_count

    def matches(self, draft: _HostDraft) -> bool:
        return (draft.slot, draft.name.strip(), draft.personality_id, draft.voice_key) == (
            self.slot,
            self.name,
            self.personality_id,
            self.voice_key,
        )


@dataclass(frozen=True, slots=True)
class EpisodeRef:
    conversation_id: int
    episode_number: int


@dataclass(frozen=True, slots=True)
class SeriesRecord:
    series_id: int
    show: KeptShow
    language: str
    hosts: tuple[SeriesHost, SeriesHost]
    """The lead, then the second host: both slots always, whatever the format."""
    episode_count: int
    unfinished: EpisodeRef | None

    @property
    def next_episode_number(self) -> int:
        return self.episode_count + 1

    def host(self, slot: str) -> SeriesHost:
        return next(host for host in self.hosts if host.slot == slot)

    def matches(self, draft_hosts: Iterable[_HostDraft]) -> bool:
        """The draft's hosts are the series' hosts: slot, name, personality and voice."""
        drafts = {draft.slot: draft for draft in draft_hosts}
        return drafts.keys() == {host.slot for host in self.hosts} and all(
            host.matches(drafts[host.slot]) for host in self.hosts
        )


@dataclass(frozen=True, slots=True)
class RememberedPoint:
    point_id: int
    kind: str
    conversation_language: str
    english: str
    episode_number: int


@dataclass(frozen=True, slots=True)
class PendingEpisode:
    """A series episode with lines the memory keeper has not read yet."""

    conversation_id: int
    episode_number: int
    remembered_up_to_message_id: int | None


@dataclass(frozen=True, slots=True)
class ShelfEntry:
    """One show in My shows, with its series in the current language if it has one."""

    show: KeptShow
    series: SeriesRecord | None


@dataclass(frozen=True, slots=True)
class PointText:
    conversation_language: str
    english: str


@dataclass(frozen=True, slots=True)
class MemoryReply:
    """What one memory call found: the episode's subject, and what the learner shared."""

    topic: PointText | None
    about_learner: tuple[PointText, ...]


class ShowLibraryStorage(ABC):
    @abstractmethod
    def keep(self, content: ShowContent) -> KeptShow:
        """Get or create the show's row: by template id, or by a learner-made show's content."""

    @abstractmethod
    def get(self, ref: ShowRef) -> KeptShow | None: ...

    @abstractmethod
    def set_favourite(self, show_row_id: int, is_favourite: bool) -> KeptShow | None:
        """None when unfavouriting deleted the row: nothing else keeps the show (§2.1)."""

    @abstractmethod
    def touch_played(self, show_row_id: int) -> None: ...

    @abstractmethod
    def list_mine(self, language: str) -> list[ShelfEntry]:
        """Favourites, shows with a series in `language`, and played learner-made shows,
        newest activity first (research R9)."""

    @abstractmethod
    def forget(self, saved_show_id: int) -> bool:
        """Delete a kept learner-made show and its series. False for an unknown or ready-made
        show (FR-024)."""


class SeriesStorage(ABC):
    @abstractmethod
    def find(self, show_row_id: int, language: str) -> SeriesRecord | None: ...

    @abstractmethod
    def get(self, series_id: int) -> SeriesRecord | None: ...

    @abstractmethod
    def create(
        self, show_row_id: int, language: str, hosts: tuple[SeriesHost, SeriesHost]
    ) -> SeriesRecord:
        """Raises SeriesAlreadyExists when the show has a series in `language`."""

    @abstractmethod
    def recast(self, series_id: int, host: SeriesHost) -> SeriesRecord:
        """Replace the host in `host.slot`; they join after the current episode count."""

    @abstractmethod
    def reset(self, series_id: int) -> bool:
        """Delete the series, its hosts, links and memories. False for an unknown series."""

    @abstractmethod
    def remembered(self, series_id: int) -> tuple[RememberedPoint, ...]:
        """Every remembered point, newest first."""

    @abstractmethod
    def pending_episodes(self, series_id: int) -> tuple[PendingEpisode, ...]:
        """Episodes with at least MIN_LINES_TO_REMEMBER messages after their marker."""

    @abstractmethod
    def remember(
        self,
        series_id: int,
        conversation_id: int,
        reply: MemoryReply,
        up_to_message_id: int | None,
    ) -> None:
        """Write the reply's points, prune to the caps and the text budget, and move the
        episode's marker, all in one transaction (data-model §2.5)."""
