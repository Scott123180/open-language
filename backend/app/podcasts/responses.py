"""Building the response bodies of /api/podcasts from domain values (contracts §1, §2, §6)."""

from app.podcasts.catalog import (
    DEFAULT_EPISODE_LENGTH,
    EPISODE_LENGTHS,
    PERSONALITIES,
    PODCAST_FORMATS,
)
from app.podcasts.schemas import (
    CatalogResponse,
    CatalogVoices,
    EpisodeHostModel,
    EpisodeLineModel,
    EpisodeResponse,
    EpisodeShowModel,
    EpisodeSummaryRow,
    FormatOption,
    HostDraftModel,
    LengthOption,
    PersonalityOption,
    PreferencesResponse,
    ShowDraftModel,
)
from app.podcasts.services.casting import Host
from app.podcasts.services.episode_turns import line_payload
from app.podcasts.services.episodes import LoadedEpisode, turn_actions
from app.podcasts.services.speaker_views import host_voice_unavailable_message
from app.podcasts.services.storage import EpisodeRecord, HostRecord, PreferencesRecord
from app.podcasts.services.turn_policy import Turn
from app.practice_languages import language_name
from app.services.tts.base import VoiceInstallation

READY_MADE_SOURCE = "ready_made"


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
    language: str, shows: list[ShowDraftModel], voices: CatalogVoices
) -> CatalogResponse:
    return CatalogResponse(
        language=language,
        language_name=language_name(language),
        shows=shows,
        voices=voices,
        **catalogue_options(),
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
    episode: LoadedEpisode, turn: Turn, installation: VoiceInstallation, voice_notice: str | None
) -> EpisodeResponse:
    return EpisodeResponse(
        **_episode_fields(episode),
        hosts=[_host_model(host, installation) for host in episode.hosts],
        shared_voice_notice=voice_notice,
        turn=turn.turn,
        awaiting=turn.awaiting,
        lines=[EpisodeLineModel(**line_payload(line)) for line in episode.lines],
        **turn_actions(episode.format, turn),
    )


def _episode_fields(episode: LoadedEpisode) -> dict:
    """What an episode response takes straight from the stored episode and its catalogues."""
    record = episode.record
    return {
        "conversation_id": record.conversation_id,
        "status": record.status,
        "language": record.target_language,
        "language_name": language_name(record.target_language),
        "native_language_name": language_name(record.native_language),
        "show": _show_model(record),
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
    )


def _show_model(record: EpisodeRecord) -> EpisodeShowModel:
    return EpisodeShowModel(
        title=record.title,
        premise=record.premise,
        topic=record.topic,
        learner_role=record.learner_role,
        source=record.show_source,
        show_id=record.show_id,
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
