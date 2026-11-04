"""SeriesService: which hosts and memory an episode starts with (010 data-model §5.2).

A series' first episode fixes its hosts from the draft, after any Shuffle. A later episode must
start with the series' hosts: they are checked, never trusted, so a stale draft is refused with
a plain 409 rather than silently overruled (SC-001, research R2). The memory an episode starts
with is frozen into its snapshot here (research R5).
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.podcasts.catalog import (
    DEFAULT_EPISODE_STYLE,
    DEFAULT_HOST_LINE_LENGTH,
    DEFAULT_INVITE_FREQUENCY,
    HOST_SLOTS,
    LEAD_SLOT,
    LEARNER_POINT,
    PERSONALITIES,
    PODCAST_FORMATS,
    READY_MADE_SOURCE,
    SERIES_KIND,
    SERIES_SETTING_NAMES,
    TOPIC_POINT,
)
from app.podcasts.schemas import (
    LANGUAGE_CHANGED,
    SERIES_CLASH,
    EpisodeSettingsModel,
    GuestRequest,
    HostDraftModel,
    StartEpisodeRequest,
    guest_problem,
    show_problem,
    validate_draft,
)
from app.podcasts.services.casting import Host, HostCaster
from app.podcasts.services.episode_settings import EpisodeSettings
from app.podcasts.services.library import ShowLibrary
from app.podcasts.services.series_settings import SeriesSettings
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
SERIES_GONE = "That series isn't there any more. Open the show again."
PERSONALITY_TAKEN = "{other} already has that personality. Pick another one."
UNKNOWN_PERSONALITY = "That personality isn't in the list. Pick one of the listed ones."
NOT_KEPT_FOR_LATER = "That setting can't be kept for later episodes."
ONE_OFF_KEEPS_NOTHING = "Only a series keeps settings for later episodes."
GUEST_TOO_EARLY = "A guest can join from the second episode."
ONE_OFF_GUEST = "Only a series episode can have a guest."
GUEST_HAS_NO_SEAT = (
    "That guest has no seat in this format. Pick Panel, or invite them in the host's place."
)
GUEST_IS_A_HOST = "{name} is already a host of this show. Invite another guest."

InstalledCount = Callable[[str], int]
"""How many voices are installed for a language."""


class StartRefused(ValueError):  # noqa: N818 — reads as what happened to the start
    """The draft cannot start an episode; the message says why and what to do (422)."""


class SeriesHostsChanged(ValueError):  # noqa: N818 — reads as what the learner is told
    """The draft's hosts are not the series' hosts: the screen is stale (409)."""

    def __init__(self) -> None:
        super().__init__(SERIES_HOSTS_CHANGED)


class SeriesNotFound(LookupError):  # noqa: N818 — reads as what the learner is told
    def __init__(self) -> None:
        super().__init__(SERIES_GONE)


class LanguageChanged(ValueError):  # noqa: N818 — reads as what happened
    """A series of another practice language cannot be changed from this one (422)."""

    def __init__(self) -> None:
        super().__init__(LANGUAGE_CHANGED)


class PersonalityTaken(ValueError):  # noqa: N818 — reads as what the learner is told
    """Two hosts never share a personality (422)."""


@dataclass(frozen=True)
class PreparedStart:
    """Everything an episode needs beyond the request: its hosts and its series link."""

    request: StartEpisodeRequest
    hosts: tuple[NewHost, ...]
    series: NewSeriesLink | None
    saved_show_id: int | None
    settings: EpisodeSettings
    """How the episode sounds, frozen into it at Start (011 FR-012)."""


class SeriesService:
    def __init__(
        self,
        library: ShowLibrary,
        series: SeriesStorage,
        installed_count: InstalledCount,
        caster: HostCaster,
    ) -> None:
        self._library = library
        self._series = series
        self._installed_count = installed_count
        self._caster = caster

    def prepare(self, req: StartEpisodeRequest, settings: AppSettingsRecord) -> PreparedStart:
        """Check the draft, keep the show and, for a series, find or create it."""
        if req.kind == SERIES_KIND:
            return self._series_start(req, settings.target_language)
        return self._one_off_start(req, settings.target_language)

    def recast(
        self,
        series_id: int,
        slot: str,
        personality_id: str | None,
        learner_name: str | None,
        language: str,
    ) -> SeriesRecord:
        """Replace one host for this and every later episode (FR-009, research R8)."""
        series = self._require(series_id)
        if series.language != language:
            raise LanguageChanged()
        _check_personality(series, slot, personality_id)
        hosts = tuple(host.to_host() for host in series.hosts)
        new = self._caster.recast(slot, hosts, learner_name, personality_id=personality_id)
        replacement = SeriesHost(
            slot, new.name, new.personality_id, new.voice_key, new.show_role, None, 0
        )
        return self._series.recast(series_id, replacement)

    def reset_settings(self, series_id: int, language: str) -> SeriesRecord:
        """Back to the show's standard settings (011 FR-019)."""
        series = self._require(series_id)
        if series.language != language:
            raise LanguageChanged()
        self._series.reset_settings(series_id)
        return self._require(series_id)

    def cast_guest(self, series_id: int, req: GuestRequest) -> Host:
        """A guest for one episode in `req.slot`, beside the other host (011 research R10)."""
        series = self._require(series_id)
        if series.language != req.language:
            raise LanguageChanged()
        if req.slot not in _used_slots(req.format):
            raise StartRefused(GUEST_HAS_NO_SEAT)
        _check_personality(series, req.slot, req.personality_id)
        other = next(host for host in series.hosts if host.slot != req.slot)
        avoid = (*(host.name for host in series.hosts), *req.avoid_names, req.learner_name or "")
        personality = req.personality_id or _expert_for(series, req.slot, other)
        return self._caster.cast_guest(
            req.slot, personality, (other.to_host(),), avoid, series.language
        )

    def reset(self, series_id: int) -> bool:
        """Start over: forget the series; its episodes stay in Past Chats (FR-011)."""
        self._require(series_id)
        return self._series.reset(series_id)

    def _require(self, series_id: int) -> SeriesRecord:
        series = self._series.get(series_id)
        if series is None:
            raise SeriesNotFound()
        return series

    def new_episode(self, prepared: PreparedStart, settings: AppSettingsRecord) -> NewEpisode:
        req, show = prepared.request, prepared.request.show
        return NewEpisode(
            show_source=show.source,
            show_id=show.show_id,
            title=show.title,
            premise=show.premise,
            topic=show.topic,
            learner_role=prepared.settings.learner_role,
            format=req.format,
            length=req.length,
            learner_name=req.learner_name,
            target_language=settings.target_language,
            native_language=settings.native_language,
            llm_model=settings.llm_model,
            hosts=prepared.hosts,
            series=prepared.series,
            settings=prepared.settings,
        )

    def _series_start(self, req: StartEpisodeRequest, language: str) -> PreparedStart:
        known = self._library.resolve(req.show)
        series = self._series.find(known.show_row_id, language) if known else None
        self._check_series_draft(req, series, language)
        self._check_extras(req, series, language)
        kept = self._library.keep(req.show)
        self._library.played(kept)
        settings = episode_settings(req, _draft_second(req).personality_id)
        chosen = _chosen_settings(req, settings)
        is_first = series is None
        series = series or self._create(kept, req, language, chosen)
        update = chosen if is_first else _kept_for_later(series, chosen, req.from_now_on)
        hosts = _participating(series, req)
        link = self._link(series, req, hosts, update)
        return PreparedStart(req, hosts, link, kept.ref.saved_show_id, settings)

    def _check_extras(
        self, req: StartEpisodeRequest, series: SeriesRecord | None, language: str
    ) -> None:
        """011 §5.2: what a series episode keeps for later, and its guest."""
        if any(name not in SERIES_SETTING_NAMES for name in req.from_now_on):
            raise StartRefused(NOT_KEPT_FOR_LATER)
        if req.guest is None:
            return
        if series is None:
            raise StartRefused(GUEST_TOO_EARLY)
        self._refuse(self._guest_problem(req, series, language))

    def _guest_problem(
        self, req: StartEpisodeRequest, series: SeriesRecord, language: str
    ) -> str | None:
        guest = req.guest
        if guest.slot not in _used_slots(req.format):
            return GUEST_HAS_NO_SEAT
        name = guest.name.strip().casefold()
        host = next((h for h in series.hosts if h.name.casefold() == name), None)
        if host is not None:
            return GUEST_IS_A_HOST.format(name=host.name)
        other = _host_draft(next(h for h in series.hosts if h.slot != guest.slot))
        installed = self._installed_count(language)
        return guest_problem(guest, other, language, req.learner_name, installed)

    def _one_off_start(self, req: StartEpisodeRequest, language: str) -> PreparedStart:
        """007's start, unchanged; a learner-made show is kept by playing it (FR-014)."""
        if req.from_now_on:
            raise StartRefused(ONE_OFF_KEEPS_NOTHING)
        if req.guest is not None:
            raise StartRefused(ONE_OFF_GUEST)
        installed = self._installed_count(language)
        self._refuse(validate_draft(req.show, language, req.learner_name, installed))
        settings = episode_settings(req, _draft_second(req).personality_id)
        return PreparedStart(req, _draft_hosts(req), None, self._play_one_off(req.show), settings)

    def _play_one_off(self, draft) -> int | None:
        """Keep a learner-made show; touch a ready-made one only if it is already kept."""
        if draft.source == READY_MADE_SOURCE:
            kept = self._library.resolve(draft)
        else:
            kept = self._library.keep(draft)
        if kept is not None:
            self._library.played(kept)
        return kept.ref.saved_show_id if kept is not None else None

    def _check_series_draft(
        self, req: StartEpisodeRequest, series: SeriesRecord | None, language: str
    ) -> None:
        """Episode 1 is checked as 007 checks a draft; later ones keep the series' hosts, whose
        names never change, so a clash with the learner's name is theirs to fix (R8)."""
        if series is None:
            installed = self._installed_count(language)
            draft, name = req.show, req.learner_name
            return self._refuse(validate_draft(draft, language, name, installed, SERIES_CLASH))
        self._refuse(show_problem(req.show, language))
        if not series.matches(req.show.hosts):
            raise SeriesHostsChanged()
        self._refuse(_name_clash(series, req.learner_name))

    def _create(
        self, kept: KeptShow, req: StartEpisodeRequest, language: str, usual: SeriesSettings
    ) -> SeriesRecord:
        hosts = tuple(_series_host(draft) for draft in _lead_first(req.show.hosts))
        try:
            return self._series.create(kept.show_row_id, language, hosts, usual)
        except SeriesAlreadyExists as raced:
            raise SeriesHostsChanged() from raced

    def _link(
        self,
        series: SeriesRecord,
        req: StartEpisodeRequest,
        hosts: tuple[NewHost, ...],
        update: SeriesSettings | None,
    ) -> NewSeriesLink:
        guest_slot = req.guest.slot if req.guest else None
        snapshot = self._snapshot(series, hosts, guest_slot)
        return NewSeriesLink(series.series_id, series.next_episode_number, snapshot, update)

    def _snapshot(
        self, series: SeriesRecord, hosts: tuple[NewHost, ...], guest_slot: str | None
    ) -> SeriesSnapshot:
        """The bounded memory, newest first, who joins the series in this episode, and today's
        guest (011)."""
        points = self._series.remembered(series.series_id)
        return SeriesSnapshot(
            episode_number=series.next_episode_number,
            topics_covered=tuple(p.conversation_language for p in points if p.kind == TOPIC_POINT),
            about_learner=tuple(p.conversation_language for p in points if p.kind == LEARNER_POINT),
            new_host_slots=self._joining_slots(series, hosts, guest_slot),
            guest_slot=guest_slot,
        )

    def _joining_slots(
        self, series: SeriesRecord, hosts: tuple[NewHost, ...], guest_slot: str | None
    ) -> tuple[str, ...]:
        """Regular hosts in this episode who are new to the show: just recast (010), or never
        in an episode yet, such as a One host series' second host (011 R12)."""
        count = series.episode_count
        if count < 1:
            return ()
        heard = set().union(*self._series.hosts_present(series.series_id).values())
        taking_part = {host.slot for host in hosts} - {guest_slot}
        return tuple(
            host.slot
            for host in series.hosts
            if host.slot in taking_part
            and (host.joined_after_episodes == count or host.name not in heard)
        )

    @staticmethod
    def _refuse(problem: str | None) -> None:
        if problem is not None:
            raise StartRefused(problem)


