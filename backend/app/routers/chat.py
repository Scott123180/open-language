import asyncio
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.conversation_levels import (
    ConversationLevel,
    with_learner_text_rules,
    with_partner_speech_rules,
)
from app.conversation_turns import (
    Corrections,
    EngineTurn,
    LearnerMessageRequest,
    SavedReply,
    plan_learner_turn,
    relay_engine_reply,
    save_learner_message,
    schedule_speech,
    sse,
    start_warming,
)
from app.corrections.services.storage import CorrectionStorageProvider
from app.corrections.services.strategies import CorrectionStrategy
from app.practice_languages import ConversationLanguages
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
    get_speech_for_language,
    get_storage,
)
from app.services.helper_sessions import HelperSessionStore, HelperTurn
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.scenario.base import ScenarioProvider
from app.services.storage.base import (
    AppSettingsRecord,
    ConversationRecord,
    MessageRecord,
    StorageProvider,
)
from app.services.tts.selection import SpeechForLanguage

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
_LIST_MARKER = re.compile(r"^[\d\.\-\s]+")

ChatMessageRequest = LearnerMessageRequest


def _require_conversation(storage: StorageProvider, conversation_id: int) -> ConversationRecord:
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=CONVERSATION_NOT_FOUND)
    return conversation


def _level_of(app_settings: AppSettingsRecord) -> ConversationLevel:
    """The stored level. A corrupt value raises rather than being guessed (data-model §5)."""
    return ConversationLevel(app_settings.conversation_level)


def _languages_of(conversation: ConversationRecord) -> ConversationLanguages:
    """Prompts name the conversation's languages ("German"), never their codes (research R2)."""
    return ConversationLanguages.of(conversation.target_language, conversation.native_language)


def _roleplay_key(conversation_id: int) -> SessionKey:
    return SessionKey(SessionKind.ROLEPLAY, str(conversation_id))


def _standing_roleplay_prompt(
    conversation: ConversationRecord, provider: ScenarioProvider, level: ConversationLevel
) -> str:
    """The system prompt that holds for the whole conversation, with the level's rules last."""
    scenario_description, character_description = _resolve_scenario_context(conversation, provider)
    languages = _languages_of(conversation)
    roleplay_prompt = build_roleplay_system_prompt(
        scenario_title=conversation.scenario_title,
        scenario_description=scenario_description,
        character_description=character_description,
        target_language=languages.target_name,
        native_language=languages.native_name,
    )
    return with_partner_speech_rules(roleplay_prompt, level)


def _saved_turns(messages: list[MessageRecord]) -> tuple[SavedTurn, ...]:
    return tuple(SavedTurn(f"{ROLEPLAY_TURN_PREFIX}{m.id}", m.role, m.content) for m in messages)


@dataclass(frozen=True)
class _RoleplayContext:
    """One roleplay conversation and everything a turn of it needs."""

    conversation: ConversationRecord
    standing_prompt: str
    storage: StorageProvider
    speech: SpeechForLanguage
    engine: ConversationEngine
    provider: SessionCapableProvider

    def turn(
        self, history: tuple[SavedTurn, ...], guidance: str | None, opening: str | None
    ) -> EngineTurn:
        key = _roleplay_key(self.conversation.id)
        request = TurnRequest(key, self.standing_prompt, history, guidance, opening)
        return EngineTurn(self.engine, self.provider, request)

    def persist(self, content: str) -> SavedReply:
        message = self.storage.save_message(
            conversation_id=self.conversation.id, role=ASSISTANT_ROLE, content=content
        )
        self._speak(message)
        return SavedReply(
            f"{ROLEPLAY_TURN_PREFIX}{message.id}", {"done": True, "message_id": message.id}
        )

    def _speak(self, message: MessageRecord) -> None:
        """Read the reply aloud in the conversation's language, or skip it and say why once."""
        language = self.conversation.target_language
        if not self.speech.is_available(language):
            name = _languages_of(self.conversation).target_name
            logger.warning("The %s voice isn't installed; the reply is not read aloud", name)
            return
        provider = self.speech.provider_for(language)
        schedule_speech(
            asyncio.get_running_loop(), self.storage, provider, message.id, message.content
        )


def _roleplay_context(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    speech: SpeechForLanguage = Depends(get_speech_for_language),
    scenarios: ScenarioProvider = Depends(get_scenario_provider),
    engine: ConversationEngine = Depends(get_conversation_engine),
    provider: SessionCapableProvider = Depends(get_session_provider),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
) -> _RoleplayContext:
    conversation = _require_conversation(storage, conversation_id)
    standing_prompt = _standing_roleplay_prompt(conversation, scenarios, _level_of(app_settings))
    return _RoleplayContext(conversation, standing_prompt, storage, speech, engine, provider)


@router.post("/chat/{conversation_id}/open")
async def open_chat(context: _RoleplayContext = Depends(_roleplay_context)):
    history = _saved_turns(context.storage.get_messages(context.conversation.id))
    if any(turn.role == USER_ROLE for turn in history):
        raise HTTPException(status_code=409, detail=CONVERSATION_ALREADY_STARTED)
    instruction = build_open_chat_user_prompt(_languages_of(context.conversation).target_name)
    turn = context.turn(history, guidance=None, opening=instruction)
    return StreamingResponse(relay_engine_reply(turn, context.persist), media_type=SSE_MEDIA_TYPE)


