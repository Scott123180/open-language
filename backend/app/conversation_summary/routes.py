"""GET /api/conversations/{id}/summary, for roleplay conversations and podcast episodes (§9)."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.conversation_levels import ConversationLevel
from app.conversation_summary.services.speaker_names import SpeakerNames
from app.conversation_summary.services.storage import SummaryStorage
from app.conversation_summary.services.summariser import (
    Summariser,
    SummaryLine,
    SummaryRequest,
    SummaryResult,
)
from app.practice_languages import ConversationLanguages, language_name
from app.services.factory import (
    get_app_settings,
    get_speaker_names,
    get_storage,
    get_structured_llm,
    get_summary_storage,
)
from app.services.llm.base import StructuredLLMProvider
from app.services.storage.base import AppSettingsRecord, ConversationRecord, StorageProvider

router = APIRouter(tags=["conversation-summary"])

CONVERSATION_NOT_FOUND = "Conversation not found"
TOO_EARLY = "There's nothing to summarise yet. Come back after the next line."
READY, TOO_EARLY_STATUS = "ready", "too_early"


@router.get("/api/conversations/{conversation_id}/summary")
async def get_summary(
    conversation_id: int,
    conversations: StorageProvider = Depends(get_storage),
    summaries: SummaryStorage = Depends(get_summary_storage),
    speaker_names: SpeakerNames = Depends(get_speaker_names),
    structured_llm: StructuredLLMProvider = Depends(get_structured_llm),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    """The conversation's own language, never the current setting (spec edge case)."""
    conversation = conversations.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=CONVERSATION_NOT_FOUND)
    request = _request(
        conversation, conversations, ConversationLevel(app_settings.conversation_level)
    )
    summariser = Summariser(structured_llm, summaries, speaker_names)
    result = await asyncio.get_running_loop().run_in_executor(None, summariser.summarise, request)
    return _response(conversation, result)


def _request(
    conversation: ConversationRecord, conversations: StorageProvider, level: ConversationLevel
) -> SummaryRequest:
    lines = tuple(
        SummaryLine(message.id, message.role, message.content)
        for message in conversations.get_messages(conversation.id)
    )
    languages = ConversationLanguages.of(conversation.target_language, conversation.native_language)
    return SummaryRequest(conversation.id, lines, languages, level)


def _response(conversation: ConversationRecord, result: SummaryResult) -> dict:
    if result.is_too_early:
        return {"status": TOO_EARLY_STATUS, "message": TOO_EARLY}
    return {
        "status": READY,
        "conversation_id": conversation.id,
        "up_to_message_id": result.up_to_message_id,
        "conversation_language": conversation.target_language,
        "conversation_language_name": language_name(conversation.target_language),
        "native_language_name": language_name(conversation.native_language),
        "points": [
            {"conversation_language": point.conversation_language, "english": point.english}
            for point in result.points
        ],
    }
