import asyncio
import json
import re
from collections.abc import Generator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.prompts.templates import (
    build_helper_system_prompt,
    build_open_chat_user_prompt,
    build_roleplay_system_prompt,
    build_suggestion_prompt,
)
from app.services.factory import (
    get_app_settings,
    get_llm,
    get_scenario_provider,
    get_storage,
    get_tts,
)
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.scenario.base import ScenarioProvider
from app.services.storage.base import AppSettingsRecord, StorageProvider
from app.services.tts.base import TTSProvider

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
            ChatMessage(role="user", content=build_open_chat_user_prompt(conversation.target_language)),
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


class ChatMessageRequest(BaseModel):
    content: str
    input_source: str = "keyboard"


@router.post("/chat/{conversation_id}/message")
async def send_message(
    conversation_id: int,
    req: ChatMessageRequest,
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
        # Persist user message
        user_msg = storage.save_message(
            conversation_id=conversation_id,
            role="user",
            content=req.content,
            input_source=req.input_source,
        )
        yield f"data: {json.dumps({'event': 'user_message_saved', 'message_id': user_msg.id})}\n\n"

        # Build full message history
        history = storage.get_messages(conversation_id)
        messages = [ChatMessage(role="system", content=system_prompt)]
        messages += [ChatMessage(role=m.role, content=m.content) for m in history]

        tokens: list[str] = []

        def _stream_tokens():
            return list(llm.chat_stream(messages))

        loop = asyncio.get_event_loop()
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
        assistant_msg = storage.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_content,
        )

        # Trigger TTS in background
        cache_dir = Path.home() / ".open-language" / "tts_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        audio_path = cache_dir / f"{assistant_msg.id}.wav"

        def _synthesize():
            tts.synthesize(full_content, audio_path)
            storage.set_tts_path(assistant_msg.id, str(audio_path))

        loop.run_in_executor(None, _synthesize)

        yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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


_helper_sessions: dict[str, list[dict]] = {}


class HelperRequest(BaseModel):
    message: str
    helper_session_id: str
    target_language: str
    native_language: str


@router.post("/chat/helper")
async def chat_helper(
    req: HelperRequest,
    llm: LLMProvider = Depends(get_llm),
):
    session_history = _helper_sessions.setdefault(req.helper_session_id, [])

    system_prompt = build_helper_system_prompt(req.target_language, req.native_language)

    messages = [ChatMessage(role="system", content=system_prompt)]
    messages.extend([ChatMessage(role=m["role"], content=m["content"]) for m in session_history])
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
        session_history.append({"role": "user", "content": req.message})
        session_history.append({"role": "assistant", "content": full_response})

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
