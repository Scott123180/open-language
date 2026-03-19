from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.factory import get_app_settings, get_scenario_provider, get_storage
from app.services.scenario.base import ScenarioProvider
from app.services.storage.base import (
    AppSettingsRecord,
    ConversationRecord,
    MessageRecord,
    StorageProvider,
)

router = APIRouter(tags=["conversations"])


class CreateConversationRequest(BaseModel):
    scenario_id: str


class ConversationResponse(BaseModel):
    id: int
    scenario_id: str
    scenario_title: str
    target_language: str
    native_language: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    llm_model: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    input_source: str | None
    created_at: datetime
    tts_audio_path: str | None


class PatchConversationRequest(BaseModel):
    status: str


def _conv_response(r: ConversationRecord) -> ConversationResponse:
    return ConversationResponse(
        id=r.id,
        scenario_id=r.scenario_id,
        scenario_title=r.scenario_title,
        target_language=r.target_language,
        native_language=r.native_language,
        status=r.status,
        started_at=r.started_at,
        ended_at=r.ended_at,
        llm_model=r.llm_model,
    )


def _msg_response(r: MessageRecord) -> MessageResponse:
    return MessageResponse(
        id=r.id,
        conversation_id=r.conversation_id,
        role=r.role,
        content=r.content,
        input_source=r.input_source,
        created_at=r.created_at,
        tts_audio_path=r.tts_audio_path,
    )


@router.post(
    "/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
def create_conversation(
    req: CreateConversationRequest,
    provider: ScenarioProvider = Depends(get_scenario_provider),
    storage: StorageProvider = Depends(get_storage),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    scenarios = provider.get_all()
    scenario = next((s for s in scenarios if s.id == req.scenario_id), None)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    record = storage.create_conversation(
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        target_language=app_settings.target_language,
        native_language=app_settings.native_language,
        llm_model=app_settings.llm_model,
    )
    return _conv_response(record)


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(storage: StorageProvider = Depends(get_storage)):
    return [_conv_response(r) for r in storage.list_conversations()]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
):
    conv = storage.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conv_response(conv)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
):
    conv = storage.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [_msg_response(m) for m in storage.get_messages(conversation_id)]


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def patch_conversation(
    conversation_id: int,
    req: PatchConversationRequest,
    storage: StorageProvider = Depends(get_storage),
):
    conv = storage.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if req.status == "completed":
        return _conv_response(storage.complete_conversation(conversation_id))
    raise HTTPException(status_code=400, detail=f"Unknown status: {req.status}")
