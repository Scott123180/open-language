from __future__ import annotations

from datetime import UTC, datetime

from app.flashcards.services.storage import FlashcardStorageProvider


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
    ) -> str | None:
        cached = self._storage.get_llm_cache(vocabulary_item_id, "fill_blank", language)
        if cached is not None:
            return cached.content

        try:
            sentence = self._generate_sentence(word, language)
        except Exception:
            return None

        self._storage.set_llm_cache(
            vocabulary_item_id=vocabulary_item_id,
            cache_type="fill_blank",
            language=language,
            content=sentence,
            generated_at=datetime.now(UTC),
        )
        return sentence

    def get_or_generate(
        self,
        vocabulary_item_id: int,
        cache_type: str,
        word: str,
        language: str,
    ) -> str | None:
        cached = self._storage.get_llm_cache(vocabulary_item_id, cache_type, language)
        if cached is not None:
            return cached.content

        try:
            content = self._generate_content(word, cache_type, language)
        except Exception:
            return None

        self._storage.set_llm_cache(
            vocabulary_item_id=vocabulary_item_id,
            cache_type=cache_type,
            language=language,
            content=content,
            generated_at=datetime.now(UTC),
        )
        return content

    def _generate_sentence(self, word: str, language: str) -> str:
        """Generate a fill-in-the-blank sentence using the LLM client."""
        if self._llm_client is None:
            raise RuntimeError("No LLM client configured")
        prompt = (
            f"Create one natural sentence in {language} that uses the word '{word}'. "
            f"Replace the word with ___ in the sentence. Return only the sentence."
        )
        return self._llm_client.generate(prompt)

    def _generate_content(self, word: str, cache_type: str, language: str) -> str:
        """Generate contextual information for a word using the LLM client."""
        if self._llm_client is None:
            raise RuntimeError("No LLM client configured")
        prompts = {
            "meanings": f"List all meanings and parts of speech for '{word}' in {language}. Be concise.",
            "usage": f"Give 3 example sentences using '{word}' in {language}.",
            "phrases": f"List common idioms and phrases containing '{word}' in {language}.",
            "similar": f"List synonyms, antonyms, and easily confused words for '{word}' in {language}.",
        }
        prompt = prompts.get(cache_type, f"Explain the word '{word}' in {language}.")
        return self._llm_client.generate(prompt)
