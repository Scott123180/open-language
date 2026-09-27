from collections.abc import Mapping
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.conversation_levels import LEVEL_CATALOG, ConversationLevel
from app.practice_languages import (
    DEFAULT_PRACTICE_LANGUAGE,
    PRACTICE_LANGUAGES,
    PracticeLanguage,
    language_name,
    voice_for,
    voice_unavailable_message,
)
from app.services.factory import (
    get_app_settings,
    get_availability_checkers,
    get_storage,
    get_voice_installation,
)
from app.services.llm.availability import ProviderAvailability, ProviderAvailabilityChecker
from app.services.llm.catalog import CLAUDE_PROVIDER_ID, PROVIDER_CATALOG, ProviderDescriptor
from app.services.llm.selection import SelectionRejected, resolve_llm_selection
from app.services.llm.selection_types import EFFORT_LEVELS
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.tts.base import VoiceInstallation
from app.services.tts.voices import AVAILABLE_VOICES, VoiceInfo

router = APIRouter(tags=["settings"])


class VoiceResponse(BaseModel):
    key: str
    display_name: str
    gender: str
    locale: str
    quality: str
    speaking_rate: str
    language: str
    is_installed: bool


class PracticeLanguageResponse(BaseModel):
    """A practice language, the learner's voice for it, and whether that voice can speak."""

    language_id: str
    display_name: str
    is_default: bool
    default_voice: str
    selected_voice: str
    is_voice_installed: bool
    voice_unavailable_message: str | None


WHISPER_MODEL_OPTIONS = frozenset({"base", "small", "medium"})
LLM_PROVIDER_PATTERN = f"^({'|'.join(PROVIDER_CATALOG)})$"
LLM_EFFORT_PATTERN = f"^({'|'.join(EFFORT_LEVELS)})$"
CONVERSATION_LEVEL_PATTERN = f"^({'|'.join(ConversationLevel)})$"
PRACTICE_LANGUAGE_PATTERN = f"^({'|'.join(PRACTICE_LANGUAGES)})$"
_VOICES_BY_KEY: Mapping[str, VoiceInfo] = {voice.key: voice for voice in AVAILABLE_VOICES}


class SettingsResponse(BaseModel):
    llm_provider: str
    llm_model: str
    llm_effort: str
    target_language: str
    native_language: str
    tts_voice: str
    suggestion_count: int
    whisper_model: str
    correction_mode: str
    conversation_level: str
    updated_at: datetime


class UpdateSettingsRequest(BaseModel):
    llm_provider: str | None = Field(None, pattern=LLM_PROVIDER_PATTERN)
    llm_model: str | None = None
    llm_effort: str | None = Field(None, pattern=LLM_EFFORT_PATTERN)
    target_language: str | None = Field(None, pattern=PRACTICE_LANGUAGE_PATTERN)
    native_language: str | None = None
    tts_voice: str | None = None
    suggestion_count: int | None = Field(None, ge=1, le=5)
    whisper_model: str | None = Field(None, pattern="^(base|small|medium)$")
    correction_mode: str | None = Field(None, pattern="^(off|gentle|strict)$")
    conversation_level: str | None = Field(None, pattern=CONVERSATION_LEVEL_PATTERN)


class ModelOptionResponse(BaseModel):
    model_id: str
    label: str


class EffortOptionResponse(BaseModel):
    effort_id: str
    label: str


class ConversationLevelResponse(BaseModel):
    """A level as the learner sees it. Never carries the limits or prompt text."""

    level_id: str
    label: str
    cefr_label: str
    description: str


class LlmProviderResponse(BaseModel):
    """A catalogue entry and its live availability. Never carries account details (FR-011)."""

    provider_id: str
    display_name: str
    is_local: bool
    models: list[ModelOptionResponse]
    default_model: str
    effort_levels: list[EffortOptionResponse]
    default_effort: str | None
    privacy_notice: str | None
    is_available: bool
    unavailable_reason: str | None
    unavailable_message: str | None


def _provider_response(
    descriptor: ProviderDescriptor, availability: ProviderAvailability
) -> LlmProviderResponse:
    return LlmProviderResponse(
        provider_id=descriptor.provider_id,
        display_name=descriptor.display_name,
        is_local=descriptor.is_local,
        models=[ModelOptionResponse(model_id=m.model_id, label=m.label) for m in descriptor.models],
        default_model=descriptor.default_model,
        effort_levels=[
            EffortOptionResponse(effort_id=e.effort_id, label=e.label)
            for e in descriptor.effort_levels
        ],
        default_effort=descriptor.default_effort,
        privacy_notice=descriptor.privacy_notice,
        is_available=availability.is_available,
        unavailable_reason=availability.reason,
        unavailable_message=availability.message,
    )


