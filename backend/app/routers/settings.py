from collections.abc import Mapping
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.factory import get_availability_checkers, get_storage
from app.services.llm.availability import ProviderAvailability, ProviderAvailabilityChecker
from app.services.llm.catalog import CLAUDE_PROVIDER_ID, PROVIDER_CATALOG, ProviderDescriptor
from app.services.llm.selection import SelectionRejected, resolve_llm_selection
from app.services.llm.selection_types import EFFORT_LEVELS
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.tts.voices import AVAILABLE_VOICES

router = APIRouter(tags=["settings"])


class VoiceResponse(BaseModel):
    key: str
    display_name: str
    gender: str
    locale: str
    quality: str
    speaking_rate: str


WHISPER_MODEL_OPTIONS = frozenset({"base", "small", "medium"})
LLM_PROVIDER_PATTERN = f"^({'|'.join(PROVIDER_CATALOG)})$"
LLM_EFFORT_PATTERN = f"^({'|'.join(EFFORT_LEVELS)})$"


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
    updated_at: datetime


class UpdateSettingsRequest(BaseModel):
    llm_provider: str | None = Field(None, pattern=LLM_PROVIDER_PATTERN)
    llm_model: str | None = None
    llm_effort: str | None = Field(None, pattern=LLM_EFFORT_PATTERN)
    target_language: str | None = None
    native_language: str | None = None
    tts_voice: str | None = None
    suggestion_count: int | None = Field(None, ge=1, le=5)
    whisper_model: str | None = Field(None, pattern="^(base|small|medium)$")
    correction_mode: str | None = Field(None, pattern="^(off|gentle|strict)$")


class ModelOptionResponse(BaseModel):
    model_id: str
    label: str


class EffortOptionResponse(BaseModel):
    effort_id: str
    label: str


class LlmProviderResponse(BaseModel):
    """A catalogue entry and its live availability. Never carries account details (FR-011)."""

    provider_id: str
    display_name: str
    is_local: bool
    models: list[ModelOptionResponse]
    default_model: str
    effort_levels: list[EffortOptionResponse]
    default_effort: str | None
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
        tts_voice=record.tts_voice,
        suggestion_count=record.suggestion_count,
        whisper_model=record.whisper_model,
        correction_mode=record.correction_mode,
        updated_at=record.updated_at,
    )


@router.get("/settings/voices", response_model=list[VoiceResponse])
def get_voices_endpoint():
    return [
        VoiceResponse(
            key=v.key,
            display_name=v.display_name,
            gender=v.gender,
            locale=v.locale,
            quality=v.quality,
            speaking_rate=v.speaking_rate,
        )
        for v in AVAILABLE_VOICES
    ]


@router.get("/settings", response_model=SettingsResponse)
def get_settings_endpoint(storage: StorageProvider = Depends(get_storage)):
    return _to_response(storage.get_settings())


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
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updates |= _llm_updates(storage.get_settings(), req, checkers)
    return _to_response(storage.update_settings(**updates))


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