def _check_personality(series: SeriesRecord, slot: str, personality_id: str | None) -> None:
    if personality_id is None:
        return
    if personality_id not in PERSONALITIES:
        raise StartRefused(UNKNOWN_PERSONALITY)
    other = next(host for host in series.hosts if host.slot != slot)
    if other.personality_id == personality_id:
        raise PersonalityTaken(PERSONALITY_TAKEN.format(other=other.name))


def _expert_for(series: SeriesRecord, slot: str, other: SeriesHost) -> str | None:
    """The show's second personality sits in the second seat of a One host series (FR-024a),
    unless the lead has it; otherwise the caster picks a free one."""
    expert = series.show.personalities[1]
    is_one_host = PODCAST_FORMATS[series.settings.format].host_count == 1
    is_one_host_seat = slot != LEAD_SLOT and is_one_host
    return expert if is_one_host_seat and expert != other.personality_id else None


def _name_clash(series: SeriesRecord, learner_name: str | None) -> str | None:
    if not learner_name:
        return None
    clashing = next((h for h in series.hosts if h.name.casefold() == learner_name.casefold()), None)
    return SERIES_CLASH.format(name=clashing.name) if clashing else None


def episode_settings(req: StartEpisodeRequest, second_personality: str) -> EpisodeSettings:
    """The request's settings, each missing one at its default and the role at the show's; in
    Listen nobody is asked and the learner only listens. One host covers the absent second
    host (011 R6)."""
    chosen = req.settings or EpisodeSettingsModel()
    podcast_format = PODCAST_FORMATS[req.format]
    is_listening = not podcast_format.is_learner_speaking
    frequency = None if is_listening else chosen.invite_frequency
    role = None if is_listening else chosen.learner_role
    return EpisodeSettings.from_ids(
        style=chosen.style or DEFAULT_EPISODE_STYLE,
        line_length=chosen.line_length or DEFAULT_HOST_LINE_LENGTH,
        invite_frequency=frequency or DEFAULT_INVITE_FREQUENCY,
        learner_role=role or req.show.learner_role,
        today_subject=chosen.today_subject,
        covered_personality=second_personality if podcast_format.host_count == 1 else None,
    )


