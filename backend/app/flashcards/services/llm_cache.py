from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.flashcards.services.storage import FlashcardStorageProvider
from app.practice_languages import language_name
from app.services.llm.base import ChatMessage, LLMError

logger = logging.getLogger(__name__)

_NO_LLM_CLIENT_DETAIL = "No language model is configured for this cache"
FILL_BLANK_CACHE_TYPE = "fill_blank"


@dataclass(frozen=True, slots=True)
class _CacheSlot:
    """Where one piece of generated content is cached."""

    vocabulary_item_id: int
    cache_type: str
    language: str


class LlmCacheService:
    """Get-or-create LLM-generated content per vocabulary word."""

    def __init__(self, storage: FlashcardStorageProvider, llm_client=None) -> None:
        self._storage = storage
        self._llm_client = llm_client

    def get_fill_blank_sentence(
        self,
        vocabulary_item_id: int,
        word: str,
        language: str,
        native_language: str,
    ) -> str | None:
        slot = _CacheSlot(vocabulary_item_id, FILL_BLANK_CACHE_TYPE, language)
        try:
            return self._cached_or_generated(
                slot, lambda: self._generate_sentence(word, language, native_language)
            )
        except LLMError as exc:
            # A card without a sentence is still practisable, so a deck build never fails here.
            logger.warning("Fill-in-the-blank sentence unavailable for %r: %s", word, exc)
            return None

    def get_or_generate(
        self,
        vocabulary_item_id: int,
        cache_type: str,
        word: str,
        language: str,
        native_language: str,
    ) -> str:
        """Raises LLMError when nothing is cached and the model cannot answer."""
        slot = _CacheSlot(vocabulary_item_id, cache_type, language)
        return self._cached_or_generated(
            slot, lambda: self._generate_content(word, cache_type, language, native_language)
        )

    def _cached_or_generated(self, slot: _CacheSlot, generate: Callable[[], str]) -> str:
        """The slot's cached content, or `generate()`'s result, stored before returning."""
        cached = self._storage.get_llm_cache(
            slot.vocabulary_item_id, slot.cache_type, slot.language
        )
        if cached is not None:
            return cached.content
        content = generate()
        self._storage.set_llm_cache(
            vocabulary_item_id=slot.vocabulary_item_id,
            cache_type=slot.cache_type,
            language=slot.language,
            content=content,
        )
        return content

    def _generate_sentence(self, word: str, language: str, native_language: str) -> str:
        """Generate a fill-in-the-blank sentence using the LLM client."""
        if self._llm_client is None:
            raise LLMError(_NO_LLM_CLIENT_DETAIL)
        prompt = (
            f"Create one natural sentence in {language_name(language)} that uses the word '{word}'. "
            f"Replace the word with ___ in the sentence. Return only the sentence."
        )
        return self._llm_client.chat([ChatMessage(role="user", content=prompt)])

    def _generate_content(
        self, word: str, cache_type: str, language: str, native_language: str
    ) -> str:
        """Generate contextual information for a word using the LLM client."""
        if self._llm_client is None:
            raise LLMError(_NO_LLM_CLIENT_DETAIL)
        # Prompts name languages ("German"); the cache slot keeps the code (research R2).
        language, native_language = language_name(language), language_name(native_language)
        prompts = {
            "meanings": f"List all meanings and parts of speech for the {language} word '{word}'. Be concise. Respond in {native_language}.",
            "usage": f"Give 3 example sentences using the {language} word '{word}'. Respond in {native_language}.",
            "phrases": f"List common idioms and phrases containing the {language} word '{word}'. Respond in {native_language}.",
            "similar": f"List synonyms, antonyms, and easily confused words for the {language} word '{word}'. Respond in {native_language}.",
        }
        prompt = prompts.get(
            cache_type,
            f"Explain the {language} word '{word}'. Respond in {native_language}.",
        )
        return self._llm_client.chat([ChatMessage(role="user", content=prompt)])
