import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from functools import partial
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
from app.services.conversation import (
    ConversationEngine,
    SavedTurn,
    SessionCapableProvider,
    SessionKey,
    SessionKind,
    TurnRequest,
)
from app.services.factory import (
    get_app_settings,
    get_conversation_engine,
    get_correction_storage,
    get_correction_strategy,
    get_helper_sessions,
    get_llm,
    get_scenario_provider,
    get_session_provider,
    get_storage,
    get_tts,
)
from app.services.helper_sessions import HelperSessionStore, HelperTurn
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.scenario.base import ScenarioProvider
from app.services.storage.base import (
    AppSettingsRecord,
    ConversationRecord,
    MessageRecord,
    StorageProvider,
)
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


SSE_MEDIA_TYPE = "text/event-stream"
CONVERSATION_NOT_FOUND = "Conversation not found"
CONVERSATION_ENDED = "This conversation has ended."
CONVERSATION_ALREADY_STARTED = "This conversation has already started."
COMPLETED_STATUS = "completed"
USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
SESSION_WARMING = "warming"
SESSION_LIVE = "live"
ROLEPLAY_TURN_PREFIX = "m"
HELPER_TURN_PREFIX = "h"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _require_conversation(storage: StorageProvider, conversation_id: int) -> ConversationRecord:
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=CONVERSATION_NOT_FOUND)
    return conversation


def _roleplay_key(conversation_id: int) -> SessionKey:
    return SessionKey(SessionKind.ROLEPLAY, str(conversation_id))


def _standing_roleplay_prompt(conversation: ConversationRecord, provider: ScenarioProvider) -> str:
    """The system prompt that holds for the whole conversation."""
    scenario_description, character_description = _resolve_scenario_context(conversation, provider)
    return build_roleplay_system_prompt(
        scenario_title=conversation.scenario_title,
        scenario_description=scenario_description,
        character_description=character_description,
        target_language=conversation.target_language,
        native_language=conversation.native_language,
    )


def _saved_turns(messages: list[MessageRecord]) -> tuple[SavedTurn, ...]:
    return tuple(SavedTurn(f"{ROLEPLAY_TURN_PREFIX}{m.id}", m.role, m.content) for m in messages)


@dataclass(frozen=True)
class _SavedReply:
    """Where a finished reply was stored, and the frame that tells the client."""

    turn_id: str
    done_frame: dict


@dataclass(frozen=True)
class _EngineTurn:
    engine: ConversationEngine
    provider: SessionCapableProvider
    request: TurnRequest

    def collect(self) -> list[str]:
        # Delivery stays batched (spec Assumptions): the whole reply is collected first.
        return list(self.engine.stream_turn(self.provider, self.request))


async def _relay_engine_reply(
    turn: _EngineTurn, persist: Callable[[str], _SavedReply]
) -> AsyncIterator[str]:
    """Run the turn, relay its tokens, store the reply, and tell the session its saved id."""
    loop = asyncio.get_running_loop()
    try:
        tokens = await loop.run_in_executor(None, turn.collect)
    except LLMError as exc:
        yield _sse({"error": exc.user_message})
        return
    for token in tokens:
        yield _sse({"token": token})
    saved = persist("".join(tokens))
    await loop.run_in_executor(None, turn.engine.acknowledge, turn.request.key, saved.turn_id)
    yield _sse(saved.done_frame)


@dataclass(frozen=True)
class _RoleplayContext:
    """One roleplay conversation and everything a turn of it needs."""

    conversation: ConversationRecord
    standing_prompt: str
    storage: StorageProvider
    tts: TTSProvider
    engine: ConversationEngine
    provider: SessionCapableProvider

    def turn(
        self, history: tuple[SavedTurn, ...], guidance: str | None, opening: str | None
    ) -> _EngineTurn:
        key = _roleplay_key(self.conversation.id)
        request = TurnRequest(key, self.standing_prompt, history, guidance, opening)
        return _EngineTurn(self.engine, self.provider, request)

    def persist(self, content: str) -> _SavedReply:
        message = self.storage.save_message(
            conversation_id=self.conversation.id, role=ASSISTANT_ROLE, content=content
        )
        _schedule_tts(asyncio.get_running_loop(), self.storage, self.tts, message.id, content)
        return _SavedReply(
            f"{ROLEPLAY_TURN_PREFIX}{message.id}", {"done": True, "message_id": message.id}
        )


