from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.factory import get_storage
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


class SettingsResponse(BaseModel):
    llm_model: str
    target_language: str
    native_language: str
    tts_voice: str
    suggestion_count: int
    whisper_model: str
    updated_at: datetime


class UpdateSettingsRequest(BaseModel):
    llm_model: str | None = None
    target_language: str | None = None
    native_language: str | None = None
    tts_voice: str | None = None
    suggestion_count: int | None = Field(None, ge=1, le=5)
    whisper_model: str | None = Field(None, pattern="^(base|small|medium)$")


def _to_response(record: AppSettingsRecord) -> SettingsResponse:
    return SettingsResponse(
        llm_model=record.llm_model,
        target_language=record.target_language,
        native_language=record.native_language,
        tts_voice=record.tts_voice,
        suggestion_count=record.suggestion_count,
        whisper_model=record.whisper_model,
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


@router.put("/settings", response_model=SettingsResponse)
def update_settings_endpoint(
    req: UpdateSettingsRequest,
    storage: StorageProvider = Depends(get_storage),
):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    return _to_response(storage.update_settings(**updates))
