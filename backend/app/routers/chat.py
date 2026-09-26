import asyncio
import json
import logging
import re
from collections.abc import Generator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.corrections.schemas import rendered_notes, to_note_payload
from app.corrections.services.storage import CorrectionStorageProvider
from app.corrections.services.strategies import (
    NULL_TURN_PLAN,
    CorrectionStrategy,
    TurnContext,
    TurnPlan,
)
from app.prompts.templates import (
    build_helper_system_prompt,
    build_open_chat_user_prompt,
    build_roleplay_system_prompt,
    build_suggestion_prompt,
)
from app.services.factory import (
    get_app_settings,
    get_correction_storage,
    get_correction_strategy,
    get_helper_sessions,
    get_llm,
    get_scenario_provider,
    get_storage,
    get_tts,
)
from app.services.helper_sessions import HelperSessionStore
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.scenario.base import ScenarioProvider
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.tts.base import TTSProvider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _resolve_scenario_context(
    conversation,
    provider: ScenarioProvider,
) -> tuple[str, str]:
    """Return (scenario_description, character_description) for building the system prompt."""
    if conversation.custom_prompt:
        return "a custom scenario defined by the user", conversation.custom_prompt
    all_scenarios = provider.get_all()
    scenario = next((s for s in all_scenarios if s.id == conversation.scenario_id), None)
    if scenario is not None:
        return scenario.description, scenario.ai_context_prompt
    return "an everyday scenario", "a helpful conversation partner"


def _tts_cache_dir(settings: AppSettingsRecord) -> Path:
    # Use home dir based cache path
    return Path.home() / ".open-language" / "tts_cache"


@router.post("/chat/{conversation_id}/open")
async def open_chat(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
    tts: TTSProvider = Depends(get_tts),
    provider: ScenarioProvider = Depends(get_scenario_provider),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    scenario_description, character_description = _resolve_scenario_context(conversation, provider)
    system_prompt = build_roleplay_system_prompt(
        scenario_title=conversation.scenario_title,
        scenario_description=scenario_description,
        character_description=character_description,
        target_language=conversation.target_language,
        native_language=conversation.native_language,
    )

    async def event_stream() -> Generator[str, None, None]:
        tokens: list[str] = []

        # Stream LLM tokens
        loop = asyncio.get_event_loop()
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(
                role="user", content=build_open_chat_user_prompt(conversation.target_language)
            ),
        ]

        def _stream_tokens():
            return list(llm.chat_stream(messages))

        try:
            token_list = await loop.run_in_executor(None, _stream_tokens)
        except LLMError:
            yield f"data: {json.dumps({'error': 'The AI is not responding. Please try again.'})}\n\n"
            return

        for token in token_list:
            tokens.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Save assistant message
        full_content = "".join(tokens)
        msg_record = storage.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_content,
        )

        # Trigger TTS in background
        cache_dir = Path.home() / ".open-language" / "tts_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        audio_path = cache_dir / f"{msg_record.id}.wav"

        def _synthesize():
            tts.synthesize(full_content, audio_path)
            storage.set_tts_path(msg_record.id, str(audio_path))

        loop.run_in_executor(None, _synthesize)

        yield f"data: {json.dumps({'done': True, 'message_id': msg_record.id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _plan_turn_failing_open(
    strategy: CorrectionStrategy, context: TurnContext, timeout: float
) -> TurnPlan:
    """FR-026: every evaluation failure ends the same way — an empty plan."""
    try:
        return await asyncio.wait_for(strategy.plan_turn(context), timeout=timeout)
    except (TimeoutError, LLMError) as exc:
        logger.warning("Correction evaluation failed (%r); continuing uncorrected", exc)
        return NULL_TURN_PLAN


def _persist_feedback(
    correction_storage: CorrectionStorageProvider, message_id: int, plan: TurnPlan
) -> list:
    """Store the turn's notes and return only those a client renders."""
    if not plan.feedback:
        return []
    return rendered_notes(correction_storage.save_feedback(message_id, plan.feedback))


def _feedback_frame(message_id: int, notes: list, awaiting_retry: bool) -> str:
    payload = {
        "event": "feedback",
        "message_id": message_id,
        "awaiting_retry": awaiting_retry,
        "notes": [to_note_payload(note) for note in notes],
    }
    return f"data: {json.dumps(payload)}\n\n"


def _last_character_line(history: list) -> str | None:
    return next((m.content for m in reversed(history) if m.role == "assistant"), None)


def _turn_context(
    conversation,
    conversation_id: int,
    content: str,
    history: list,
    is_low_confidence: bool = False,
) -> TurnContext:
    return TurnContext(
        conversation_id=conversation_id,
        learner_text=content,
        target_language=conversation.target_language,
        native_language=conversation.native_language,
        preceding_character_line=_last_character_line(history),
        is_low_confidence=is_low_confidence,
    )


class ChatMessageRequest(BaseModel):
    content: str
    input_source: str = "keyboard"
    transcription_confidence: float | None = Field(None, ge=0.0, le=1.0)

    @property
    def spoken_confidence(self) -> float | None:
        """The value is client-supplied, so it counts only for spoken input."""
        if self.input_source != "voice":
            return None
        return self.transcription_confidence


def _is_low_confidence(confidence: float | None) -> bool:
    """None means "no information" and is never gated (FR-010a); 0.0 is."""
    if confidence is None:
        return False
    return confidence < get_settings().low_confidence_threshold


