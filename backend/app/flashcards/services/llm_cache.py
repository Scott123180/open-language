from __future__ import annotations

from app.flashcards.services.storage import FlashcardStorageProvider
from app.services.llm.base import ChatMessage


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
        cached = self._storage.get_llm_cache(vocabulary_item_id, "fill_blank", language)
        if cached is not None:
            return cached.content

        try:
            sentence = self._generate_sentence(word, language, native_language)
        except Exception:
            return None

        self._storage.set_llm_cache(
            vocabulary_item_id=vocabulary_item_id,
            cache_type="fill_blank",
            language=language,
            content=sentence,
        )
        return sentence

    def get_or_generate(
        self,
        vocabulary_item_id: int,
        cache_type: str,
        word: str,
        language: str,
        native_language: str,
    ) -> str | None:
        cached = self._storage.get_llm_cache(vocabulary_item_id, cache_type, language)
        if cached is not None:
            return cached.content

        try:
            content = self._generate_content(word, cache_type, language, native_language)
        except Exception:
            return None

        self._storage.set_llm_cache(
            vocabulary_item_id=vocabulary_item_id,
            cache_type=cache_type,
            language=language,
            content=content,
        )
        return content

    def _generate_sentence(self, word: str, language: str, native_language: str) -> str:
        """Generate a fill-in-the-blank sentence using the LLM client."""
        if self._llm_client is None:
            raise RuntimeError("No LLM client configured")
        prompt = (
            f"Create one natural sentence in {language} that uses the word '{word}'. "
            f"Replace the word with ___ in the sentence. Return only the sentence."
        )
        return self._llm_client.chat([ChatMessage(role="user", content=prompt)])

    def _generate_content(
        self, word: str, cache_type: str, language: str, native_language: str
    ) -> str:
        """Generate contextual information for a word using the LLM client."""
        if self._llm_client is None:
            raise RuntimeError("No LLM client configured")
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
