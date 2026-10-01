"""/api/podcasts: shows, preferences and episodes (contracts §1–§8).

The router only sequences: casting, the turn policy, the line writing and storage live in
`services/`. Every line-producing action takes the episode's lock first, so one line is made
at a time, then checks the turn state, and answers a disallowed action with a plain 409.
"""

import asyncio
import random
from collections.abc import AsyncIterator, Callable
from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.conversation_levels import ConversationLevel
from app.conversation_turns import Corrections, LearnerMessageRequest
from app.corrections.services.storage import CorrectionStorageProvider
from app.corrections.services.strategies import CorrectionStrategy
from app.podcasts.catalog import LEAD_SLOT, PODCAST_FORMATS, SHOW_TEMPLATES
from app.podcasts.host_routes import host_router
from app.podcasts.responses import (
    READY_MADE_SOURCE,
    catalog_response,
    episode_response,
    preferences_response,
    show_draft,
    summary_row,
)
from app.podcasts.schemas import (
    CatalogResponse,
    CatalogVoices,
    EpisodeResponse,
    EpisodeSummaryRow,
    PreferencesResponse,
    StartEpisodeRequest,
    UpdatePreferencesRequest,
    validate_draft,
)
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.episode_lock import EpisodeLocks, HeldEpisode
from app.podcasts.services.episode_turns import EpisodeDependencies, EpisodeTurns
from app.podcasts.services.episodes import LoadedEpisode, load_episode
from app.podcasts.services.storage import NewEpisode, NewHost, PodcastStorage, PreferencesRecord
from app.podcasts.services.suggestions import parse_suggestions, suggestion_prompt
from app.podcasts.services.turn_policy import (
    AWAITING_CONTINUE,
    AWAITING_OPENING,
    LEARNER_TURN,
    TurnPolicy,
)
from app.podcasts.services.voice_notices import catalogue_notices, episode_voice_notice
from app.podcasts.show_routes import show_router
from app.services.conversation import ConversationEngine, SessionCapableProvider
from app.services.factory import (
    get_app_settings,
    get_conversation_engine,
    get_correction_storage,
    get_correction_strategy,
    get_episode_locks,
    get_host_caster,
    get_llm,
    get_podcast_storage,
    get_session_provider,
    get_speech_for_language,
    get_storage,
    get_voice_installation,
)
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.tts.base import VoiceInstallation
from app.services.tts.selection import SpeechForLanguage
from app.services.tts.voices import voices_for

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])

SSE_MEDIA_TYPE = "text/event-stream"
EPISODE_NOT_FOUND = "Episode not found"
LINE_NOT_FOUND = "That line isn't a host line of this episode."
LINE_IN_PROGRESS = "A line is already on its way."
EPISODE_FINISHED = "This episode has finished."
YOUR_TURN = "It's your turn. Reply, pass or end the episode."
LISTENING_EPISODE = "This is a listening episode. Start the show in One host or Panel to speak."
PASS_ONLY_IN_PANEL = "You can pass only when it's your turn in a Panel."
WAIT_FOR_HOSTS = "Wait for the hosts' line, then reply."
USER_ROLE = "user"

TurnCheck = Callable[[EpisodeTurns, LoadedEpisode], None]


def get_turn_policy() -> TurnPolicy:
    """A policy drawing from fresh randomness per request; tests inject a seeded one."""
    return TurnPolicy(random.Random())


# --- catalogue and preferences (contracts §1, §2) ---------------------------------------


@router.get("/catalog", response_model=CatalogResponse)
def get_catalog(
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    podcasts: PodcastStorage = Depends(get_podcast_storage),
    caster: HostCaster = Depends(get_host_caster),
    installation: VoiceInstallation = Depends(get_voice_installation),
):
    language = app_settings.target_language
    learner_name = podcasts.get_preferences().learner_name
    shows = [
        show_draft(
            show, caster.cast_template(show, language, learner_name), language, READY_MADE_SOURCE
        )
        for show in SHOW_TEMPLATES.values()
    ]
    return catalog_response(language, shows, _catalog_voices(language, installation))


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(podcasts: PodcastStorage = Depends(get_podcast_storage)):
    return preferences_response(podcasts.get_preferences())


@router.put("/preferences", response_model=PreferencesResponse)
def update_preferences(
    req: UpdatePreferencesRequest, podcasts: PodcastStorage = Depends(get_podcast_storage)
):
    updated = _apply_preferences(podcasts.get_preferences(), req)
    return preferences_response(podcasts.save_preferences(updated))


def _apply_preferences(
    stored: PreferencesRecord, req: UpdatePreferencesRequest
) -> PreferencesRecord:
    changes: dict = {}
    if req.is_show_text_on is not None:
        changes["is_show_text_on"] = req.is_show_text_on
    if req.interests is not None:
        changes["interests"] = tuple(req.interests)
    if "learner_name" in req.model_fields_set:
        changes["learner_name"] = req.learner_name
    return replace(stored, **changes)


