from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.flashcards.services.sqlite_storage import SQLiteFlashcardStorageProvider
from app.flashcards.services.storage import FlashcardStorageProvider
from app.services.helper_sessions import HelperSessionStore
from app.services.llm.base import LLMProvider
from app.services.scenario.base import ScenarioProvider
from app.services.scenario.static import StaticScenarioProvider
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.storage.sqlite import SQLiteStorageProvider
from app.services.stt.base import STTProvider
from app.services.tts.base import TTSProvider


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


def get_storage(db: Session = Depends(get_db)) -> StorageProvider:
    return SQLiteStorageProvider(db)


def get_flashcard_storage(db: Session = Depends(get_db)) -> FlashcardStorageProvider:
    return SQLiteFlashcardStorageProvider(db)


def get_app_settings(storage: StorageProvider = Depends(get_storage)) -> AppSettingsRecord:
    return storage.get_settings()


def get_llm(app_settings: AppSettingsRecord = Depends(get_app_settings)) -> LLMProvider:
    from app.services.llm.ollama import OllamaLLMProvider

    return OllamaLLMProvider(model=app_settings.llm_model)


def get_tts(app_settings: AppSettingsRecord = Depends(get_app_settings)) -> TTSProvider:
    from app.services.tts.piper import PiperTTSProvider

    settings = get_settings()
    return PiperTTSProvider(voice_name=app_settings.tts_voice, voice_dir=settings.voice_dir)


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
