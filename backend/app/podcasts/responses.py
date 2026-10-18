"""Building the response bodies of /api/podcasts from domain values (007 contracts §1, §2, §6;
010 contracts §1, §2, §5)."""

from app.podcasts.catalog import (
    DEFAULT_EPISODE_LENGTH,
    EPISODE_LENGTHS,
    LEARNER_POINT,
    PERSONALITIES,
    PODCAST_FORMATS,
    READY_MADE_SOURCE,
    TOPIC_POINT,
)
from app.podcasts.schemas import (
    CatalogResponse,
    CatalogVoices,
    EpisodeHostModel,
    EpisodeLineModel,
    EpisodeResponse,
    EpisodeSeriesModel,
    EpisodeShowModel,
    EpisodeSummaryRow,
    FormatOption,
    HostDraftModel,
    LengthOption,
    PersonalityOption,
    PreferencesResponse,
    RememberedModel,
    RememberedPointModel,
    SeriesDetailResponse,
    SeriesHostModel,
    SeriesSummaryModel,
    ShowDraftModel,
    ShowListing,
    UnfinishedEpisodeModel,
)
from app.podcasts.services.casting import Host
from app.podcasts.services.episode_turns import line_payload
from app.podcasts.services.episodes import LoadedEpisode, turn_actions
from app.podcasts.services.library import ShelfItem
from app.podcasts.services.series_storage import RememberedPoint, SeriesHost, SeriesRecord
from app.podcasts.services.speaker_views import host_voice_unavailable_message
from app.podcasts.services.storage import EpisodeRecord, HostRecord, PreferencesRecord
from app.podcasts.services.turn_policy import Turn
from app.practice_languages import language_name
from app.services.tts.base import VoiceInstallation


def catalogue_options() -> dict:
    """The formats, lengths and personalities, in catalogue order."""
    return {
        "formats": _format_options(),
        "lengths": _length_options(),
        "personalities": _personality_options(),
    }


def _format_options() -> list[FormatOption]:
    return [
        FormatOption(
            format_id=f.format_id,
            label=f.label,
            host_count=f.host_count,
            is_learner_speaking=f.is_learner_speaking,
            description=f.description,
        )
        for f in PODCAST_FORMATS.values()
    ]


def _length_options() -> list[LengthOption]:
    return [
        LengthOption(
            length_id=length.length_id,
            label=length.label,
            target_host_lines=length.target_host_lines,
            is_default=length.length_id == DEFAULT_EPISODE_LENGTH,
        )
        for length in EPISODE_LENGTHS.values()
    ]


def _personality_options() -> list[PersonalityOption]:
    return [
        PersonalityOption(personality_id=p.personality_id, label=p.label, description=p.description)
        for p in PERSONALITIES.values()
    ]


def catalog_response(
    language: str,
    shows: list[ShowListing],
    voices: CatalogVoices,
    my_shows: list[ShowListing],
) -> CatalogResponse:
    return CatalogResponse(
        language=language,
        language_name=language_name(language),
        shows=shows,
        my_shows=my_shows,
        voices=voices,
        **catalogue_options(),
    )


def catalog_listings(items: list[ShelfItem], language: str) -> list[ShowListing]:
    """Shows as the catalogue lists them, in the order given (FR-015)."""
    return [show_listing(item, language) for item in items]


def show_listing(item: ShelfItem, language: str) -> ShowListing:
    return ShowListing(
        source=item.source,
        show_id=item.show_id,
        saved_show_id=item.saved_show_id,
        title=item.title,
        premise=item.premise,
        topic=item.topic,
        learner_role=item.learner_role,
        language=language,
        hosts=[host_draft(host) for host in item.hosts],
        is_favourite=item.is_favourite,
        series=series_summary(item.series),
    )


def series_summary(series: SeriesRecord | None) -> SeriesSummaryModel | None:
    if series is None:
        return None
    return SeriesSummaryModel(
        series_id=series.series_id,
        episode_count=series.episode_count,
        next_episode_number=series.next_episode_number,
        unfinished_episode=_unfinished(series),
    )


def _unfinished(series: SeriesRecord) -> UnfinishedEpisodeModel | None:
    if series.unfinished is None:
        return None
    ref = series.unfinished
    return UnfinishedEpisodeModel(
        conversation_id=ref.conversation_id, episode_number=ref.episode_number
    )


def show_draft(show, hosts: tuple[Host, Host], language: str, source: str) -> ShowDraftModel:
    """A draft of `show` (a template or a generated show) with its cast hosts."""
    return ShowDraftModel(
        source=source,
        show_id=getattr(show, "show_id", None) if source == READY_MADE_SOURCE else None,
        title=show.title,
        premise=show.premise,
        topic=show.topic,
        learner_role=show.learner_role,
        language=language,
        hosts=[host_draft(host) for host in hosts],
    )


def host_draft(host: Host) -> HostDraftModel:
    return HostDraftModel(
        slot=host.slot,
        name=host.name,
        personality_id=host.personality_id,
        voice_key=host.voice_key,
        show_role=host.show_role,
        angle=host.angle,
    )