@router.post("/chat/{conversation_id}/session", status_code=202)
async def warm_session(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    scenarios: ScenarioProvider = Depends(get_scenario_provider),
    engine: ConversationEngine = Depends(get_conversation_engine),
    provider: SessionCapableProvider = Depends(get_session_provider),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    """Start building the conversation's session in the background (FR-S07)."""
    conversation = _require_conversation(storage, conversation_id)
    if conversation.status == COMPLETED_STATUS:
        raise HTTPException(status_code=409, detail=CONVERSATION_ENDED)
    key = _roleplay_key(conversation_id)
    if engine.is_live(key):
        return {"status": SESSION_LIVE}
    # The same prompt a turn would build, so the warmed session's fingerprint matches (R8).
    standing_prompt = _standing_roleplay_prompt(conversation, scenarios, _level_of(app_settings))
    history = _saved_turns(storage.get_messages(conversation_id))
    start_warming(engine, provider, key, standing_prompt, history)
    return {"status": SESSION_WARMING}


@router.post("/chat/{conversation_id}/message")
async def send_message(
    req: ChatMessageRequest,
    context: _RoleplayContext = Depends(_roleplay_context),
    strategy: CorrectionStrategy = Depends(get_correction_strategy),
    correction_storage: CorrectionStorageProvider = Depends(get_correction_storage),
):
    corrections = Corrections(strategy, correction_storage)
    return StreamingResponse(_message_events(context, req, corrections), media_type=SSE_MEDIA_TYPE)


async def _message_events(
    context: _RoleplayContext, req: ChatMessageRequest, corrections: Corrections
) -> AsyncIterator[str]:
    conversation = context.conversation
    learner_message = save_learner_message(context.storage, conversation.id, req)
    yield sse({"event": "user_message_saved", "message_id": learner_message.id})
    history = context.storage.get_messages(conversation.id)
    plan = await plan_learner_turn(corrections, conversation, learner_message, history[:-1])
    feedback = corrections.feedback_frame(conversation.id, learner_message.id, plan)
    if feedback:
        yield feedback
    if not plan.generate_reply:
        yield sse({"done": True, "message_id": None})
        return
    # The full saved history, so a Strict-paused message and its retry are both pending.
    turn = context.turn(_saved_turns(history), guidance=plan.reply_prompt_suffix, opening=None)
    async for frame in relay_engine_reply(turn, context.persist):
        yield frame


@router.post("/chat/{conversation_id}/suggestions")
async def get_suggestions(
    conversation_id: int,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    conversation = _require_conversation(storage, conversation_id)
    messages = storage.get_messages(conversation_id)
    prompt = _suggestion_prompt(conversation, messages, app_settings)
    full_response = await asyncio.get_running_loop().run_in_executor(
        None, llm.chat, [ChatMessage(role=USER_ROLE, content=prompt)]
    )
    count = app_settings.suggestion_count
    return {"suggestions": _parse_numbered_suggestions(full_response, count)}


def _suggestion_prompt(
    conversation: ConversationRecord, messages: list[MessageRecord], app_settings: AppSettingsRecord
) -> str:
    """Today's suggestion prompt, with the level's learner-text rules last (FR-017)."""
    history_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
    prompt = build_suggestion_prompt(
        history_text, _languages_of(conversation).target_name, app_settings.suggestion_count
    )
    return with_learner_text_rules(prompt, _level_of(app_settings))


def _parse_numbered_suggestions(text: str, count: int) -> list[str]:
    """Numbered or bulleted lines, markers stripped; the whole text if there are none."""
    lines = (line.strip() for line in text.strip().split("\n"))
    listed = [line for line in lines if line[:1].isdigit() or line.startswith("-")]
    stripped = (_LIST_MARKER.sub("", line).strip() for line in listed)
    suggestions = [suggestion for suggestion in stripped if suggestion]
    return (suggestions or [text.strip()])[:count]


class HelperRequest(BaseModel):
    message: str
    helper_session_id: str
    conversation_id: int


@router.post("/chat/helper")
async def chat_helper(
    req: HelperRequest,
    storage: StorageProvider = Depends(get_storage),
    helper_sessions: HelperSessionStore = Depends(get_helper_sessions),
    engine: ConversationEngine = Depends(get_conversation_engine),
    provider: SessionCapableProvider = Depends(get_session_provider),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    languages = _languages_of(_require_conversation(storage, req.conversation_id))
    stored = helper_sessions.get_history(req.helper_session_id)
    request = _helper_turn_request(req, stored, languages, _level_of(app_settings))
    answer = _HelperAnswer(helper_sessions, req, answer_index=len(stored) + 1)
    turn = EngineTurn(engine, provider, request)
    return StreamingResponse(relay_engine_reply(turn, answer.persist), media_type=SSE_MEDIA_TYPE)


def _helper_turn_request(
    req: HelperRequest,
    stored: list[HelperTurn],
    languages: ConversationLanguages,
    level: ConversationLevel,
) -> TurnRequest:
    """The helper's turn. Only its target-language phrase follows the level (research R6)."""
    helper_prompt = build_helper_system_prompt(languages.target_name, languages.native_name)
    question = SavedTurn(f"{HELPER_TURN_PREFIX}{len(stored)}", USER_ROLE, req.message)
    return TurnRequest(
        key=SessionKey(SessionKind.HELPER, req.helper_session_id),
        standing_prompt=with_learner_text_rules(helper_prompt, level),
        history=(*_helper_turns(stored), question),
        guidance=None,
        opening_instruction=None,
    )


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

    def persist(self, answer: str) -> SavedReply:
        self.helper_sessions.append_exchange(
            session_id=self.req.helper_session_id,
            user_message=self.req.message,
            assistant_message=answer,
        )
        return SavedReply(f"{HELPER_TURN_PREFIX}{self.answer_index}", {"done": True})
