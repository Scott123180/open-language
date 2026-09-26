from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.conversation_levels import ConversationLevel, with_learner_text_rules
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


class GrammarRequest(BaseModel):
    message_id: int
    content: str
    preceding_message: str | None = None


class TranslateRequest(BaseModel):
    message_id: int
    content: str
    native_language: str


class PhrasingRequest(BaseModel):
    message_id: int
    content: str
    target_language: str


class WordLookupRequest(BaseModel):
    message_id: int
    selection: str
    target_language: str
    native_language: str
    sentence_context: str | None = None


@router.post("/learning/grammar")
async def grammar_check(
    req: GrammarRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    prompt = build_grammar_prompt(req.content, app_settings.native_language, req.preceding_message)

    computed = False

    def _compute() -> str:
        nonlocal computed
        computed = True
        return llm.chat([ChatMessage(role="user", content=prompt)])

    result_record = storage.get_or_create_learning_result(
        req.message_id, "grammar", req.content, _compute
    )
    return {"result": result_record.result, "cached": not computed}


@router.post("/learning/translate")
async def translate(
    req: TranslateRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
):
    prompt = build_translation_prompt(req.content, req.native_language)

    computed = False

    def _compute() -> str:
        nonlocal computed
        computed = True
        return llm.chat([ChatMessage(role="user", content=prompt)])

    result_record = storage.get_or_create_learning_result(
        req.message_id, "translation", req.content, _compute
    )
    return {"result": result_record.result, "cached": not computed}


@router.post("/learning/phrasing")
async def alternative_phrasing(
    req: PhrasingRequest,
    storage: StorageProvider = Depends(get_storage),
    llm: LLMProvider = Depends(get_llm),
    app_settings: AppSettingsRecord = Depends(get_app_settings),
):
    level = ConversationLevel(app_settings.conversation_level)
    prompt = _phrasing_prompt(req.content, app_settings.target_language, level)
    computed = False

    def _compute() -> str:
        nonlocal computed
        computed = True
        return llm.chat([ChatMessage(role="user", content=prompt)])

    cache_key = _phrasing_cache_key(req.content, level)
    result_record = storage.get_or_create_learning_result(
        req.message_id, "alternative_phrasing", cache_key, _compute
    )
    return {"result": result_record.result, "cached": not computed}


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
    prompt = build_word_lookup_prompt(
        req.selection, req.target_language, req.native_language, req.sentence_context
    )

    computed = False

    def _compute() -> str:
        nonlocal computed
        computed = True
        return llm.chat([ChatMessage(role="user", content=prompt)])

    result_record = storage.get_or_create_learning_result(
        req.message_id, "word_lookup", req.selection, _compute
    )
    return {"result": result_record.result, "cached": not computed}