def preferences_response(preferences: PreferencesRecord) -> PreferencesResponse:
    return PreferencesResponse(
        last_format=preferences.last_format,
        is_show_text_on=preferences.is_show_text_on,
        interests=list(preferences.interests),
        learner_name=preferences.learner_name,
    )


def episode_response(
    episode: LoadedEpisode,
    turn: Turn,
    installation: VoiceInstallation,
    voice_notice: str | None,
    saved_show_id: int | None = None,
) -> EpisodeResponse:
    return EpisodeResponse(
        **_episode_fields(episode, saved_show_id),
        hosts=[_host_model(host, installation) for host in episode.hosts],
        shared_voice_notice=voice_notice,
        turn=turn.turn,
        awaiting=turn.awaiting,
        lines=[EpisodeLineModel(**line_payload(line)) for line in episode.lines],
        **turn_actions(episode.format, turn),
    )


def _episode_fields(episode: LoadedEpisode, saved_show_id: int | None) -> dict:
    """What an episode response takes straight from the stored episode and its catalogues."""
    record = episode.record
    return {
        "series": _episode_series(record),
        "conversation_id": record.conversation_id,
        "status": record.status,
        "language": record.target_language,
        "language_name": language_name(record.target_language),
        "native_language_name": language_name(record.native_language),
        "show": _show_model(record, saved_show_id),
        "format": record.format,
        "format_label": episode.format.label,
        "length": record.length,
        "target_host_lines": episode.length.target_host_lines,
        "learner_name": record.learner_name,
    }


def summary_row(record: EpisodeRecord, hosts: tuple[HostRecord, ...]) -> EpisodeSummaryRow:
    return EpisodeSummaryRow(
        conversation_id=record.conversation_id,
        show_title=record.title,
        format=record.format,
        format_label=PODCAST_FORMATS[record.format].label,
        host_names=[host.name for host in hosts],
        language=record.target_language,
        language_name=language_name(record.target_language),
        status=record.status,
        episode_number=record.series.episode_number if record.series else None,
    )


def _episode_series(record: EpisodeRecord) -> EpisodeSeriesModel | None:
    if record.series is None:
        return None
    facts = record.series
    return EpisodeSeriesModel(series_id=facts.series_id, episode_number=facts.episode_number)


def _show_model(record: EpisodeRecord, saved_show_id: int | None) -> EpisodeShowModel:
    return EpisodeShowModel(
        title=record.title,
        premise=record.premise,
        topic=record.topic,
        learner_role=record.learner_role,
        source=record.show_source,
        show_id=record.show_id,
        saved_show_id=saved_show_id,
    )


def _host_model(host: HostRecord, installation: VoiceInstallation) -> EpisodeHostModel:
    is_available = installation.is_installed(host.voice_key)
    return EpisodeHostModel(
        host_id=host.host_id,
        slot=host.slot,
        name=host.name,
        personality_id=host.personality_id,
        personality_label=PERSONALITIES[host.personality_id].label,
        voice_key=host.voice_key,
        show_role=host.show_role,
        is_voice_available=is_available,
        voice_unavailable_message=(
            None if is_available else host_voice_unavailable_message(host.name)
        ),
    )


def series_detail(
    series: SeriesRecord,
    points: tuple[RememberedPoint, ...],
    memory_status: str,
    show: ShowListing,
    installation: VoiceInstallation,
) -> SeriesDetailResponse:
    """The setup screen's view of a series: its hosts and what they remember (FR-011)."""
    return SeriesDetailResponse(
        series_id=series.series_id,
        language=series.language,
        show=show,
        episode_count=series.episode_count,
        next_episode_number=series.next_episode_number,
        unfinished_episode=_unfinished(series),
        memory_status=memory_status,
        hosts=[_series_host_model(host, series, installation) for host in series.hosts],
        remembered=_remembered_model(points),
    )


def _series_host_model(
    host: SeriesHost, series: SeriesRecord, installation: VoiceInstallation
) -> SeriesHostModel:
    is_available = installation.is_installed(host.voice_key)
    return SeriesHostModel(
        slot=host.slot,
        name=host.name,
        personality_id=host.personality_id,
        personality_label=PERSONALITIES[host.personality_id].label,
        voice_key=host.voice_key,
        show_role=host.show_role,
        has_history=host.has_history(series.episode_count),
        is_new_next_episode=host.is_new_in(series.next_episode_number),
        is_voice_available=is_available,
        voice_unavailable_message=(
            None if is_available else host_voice_unavailable_message(host.name)
        ),
    )


def _remembered_model(points: tuple[RememberedPoint, ...]) -> RememberedModel:
    """The English versions, newest first: what the learner reads (research R6)."""
    return RememberedModel(
        topics=[_point_model(p) for p in points if p.kind == TOPIC_POINT],
        about_learner=[_point_model(p) for p in points if p.kind == LEARNER_POINT],
    )


def _point_model(point: RememberedPoint) -> RememberedPointModel:
    return RememberedPointModel(
        point_id=point.point_id, text=point.english, episode_number=point.episode_number
    )