def _installed_count(language: str, installation: VoiceInstallation) -> int:
    return sum(1 for voice in voices_for(language) if installation.is_installed(voice.key))


def _catalog_voices(language: str, installation: VoiceInstallation) -> CatalogVoices:
    count = _installed_count(language, installation)
    return CatalogVoices(installed_count=count, **catalogue_notices(language, count))


# --- episodes (contracts §6) ------------------------------------------------------------


@router.post("/episodes", status_code=201, response_model=EpisodeResponse)
def start_episode(
    req: StartEpisodeRequest,
    podcasts: PodcastStorage = Depends(get_podcast_storage),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    installation: VoiceInstallation = Depends(get_voice_installation),
    policy: TurnPolicy = Depends(get_turn_policy),
):
    language = app_settings.target_language
    installed = _installed_count(language, installation)
    problem = validate_draft(req.show, language, req.learner_name, installed)
    if problem is not None:
        raise HTTPException(status_code=422, detail=problem)
    record = podcasts.create_episode(_new_episode(req, app_settings))
    _remember_start(podcasts, req)
    episode = load_episode(podcasts, record.conversation_id)
    notice = episode_voice_notice(episode)
    return episode_response(episode, policy.turn(episode.state), installation, notice)


def _new_episode(req: StartEpisodeRequest, app_settings: AppSettingsRecord) -> NewEpisode:
    show = req.show
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
        target_language=app_settings.target_language,
        native_language=app_settings.native_language,
        llm_model=app_settings.llm_model,
        hosts=_participating_hosts(req),
    )


def _participating_hosts(req: StartEpisodeRequest) -> tuple[NewHost, ...]:
    """Every host of the draft, or only the lead in a one-host format (FR-003)."""
    hosts = sorted(req.show.hosts, key=lambda host: host.slot != LEAD_SLOT)
    count = PODCAST_FORMATS[req.format].host_count
    return tuple(
        NewHost(h.slot, h.name.strip(), h.personality_id, h.voice_key, h.show_role, h.angle)
        for h in hosts[:count]
    )


def _remember_start(podcasts: PodcastStorage, req: StartEpisodeRequest) -> None:
    """FR-005: the next setup starts on this format; FR-011: and with this name."""
    changes: dict = {"last_format": req.format}
    if req.learner_name is not None:
        changes["learner_name"] = req.learner_name
    podcasts.save_preferences(replace(podcasts.get_preferences(), **changes))


@router.get("/episodes", response_model=list[EpisodeSummaryRow])
def list_episodes(podcasts: PodcastStorage = Depends(get_podcast_storage)):
    return [
        summary_row(record, podcasts.get_hosts(record.conversation_id))
        for record in podcasts.list_episodes()
    ]


def _episode_turns(
    conversation_id: int,
    podcasts: PodcastStorage = Depends(get_podcast_storage),
    conversations: StorageProvider = Depends(get_storage),
    correction_storage: CorrectionStorageProvider = Depends(get_correction_storage),
    engine: ConversationEngine = Depends(get_conversation_engine),
    provider: SessionCapableProvider = Depends(get_session_provider),
    speech: SpeechForLanguage = Depends(get_speech_for_language),
    policy: TurnPolicy = Depends(get_turn_policy),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
) -> EpisodeTurns:
    level = ConversationLevel(app_settings.conversation_level)
    deps = EpisodeDependencies(
        podcasts, conversations, correction_storage, engine, provider, speech, policy, level
    )
    return EpisodeTurns(deps, conversation_id)


def _require_episode(turns: EpisodeTurns) -> LoadedEpisode:
    episode = turns.load()
    if episode is None:
        raise HTTPException(status_code=404, detail=EPISODE_NOT_FOUND)
    return episode


@router.get("/episodes/{conversation_id}", response_model=EpisodeResponse)
def get_episode(
    turns: EpisodeTurns = Depends(_episode_turns),
    installation: VoiceInstallation = Depends(get_voice_installation),
):
    episode = _require_episode(turns)
    return episode_response(
        episode, turns.turn(episode), installation, episode_voice_notice(episode)
    )


# --- line-producing actions (contracts §7) ----------------------------------------------


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def _check_next(turns: EpisodeTurns, episode: LoadedEpisode) -> None:
    if episode.is_finished:
        raise _conflict(EPISODE_FINISHED)
    if turns.turn(episode).turn == LEARNER_TURN:
        raise _conflict(YOUR_TURN)


