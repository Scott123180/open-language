from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.conversation_levels import ConversationLevel, with_learner_text_rules
from app.practice_languages import ConversationLanguages
from app.prompts.templates import (
    build_grammar_prompt,
    build_phrasing_prompt,
    build_translation_prompt,
    build_word_lookup_prompt,
)
from app.services.factory import get_app_settings, get_llm, get_storage
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.storage.base import AppSettingsRecord, StorageProvider

router = APIRouter(tags=["learning"])

LEVEL_CACHE_KEY_PREFIX = "[level:"
MESSAGE_NOT_FOUND = "Message not found"


class GrammarRequest(BaseModel):
    message_id: int
    content: str
    preceding_message: str | None = None


class TranslateRequest(BaseModel):
    message_id: int
    content: str


class PhrasingRequest(BaseModel):
    message_id: int
    content: str


class WordLookupRequest(BaseModel):
    message_id: int
    selection: str
    sentence_context: str | None = None


@dataclass(frozen=True)
class CachedToolRequest:
    """One learning-tool call: where its result is cached, and the prompt that computes it."""

    message_id: int
    tool_type: str
    cache_key: str
    prompt: str


def conversation_languages_for_message(
    storage: StorageProvider, message_id: int
) -> ConversationLanguages:
    """A message's languages are its conversation's, never the current setting (FR-009)."""
    message = storage.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
    conversation = storage.get_conversation(message.conversation_id)
    return ConversationLanguages.of(conversation.target_language, conversation.native_language)


def _cached_llm_result(
    storage: StorageProvider, llm: LLMProvider, request: CachedToolRequest
) -> dict:
    computed = False

    def compute() -> str:
        nonlocal computed
        computed = True
        return llm.chat([ChatMessage(role="user", content=request.prompt)])

    record = storage.get_or_create_learning_result(
        request.message_id, request.tool_type, request.cache_key, compute
    )
    return {"result": record.result, "cached": not computed}


@router.post("/learning/grammar")
async def grammar_check(
    req: GrammarRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
):
    languages = conversation_languages_for_message(storage, req.message_id)
    prompt = build_grammar_prompt(req.content, languages.native_name, req.preceding_message)
    request = CachedToolRequest(req.message_id, "grammar", req.content, prompt)
    return _cached_llm_result(storage, llm, request)


@router.post("/learning/translate")
async def translate(
    req: TranslateRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
):
    languages = conversation_languages_for_message(storage, req.message_id)
    prompt = build_translation_prompt(req.content, languages.native_name)
    request = CachedToolRequest(req.message_id, "translation", req.content, prompt)
    return _cached_llm_result(storage, llm, request)


@router.post("/learning/phrasing")
async def alternative_phrasing(
    req: PhrasingRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    languages = conversation_languages_for_message(storage, req.message_id)
    level = ConversationLevel(app_settings.conversation_level)
    prompt = _phrasing_prompt(req.content, languages.target_name, level)
    cache_key = _phrasing_cache_key(req.content, level)
    request = CachedToolRequest(req.message_id, "alternative_phrasing", cache_key, prompt)
    return _cached_llm_result(storage, llm, request)


def _phrasing_prompt(content: str, target_language: str, level: ConversationLevel) -> str:
    """Today's phrasing prompt, with the level's learner-text rules last (FR-017)."""
    return with_learner_text_rules(build_phrasing_prompt(content, target_language), level)


def _phrasing_cache_key(content: str, level: ConversationLevel) -> str:
    """Natural keeps the bare content, so phrasings cached before 005 stay valid (research R7)."""
    if level is ConversationLevel.NATURAL:
        return content
    return f"{LEVEL_CACHE_KEY_PREFIX}{level.value}] {content}"


@router.post("/learning/word-lookup")
async def word_lookup(
    req: WordLookupRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
):
    languages = conversation_languages_for_message(storage, req.message_id)
    prompt = build_word_lookup_prompt(
        req.selection, languages.target_name, languages.native_name, req.sentence_context
    )
    request = CachedToolRequest(req.message_id, "word_lookup", req.selection, prompt)
    return _cached_llm_result(storage, llm, request)
