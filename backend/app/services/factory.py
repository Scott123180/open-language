import random
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from functools import lru_cache, partial

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.conversation_summary import SpeakerNames
from app.conversation_summary.services.sqlite_storage import SQLiteSummaryStorage
from app.conversation_summary.services.storage import SummaryStorage
from app.corrections import build_correction_strategy
from app.corrections.services.evaluator import LlmCorrectionEvaluator
from app.corrections.services.sqlite_storage import SQLiteCorrectionStorageProvider
from app.corrections.services.storage import CorrectionStorageProvider
from app.corrections.services.strategies import CorrectionStrategy
from app.database import get_db
from app.flashcards.services.sqlite_storage import SQLiteFlashcardStorageProvider
from app.flashcards.services.storage import FlashcardStorageProvider
from app.podcasts.services.casting import HostCaster
from app.podcasts.services.episode_lock import EpisodeLocks
from app.podcasts.services.speaker_views import PodcastMessageVoices, PodcastSpeakerNames
from app.podcasts.services.sqlite_storage import SQLitePodcastStorage
from app.podcasts.services.storage import PodcastStorage
from app.podcasts.services.surprise import RecentSurprises
from app.practice_languages import voice_for, voice_unavailable_message
from app.services.conversation import (
    ConversationEngine,
    ConversationSessionPool,
    SessionCapableProvider,
)
from app.services.helper_sessions import HelperSessionStore
from app.services.llm.availability import ProviderAvailabilityChecker
from app.services.llm.base import LLMProvider, StructuredLLMProvider
from app.services.llm.registry import (
    ConfiguredLLMProvider,
    build_availability_checkers,
    build_llm_provider,
)
from app.services.llm.selection_types import LLMSelection
from app.services.scenario.base import ScenarioProvider
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.storage.sqlite import SQLiteStorageProvider
from app.services.stt.base import STTProvider
from app.services.tts.base import MessageVoiceLookup, TTSProvider, VoiceInstallation
from app.services.tts.selection import SpeechForLanguage


@lru_cache
def _get_scenario_provider() -> ScenarioProvider:
    return StaticScenarioProvider()


def get_scenario_provider() -> ScenarioProvider:
    return _get_scenario_provider()


@lru_cache
def _get_helper_sessions() -> HelperSessionStore:
    return HelperSessionStore()


def get_helper_sessions() -> HelperSessionStore:
    return _get_helper_sessions()


@lru_cache
def get_conversation_engine() -> ConversationEngine:
    """One engine per process: its pool holds every live conversation session."""
    settings = get_settings()
    pool = ConversationSessionPool(
        settings.session_max_live,
        timedelta(minutes=settings.session_idle_ttl_minutes),
        clock=lambda: datetime.now(UTC),
    )
    return ConversationEngine(pool)


def get_storage(db: Session = Depends(get_db)) -> StorageProvider:
    return SQLiteStorageProvider(db)


def get_flashcard_storage(db: Session = Depends(get_db)) -> FlashcardStorageProvider:
    return SQLiteFlashcardStorageProvider(db)


def get_correction_storage(db: Session = Depends(get_db)) -> CorrectionStorageProvider:
    return SQLiteCorrectionStorageProvider(db)


def get_app_settings(storage: StorageProvider = Depends(get_storage)) -> AppSettingsRecord:
    return storage.get_settings()


def _configured_provider(app_settings: AppSettingsRecord) -> ConfiguredLLMProvider:
    selection = LLMSelection(app_settings.llm_provider, app_settings.llm_model)
    return build_llm_provider(selection, get_settings(), app_settings.llm_effort)


def get_llm(app_settings: AppSettingsRecord = Depends(get_app_settings)) -> LLMProvider:
    return _configured_provider(app_settings)


def get_structured_llm(
    app_settings: AppSettingsRecord = Depends(get_app_settings),
) -> StructuredLLMProvider:
    return _configured_provider(app_settings)


def get_session_provider(
    app_settings: AppSettingsRecord = Depends(get_app_settings),
) -> SessionCapableProvider:
    return _configured_provider(app_settings)


def get_availability_checkers() -> Mapping[str, ProviderAvailabilityChecker]:
    return build_availability_checkers(get_settings())


def get_voice_installation() -> VoiceInstallation:
    from app.services.tts.piper import PiperVoiceInstallation

    return PiperVoiceInstallation(get_settings().voice_dir)


def get_speech_for_language(
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    installation: VoiceInstallation = Depends(get_voice_installation),
) -> SpeechForLanguage:
    """The only place a TTS voice becomes a Piper provider (Principle VI)."""
    return SpeechForLanguage(
        resolve_voice=partial(voice_for, voice_choices=app_settings.voice_choices),
        installation=installation,
        build=_build_piper_voice,
        unavailable_message=voice_unavailable_message,
    )


def _build_piper_voice(voice_key: str) -> TTSProvider:
    from app.services.tts.piper import PiperTTSProvider

    return PiperTTSProvider(voice_name=voice_key, voice_dir=get_settings().voice_dir)


_stt_providers: dict[str, "STTProvider"] = {}


def get_stt(app_settings: AppSettingsRecord = Depends(get_app_settings)) -> STTProvider:
    from app.services.stt.whisper import WhisperSTTProvider

    model_size = app_settings.whisper_model
    if model_size not in _stt_providers:
        settings = get_settings()
        _stt_providers[model_size] = WhisperSTTProvider(
            model_size=model_size, device=settings.whisper_device
        )
    return _stt_providers[model_size]


def get_podcast_storage(db: Session = Depends(get_db)) -> PodcastStorage:
    return SQLitePodcastStorage(db)


def get_message_voices(
    podcasts: PodcastStorage = Depends(get_podcast_storage),
    conversations: StorageProvider = Depends(get_storage),
) -> MessageVoiceLookup:
    """A host line is spoken in its host's voice; the audio router never imports podcasts."""
    return PodcastMessageVoices(podcasts, conversations)


def get_summary_storage(db: Session = Depends(get_db)) -> SummaryStorage:
    return SQLiteSummaryStorage(db)


class _PodcastSpeakerNamesAdapter(SpeakerNames):
    """The podcast names, as the summary module asks for them. Neither module imports the other."""

    def __init__(self, names: PodcastSpeakerNames) -> None:
        self._names = names

    def names_for(self, conversation_id: int) -> Mapping[int, str] | None:
        return self._names.names_for(conversation_id)


def get_speaker_names(
    podcasts: PodcastStorage = Depends(get_podcast_storage),
    conversations: StorageProvider = Depends(get_storage),
) -> SpeakerNames:
    return _PodcastSpeakerNamesAdapter(PodcastSpeakerNames(podcasts, conversations))


@lru_cache
def get_episode_locks() -> EpisodeLocks:
    """One per process: a line in progress is guarded across every request (research R12)."""
    return EpisodeLocks()


@lru_cache
def get_recent_surprises() -> RecentSurprises:
    """One per process: Surprise me never repeats one of its last ideas (research R9)."""
    return RecentSurprises()


def get_host_caster(
    installation: VoiceInstallation = Depends(get_voice_installation),
) -> HostCaster:
    return HostCaster(installation, random.Random())


def get_correction_strategy(
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    structured_llm: StructuredLLMProvider = Depends(get_structured_llm),
    correction_storage: CorrectionStorageProvider = Depends(get_correction_storage),
) -> CorrectionStrategy:
    return build_correction_strategy(
        app_settings.correction_mode,
        evaluator=LlmCorrectionEvaluator(structured_llm),
        storage=correction_storage,
    )