def _check_message(turns: EpisodeTurns, episode: LoadedEpisode) -> None:
    if not episode.format.is_learner_speaking:
        raise _conflict(LISTENING_EPISODE)
    if episode.is_finished:
        raise _conflict(EPISODE_FINISHED)
    awaiting = turns.turn(episode).awaiting
    is_jump_in = awaiting == AWAITING_CONTINUE and episode.format.has_jump_in
    if awaiting == AWAITING_OPENING or (awaiting == AWAITING_CONTINUE and not is_jump_in):
        raise _conflict(WAIT_FOR_HOSTS)


def _check_pass(turns: EpisodeTurns, episode: LoadedEpisode) -> None:
    if episode.is_finished:
        raise _conflict(EPISODE_FINISHED)
    if not episode.format.has_jump_in or turns.turn(episode).turn != LEARNER_TURN:
        raise _conflict(PASS_ONLY_IN_PANEL)


def _check_end(turns: EpisodeTurns, episode: LoadedEpisode) -> None:
    if episode.is_finished:
        raise _conflict(EPISODE_FINISHED)


def _guarded_stream(
    turns: EpisodeTurns,
    locks: EpisodeLocks,
    check: TurnCheck,
    frames: Callable[[], AsyncIterator[str]],
) -> StreamingResponse:
    """Hold the episode's lock for the whole line; refuse at once if a line is on its way."""
    held = locks.try_acquire(turns.conversation_id)
    if held is None:
        raise _conflict(LINE_IN_PROGRESS)
    try:
        check(turns, _require_episode(turns))
    except HTTPException:
        held.release()
        raise
    return StreamingResponse(_holding(held, frames()), media_type=SSE_MEDIA_TYPE)


async def _holding(held: HeldEpisode, frames: AsyncIterator[str]) -> AsyncIterator[str]:
    with held:
        async for frame in frames:
            yield frame


@router.post("/episodes/{conversation_id}/next")
def next_line(
    turns: EpisodeTurns = Depends(_episode_turns),
    locks: EpisodeLocks = Depends(get_episode_locks),
):
    return _guarded_stream(turns, locks, _check_next, turns.next_line_events)


@router.post("/episodes/{conversation_id}/message")
def send_message(
    req: LearnerMessageRequest,
    turns: EpisodeTurns = Depends(_episode_turns),
    locks: EpisodeLocks = Depends(get_episode_locks),
    strategy: CorrectionStrategy = Depends(get_correction_strategy),
    correction_storage: CorrectionStorageProvider = Depends(get_correction_storage),
):
    corrections = Corrections(strategy, correction_storage)
    return _guarded_stream(
        turns, locks, _check_message, lambda: turns.learner_events(req, corrections)
    )


@router.post("/episodes/{conversation_id}/pass")
def pass_turn(
    turns: EpisodeTurns = Depends(_episode_turns),
    locks: EpisodeLocks = Depends(get_episode_locks),
):
    return _guarded_stream(turns, locks, _check_pass, turns.pass_events)


@router.post("/episodes/{conversation_id}/end")
def end_episode(
    turns: EpisodeTurns = Depends(_episode_turns),
    locks: EpisodeLocks = Depends(get_episode_locks),
):
    return _guarded_stream(turns, locks, _check_end, turns.end_events)


# --- other episode endpoints (contracts §8) ---------------------------------------------


@router.post("/episodes/{conversation_id}/lines/{message_id}/reveal", status_code=204)
def reveal_line(
    conversation_id: int, message_id: int, podcasts: PodcastStorage = Depends(get_podcast_storage)
):
    """FR-043: a tapped Listen line stays revealed for the rest of the episode."""
    if not podcasts.mark_revealed(conversation_id, message_id):
        raise HTTPException(status_code=404, detail=LINE_NOT_FOUND)
    return Response(status_code=204)


@router.post("/episodes/{conversation_id}/session", status_code=202)
async def warm_session(turns: EpisodeTurns = Depends(_episode_turns)):
    episode = _require_episode(turns)
    _check_end(turns, episode)
    return {"status": turns.warm(episode)}


@router.post("/episodes/{conversation_id}/suggestions")
async def get_suggestions(
    turns: EpisodeTurns = Depends(_episode_turns),
    llm: LLMProvider = Depends(get_llm),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    episode = _require_episode(turns)
    if not episode.format.is_learner_speaking:
        raise _conflict(LISTENING_EPISODE)
    level = ConversationLevel(app_settings.conversation_level)
    count = app_settings.suggestion_count
    prompt = suggestion_prompt(episode, count, level)
    reply = await asyncio.get_running_loop().run_in_executor(
        None, llm.chat, [ChatMessage(role=USER_ROLE, content=prompt)]
    )
    return {"suggestions": parse_suggestions(reply, count)}


router.include_router(show_router)
router.include_router(host_router)