@router.post("/chat/{conversation_id}/message")
async def send_message(
    conversation_id: int,
    req: ChatMessageRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
    tts: TTSProvider = Depends(get_tts),
    provider: ScenarioProvider = Depends(get_scenario_provider),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
    strategy: CorrectionStrategy = Depends(get_correction_strategy),
    correction_storage: CorrectionStorageProvider = Depends(get_correction_storage),
):
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    scenario_description, character_description = _resolve_scenario_context(conversation, provider)
    system_prompt = build_roleplay_system_prompt(
        scenario_title=conversation.scenario_title,
        scenario_description=scenario_description,
        character_description=character_description,
        target_language=conversation.target_language,
        native_language=conversation.native_language,
    )

    async def event_stream() -> Generator[str, None, None]:
        confidence = req.spoken_confidence
        is_low_confidence = _is_low_confidence(confidence)
        user_msg = storage.save_message(
            conversation_id=conversation_id,
            role="user",
            content=req.content,
            input_source=req.input_source,
            transcription_confidence=confidence,
            is_low_confidence=is_low_confidence if confidence is not None else None,
        )
        yield f"data: {json.dumps({'event': 'user_message_saved', 'message_id': user_msg.id})}\n\n"

        history = storage.get_messages(conversation_id)
        context = _turn_context(
            conversation, conversation_id, req.content, history[:-1], is_low_confidence
        )
        plan = await _plan_turn_failing_open(
            strategy, context, get_settings().correction_timeout_seconds
        )

        notes = _persist_feedback(correction_storage, user_msg.id, plan)
        if notes:
            awaiting_retry = correction_storage.get_pause_state(conversation_id).awaiting_retry
            yield _feedback_frame(user_msg.id, notes, awaiting_retry)

        if not plan.generate_reply:
            yield f"data: {json.dumps({'done': True, 'message_id': None})}\n\n"
            return

        messages = [
            ChatMessage(role="system", content=system_prompt + (plan.reply_prompt_suffix or ""))
        ]
        messages += [ChatMessage(role=m.role, content=m.content) for m in history]

        async for frame in _stream_reply(conversation_id, messages, storage, llm, tts):
            yield frame

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _stream_reply(
    conversation_id: int,
    messages: list[ChatMessage],
    storage: StorageProvider,
    llm: LLMProvider,
    tts: TTSProvider,
):
    """Stream the character's reply, persist it, and hand it to TTS."""
    loop = asyncio.get_event_loop()

    def _stream_tokens():
        return list(llm.chat_stream(messages))

    try:
        token_list = await loop.run_in_executor(None, _stream_tokens)
    except LLMError:
        yield f"data: {json.dumps({'error': 'The AI is not responding. Please try again.'})}\n\n"
        return

    for token in token_list:
        yield f"data: {json.dumps({'token': token})}\n\n"

    assistant_msg = storage.save_message(
        conversation_id=conversation_id,
        role="assistant",
        content="".join(token_list),
    )
    _schedule_tts(loop, storage, tts, assistant_msg.id, "".join(token_list))
    yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id})}\n\n"


def _schedule_tts(loop, storage: StorageProvider, tts: TTSProvider, message_id: int, text: str):
    cache_dir = Path.home() / ".open-language" / "tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = cache_dir / f"{message_id}.wav"

    def _synthesize():
        tts.synthesize(text, audio_path)
        storage.set_tts_path(message_id, str(audio_path))

    loop.run_in_executor(None, _synthesize)


@router.post("/chat/{conversation_id}/suggestions")
async def get_suggestions(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    conv = storage.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = storage.get_messages(conversation_id)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in messages)

    prompt = build_suggestion_prompt(
        history_text, conv.target_language, app_settings.suggestion_count
    )

    loop = asyncio.get_event_loop()
    full_response = await loop.run_in_executor(
        None, llm.chat, [ChatMessage(role="user", content=prompt)]
    )

    suggestions = []
    for line in full_response.strip().split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            cleaned = re.sub(r"^[\d\.\-\s]+", "", line).strip()
            if cleaned:
                suggestions.append(cleaned)

    if not suggestions:
        suggestions = [full_response.strip()]

    return {"suggestions": suggestions[: app_settings.suggestion_count]}


class HelperRequest(BaseModel):
    message: str
    helper_session_id: str
    target_language: str
    native_language: str


@router.post("/chat/helper")
async def chat_helper(
    req: HelperRequest,
    llm: LLMProvider = Depends(get_llm),
    helper_sessions: HelperSessionStore = Depends(get_helper_sessions),
):
    system_prompt = build_helper_system_prompt(req.target_language, req.native_language)

    messages = [ChatMessage(role="system", content=system_prompt)]
    messages.extend(
        ChatMessage(role=turn.role, content=turn.content)
        for turn in helper_sessions.get_history(req.helper_session_id)
    )
    messages.append(ChatMessage(role="user", content=req.message))

    async def event_stream():
        tokens = []
        loop = asyncio.get_event_loop()

        def _stream():
            return list(llm.chat_stream(messages))

        try:
            token_list = await loop.run_in_executor(None, _stream)
        except LLMError:
            yield f"data: {json.dumps({'error': 'The AI is not responding. Please try again.'})}\n\n"
            return

        for token in token_list:
            tokens.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        full_response = "".join(tokens)
        helper_sessions.append_exchange(
            session_id=req.helper_session_id,
            user_message=req.message,
            assistant_message=full_response,
        )

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