def _roleplay_context(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    tts: TTSProvider = Depends(get_tts),
    scenarios: ScenarioProvider = Depends(get_scenario_provider),
    engine: ConversationEngine = Depends(get_conversation_engine),
    provider: SessionCapableProvider = Depends(get_session_provider),
) -> _RoleplayContext:
    conversation = _require_conversation(storage, conversation_id)
    standing_prompt = _standing_roleplay_prompt(conversation, scenarios)
    return _RoleplayContext(conversation, standing_prompt, storage, tts, engine, provider)


@router.post("/chat/{conversation_id}/open")
async def open_chat(context: _RoleplayContext = Depends(_roleplay_context)):
    history = _saved_turns(context.storage.get_messages(context.conversation.id))
    if any(turn.role == USER_ROLE for turn in history):
        raise HTTPException(status_code=409, detail=CONVERSATION_ALREADY_STARTED)
    instruction = build_open_chat_user_prompt(context.conversation.target_language)
    turn = context.turn(history, guidance=None, opening=instruction)
    return StreamingResponse(_relay_engine_reply(turn, context.persist), media_type=SSE_MEDIA_TYPE)


@router.post("/chat/{conversation_id}/session", status_code=202)
async def warm_session(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    scenarios: ScenarioProvider = Depends(get_scenario_provider),
    engine: ConversationEngine = Depends(get_conversation_engine),
    provider: SessionCapableProvider = Depends(get_session_provider),
):
    """Start building the conversation's session in the background (FR-S07)."""
    conversation = _require_conversation(storage, conversation_id)
    if conversation.status == COMPLETED_STATUS:
        raise HTTPException(status_code=409, detail=CONVERSATION_ENDED)
    key = _roleplay_key(conversation_id)
    if engine.is_live(key):
        return {"status": SESSION_LIVE}
    history = _saved_turns(storage.get_messages(conversation_id))
    standing_prompt = _standing_roleplay_prompt(conversation, scenarios)
    warm = partial(engine.warm, provider, key, standing_prompt, history)
    asyncio.get_running_loop().run_in_executor(None, _warm_quietly, warm)
    return {"status": SESSION_WARMING}


def _warm_quietly(warm: Callable[[], None]) -> None:
    """A failed warm-up is never shown: the first real turn reports the problem."""
    try:
        warm()
    except LLMError as exc:
        logger.warning("Session warm-up failed; the next turn will try again: %s", exc)


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


@dataclass(frozen=True)
class _Corrections:
    strategy: CorrectionStrategy
    storage: CorrectionStorageProvider

    def feedback_frame(self, conversation_id: int, message_id: int, plan: TurnPlan) -> str | None:
        notes = _persist_feedback(self.storage, message_id, plan)
        if not notes:
            return None
        awaiting_retry = self.storage.get_pause_state(conversation_id).awaiting_retry
        return _feedback_frame(message_id, notes, awaiting_retry)


@router.post("/chat/{conversation_id}/message")
async def send_message(
    req: ChatMessageRequest,
    context: _RoleplayContext = Depends(_roleplay_context),
    strategy: CorrectionStrategy = Depends(get_correction_strategy),
    correction_storage: CorrectionStorageProvider = Depends(get_correction_storage),
):
    corrections = _Corrections(strategy, correction_storage)
    return StreamingResponse(_message_events(context, req, corrections), media_type=SSE_MEDIA_TYPE)