def _to_response(record: AppSettingsRecord) -> SettingsResponse:
    return SettingsResponse(
        llm_provider=record.llm_provider,
        llm_model=record.llm_model,
        llm_effort=record.llm_effort,
        target_language=record.target_language,
        native_language=record.native_language,
        tts_voice=voice_for(record.target_language, record.voice_choices),
        suggestion_count=record.suggestion_count,
        whisper_model=record.whisper_model,
        correction_mode=record.correction_mode,
        conversation_level=record.conversation_level,
        updated_at=record.updated_at,
    )


def _language_response(
    language: PracticeLanguage,
    app_settings: AppSettingsRecord,
    installation: VoiceInstallation,
) -> PracticeLanguageResponse:
    voice = voice_for(language.code, app_settings.voice_choices)
    is_installed = installation.is_installed(voice)
    return PracticeLanguageResponse(
        language_id=language.code,
        display_name=language.name,
        is_default=language.code == DEFAULT_PRACTICE_LANGUAGE,
        default_voice=language.default_voice,
        selected_voice=voice,
        is_voice_installed=is_installed,
        voice_unavailable_message=(
            None if is_installed else voice_unavailable_message(language.code)
        ),
    )


@router.get("/settings/voices", response_model=list[VoiceResponse])
def get_voices_endpoint(installation: VoiceInstallation = Depends(get_voice_installation)):
    return [
        VoiceResponse(
            key=v.key,
            display_name=v.display_name,
            gender=v.gender,
            locale=v.locale,
            quality=v.quality,
            speaking_rate=v.speaking_rate,
            language=v.language,
            is_installed=installation.is_installed(v.key),
        )
        for v in AVAILABLE_VOICES
    ]


@router.get("/settings/practice-languages", response_model=list[PracticeLanguageResponse])
def get_practice_languages_endpoint(
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    installation: VoiceInstallation = Depends(get_voice_installation),
):
    return [
        _language_response(language, app_settings, installation)
        for language in PRACTICE_LANGUAGES.values()
    ]


@router.get("/settings", response_model=SettingsResponse)
def get_settings_endpoint(storage: StorageProvider = Depends(get_storage)):
    return _to_response(storage.get_settings())


@router.get("/settings/conversation-levels", response_model=list[ConversationLevelResponse])
def get_conversation_levels_endpoint():
    return [
        ConversationLevelResponse(
            level_id=descriptor.level.value,
            label=descriptor.label,
            cefr_label=descriptor.cefr_label,
            description=descriptor.description,
        )
        for descriptor in LEVEL_CATALOG.values()
    ]


@router.get("/settings/llm-providers", response_model=list[LlmProviderResponse])
def get_llm_providers_endpoint(
    checkers: Mapping[str, ProviderAvailabilityChecker] = Depends(get_availability_checkers),
):
    return [
        _provider_response(descriptor, checkers[provider_id].check())
        for provider_id, descriptor in PROVIDER_CATALOG.items()
    ]


@router.put("/settings", response_model=SettingsResponse)
def update_settings_endpoint(
    req: UpdateSettingsRequest,
    storage: StorageProvider = Depends(get_storage),
    checkers: Mapping[str, ProviderAvailabilityChecker] = Depends(get_availability_checkers),
):
    stored = storage.get_settings()
    updates = req.model_dump(exclude_none=True, exclude={"tts_voice"})
    voice_choice = _voice_update(req, stored)
    updates |= _llm_updates(stored, req, checkers)
    # Written only once every part of the request has been validated.
    if voice_choice is not None:
        storage.save_voice_choice(*voice_choice)
    return _to_response(storage.update_settings(**updates))


def _voice_update(req: UpdateSettingsRequest, stored: AppSettingsRecord) -> tuple[str, str] | None:
    """The (language, voice) to remember, for the language in effect after this update."""
    if req.tts_voice is None:
        return None
    language = req.target_language or stored.target_language
    voice = _VOICES_BY_KEY.get(req.tts_voice)
    if voice is None:
        raise HTTPException(status_code=422, detail="Unknown voice.")
    if voice.language != language:
        raise HTTPException(
            status_code=422,
            detail=f"That voice is for {language_name(voice.language)}. "
            f"Choose a {language_name(language)} voice.",
        )
    return language, voice.key


def _llm_updates(
    current: AppSettingsRecord,
    req: UpdateSettingsRequest,
    checkers: Mapping[str, ProviderAvailabilityChecker],
) -> dict[str, str]:
    """Validate the provider/model pair before anything is written (FR-027)."""
    claude_check = checkers[CLAUDE_PROVIDER_ID].check
    try:
        selection = resolve_llm_selection(current, req.llm_provider, req.llm_model, claude_check)
    except SelectionRejected as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    return {"llm_provider": selection.provider_id, "llm_model": selection.model}