def _draft_second(req: StartEpisodeRequest) -> HostDraftModel:
    return next(host for host in req.show.hosts if host.slot != LEAD_SLOT)


def _lead_first(hosts):
    return sorted(hosts, key=lambda host: host.slot != LEAD_SLOT)


def _series_host(draft: HostDraftModel) -> SeriesHost:
    name = draft.name.strip()
    return SeriesHost(
        draft.slot, name, draft.personality_id, draft.voice_key, draft.show_role, draft.angle, 0
    )


def _participating(series: SeriesRecord, req: StartEpisodeRequest) -> tuple[NewHost, ...]:
    """The series' hosts for the format's slots, the lead alone in One host (FR-003), with
    today's guest in their slot (011 FR-020)."""
    count = PODCAST_FORMATS[req.format].host_count
    hosts = tuple(_new_host(host) for host in series.hosts[:count])
    guest = req.guest
    if guest is None:
        return hosts
    return tuple(_draft_host(guest) if host.slot == guest.slot else host for host in hosts)


def _used_slots(format_id: str) -> tuple[str, ...]:
    return HOST_SLOTS[: PODCAST_FORMATS[format_id].host_count]


def _chosen_settings(req: StartEpisodeRequest, settings: EpisodeSettings) -> SeriesSettings:
    """This episode's choices, in the form a series keeps them."""
    return SeriesSettings(
        format=req.format,
        length=req.length,
        style=settings.style.style_id,
        line_length=settings.line_length.line_length_id,
        invite_frequency=settings.invite_frequency.invite_frequency_id,
        learner_role=settings.learner_role,
    )


def _kept_for_later(
    series: SeriesRecord, chosen: SeriesSettings, names: list[str]
) -> SeriesSettings | None:
    return series.settings.with_changes(chosen, tuple(names)) if names else None


def _host_draft(host: SeriesHost) -> HostDraftModel:
    return HostDraftModel(
        slot=host.slot,
        name=host.name,
        personality_id=host.personality_id,
        voice_key=host.voice_key,
        show_role=host.show_role,
        angle=host.angle,
    )


def _draft_host(draft: HostDraftModel) -> NewHost:
    return NewHost(
        draft.slot,
        draft.name.strip(),
        draft.personality_id,
        draft.voice_key,
        draft.show_role,
        draft.angle,
    )


def _new_host(host: SeriesHost) -> NewHost:
    return NewHost(
        host.slot, host.name, host.personality_id, host.voice_key, host.show_role, host.angle
    )


def _draft_hosts(req: StartEpisodeRequest) -> tuple[NewHost, ...]:
    """Every host of the draft, or only the lead in a one-host format (FR-003)."""
    count = PODCAST_FORMATS[req.format].host_count
    return tuple(_draft_host(h) for h in _lead_first(req.show.hosts)[:count])