async def _message_events(
    context: _RoleplayContext, req: ChatMessageRequest, corrections: _Corrections
) -> AsyncIterator[str]:
    conversation = context.conversation
    learner_message = _save_learner_message(context.storage, conversation.id, req)
    yield _sse({"event": "user_message_saved", "message_id": learner_message.id})
    history = context.storage.get_messages(conversation.id)
    plan = await _plan_learner_turn(corrections, conversation, learner_message, history[:-1])
    feedback = corrections.feedback_frame(conversation.id, learner_message.id, plan)
    if feedback:
        yield feedback
    if not plan.generate_reply:
        yield _sse({"done": True, "message_id": None})
        return
    # The full saved history, so a Strict-paused message and its retry are both pending.
    turn = context.turn(_saved_turns(history), guidance=plan.reply_prompt_suffix, opening=None)
    async for frame in _relay_engine_reply(turn, context.persist):
        yield frame


def _save_learner_message(
    storage: StorageProvider, conversation_id: int, req: ChatMessageRequest
) -> MessageRecord:
    confidence = req.spoken_confidence
    return storage.save_message(
        conversation_id=conversation_id,
        role=USER_ROLE,
        content=req.content,
        input_source=req.input_source,
        transcription_confidence=confidence,
        is_low_confidence=_is_low_confidence(confidence) if confidence is not None else None,
    )


async def _plan_learner_turn(
    corrections: _Corrections,
    conversation: ConversationRecord,
    learner_message: MessageRecord,
    preceding: list[MessageRecord],
) -> TurnPlan:
    is_low_confidence = bool(learner_message.is_low_confidence)
    context = _turn_context(
        conversation, conversation.id, learner_message.content, preceding, is_low_confidence
    )
    timeout = get_settings().correction_timeout_seconds
    return await _plan_turn_failing_open(corrections.strategy, context, timeout)


def _tts_cache_dir() -> Path:
    return Path.home() / ".open-language" / "tts_cache"


def _schedule_tts(loop, storage: StorageProvider, tts: TTSProvider, message_id: int, text: str):
    cache_dir = _tts_cache_dir()
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
    helper_sessions: HelperSessionStore = Depends(get_helper_sessions),
    engine: ConversationEngine = Depends(get_conversation_engine),
    provider: SessionCapableProvider = Depends(get_session_provider),
):
    stored = helper_sessions.get_history(req.helper_session_id)
    question = SavedTurn(f"{HELPER_TURN_PREFIX}{len(stored)}", USER_ROLE, req.message)
    request = TurnRequest(
        key=SessionKey(SessionKind.HELPER, req.helper_session_id),
        standing_prompt=build_helper_system_prompt(req.target_language, req.native_language),
        history=(*_helper_turns(stored), question),
        guidance=None,
        opening_instruction=None,
    )
    answer = _HelperAnswer(helper_sessions, req, answer_index=len(stored) + 1)
    turn = _EngineTurn(engine, provider, request)
    return StreamingResponse(_relay_engine_reply(turn, answer.persist), media_type=SSE_MEDIA_TYPE)


def _helper_turns(stored: list[HelperTurn]) -> tuple[SavedTurn, ...]:
    """Helper threads aren't in the database, so their turns get positional ids (R-15)."""
    return tuple(
        SavedTurn(f"{HELPER_TURN_PREFIX}{index}", turn.role, turn.content)
        for index, turn in enumerate(stored)
    )


@dataclass(frozen=True)
class _HelperAnswer:
    """Stores the answer to one helper question at its position in the thread."""

    helper_sessions: HelperSessionStore
    req: HelperRequest
    answer_index: int

    def persist(self, answer: str) -> _SavedReply:
        self.helper_sessions.append_exchange(
            session_id=self.req.helper_session_id,
            user_message=self.req.message,
            assistant_message=answer,
        )
        return _SavedReply(f"{HELPER_TURN_PREFIX}{self.answer_index}", {"done": True})
