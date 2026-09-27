"""Unit tests for LlmCacheService — T048 / T065.

T048 covers:
  - Returns cached sentence on second call (no LLM call)
  - Generates new sentence via LLM for new word
  - LLM error triggers graceful fallback (returns None); other errors propagate
  - Cache key includes word + language

T065 extends with get_or_generate():
  - Cache hit returns stored content
  - Cache miss triggers LLM call and stores result
  - Language change (different language key) triggers new LLM call
"""

from unittest.mock import MagicMock, patch

import pytest

from app.flashcards.services.llm_cache import LlmCacheService
from app.services.llm.base import LLMError


@pytest.fixture()
def mock_storage():
    return MagicMock()


class TestGetFillBlankSentence:
    def test_returns_cached_sentence_when_cache_hit(self, mock_storage):
        from datetime import UTC, datetime

        from app.flashcards.services.storage import LlmCacheRecord

        cached = LlmCacheRecord(
            id=1,
            vocabulary_item_id=1,
            cache_type="fill_blank",
            content="Je dis ___ à tout le monde.",
            language="de",
            generated_at=datetime.now(UTC),
        )
        mock_storage.get_llm_cache.return_value = cached

        service = LlmCacheService(storage=mock_storage)
        result = service.get_fill_blank_sentence(
            vocabulary_item_id=1, word="bonjour", language="de", native_language="en"
        )

        assert result == "Je dis ___ à tout le monde."
        mock_storage.get_llm_cache.assert_called_once_with(1, "fill_blank", "de")

    def test_calls_llm_when_no_cache(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None
        mock_storage.set_llm_cache.return_value = MagicMock()

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with patch.object(service, "_generate_sentence", return_value="Elle dit ___ chaque matin."):
            result = service.get_fill_blank_sentence(
                vocabulary_item_id=2, word="bonjour", language="de", native_language="en"
            )

        assert result == "Elle dit ___ chaque matin."
        mock_storage.set_llm_cache.assert_called_once()

    def test_returns_none_on_llm_error(self, mock_storage, caplog):
        mock_storage.get_llm_cache.return_value = None

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with patch.object(service, "_generate_sentence", side_effect=LLMError("LLM unavailable")):
            result = service.get_fill_blank_sentence(
                vocabulary_item_id=3, word="merci", language="de", native_language="en"
            )

        assert result is None
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_propagates_a_non_llm_failure(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with (
            patch.object(service, "_generate_sentence", side_effect=RuntimeError("bug")),
            pytest.raises(RuntimeError, match="bug"),
        ):
            service.get_fill_blank_sentence(
                vocabulary_item_id=3, word="merci", language="de", native_language="en"
            )

    def test_returns_none_when_no_llm_client_is_configured(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None

        service = LlmCacheService(storage=mock_storage, llm_client=None)

        assert (
            service.get_fill_blank_sentence(
                vocabulary_item_id=3, word="merci", language="de", native_language="en"
            )
            is None
        )

    def test_does_not_call_llm_on_cache_hit(self, mock_storage):
        from datetime import UTC, datetime

        from app.flashcards.services.storage import LlmCacheRecord

        cached = LlmCacheRecord(
            id=1,
            vocabulary_item_id=4,
            cache_type="fill_blank",
            content="Cached sentence.",
            language="de",
            generated_at=datetime.now(UTC),
        )
        mock_storage.get_llm_cache.return_value = cached

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with patch.object(service, "_generate_sentence") as mock_gen:
            service.get_fill_blank_sentence(
                vocabulary_item_id=4, word="merci", language="de", native_language="en"
            )
            mock_gen.assert_not_called()

    def test_cache_key_uses_word_and_language(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None
        mock_storage.save_llm_cache.return_value = MagicMock()

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with patch.object(service, "_generate_sentence", return_value="Sentence here."):
            service.get_fill_blank_sentence(
                vocabulary_item_id=5, word="au revoir", language="de", native_language="en"
            )

        mock_storage.get_llm_cache.assert_called_with(5, "fill_blank", "de")


class TestGetOrGenerate:
    """T065 — get_or_generate() for word-level contextual info (meanings, usage, phrases, similar)."""

    def test_returns_cached_content_on_hit(self, mock_storage):
        from datetime import UTC, datetime

        from app.flashcards.services.storage import LlmCacheRecord

        cached = LlmCacheRecord(
            id=10,
            vocabulary_item_id=1,
            cache_type="meanings",
            content="hello: greeting word",
            language="de",
            generated_at=datetime.now(UTC),
        )
        mock_storage.get_llm_cache.return_value = cached

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        result = service.get_or_generate(
            vocabulary_item_id=1,
            cache_type="meanings",
            word="bonjour",
            language="de",
            native_language="en",
        )
        assert result == "hello: greeting word"
        mock_storage.set_llm_cache.assert_not_called()

    def test_calls_llm_on_cache_miss(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None
        mock_storage.set_llm_cache.return_value = MagicMock()

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with patch.object(service, "_generate_content", return_value="Some meanings."):
            result = service.get_or_generate(
                vocabulary_item_id=2,
                cache_type="meanings",
                word="bonjour",
                language="de",
                native_language="en",
            )
        assert result == "Some meanings."
        mock_storage.set_llm_cache.assert_called_once()

    def test_different_language_triggers_new_call(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None
        mock_storage.set_llm_cache.return_value = MagicMock()

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with patch.object(service, "_generate_content", return_value="Spanish meanings."):
            service.get_or_generate(
                vocabulary_item_id=1,
                cache_type="meanings",
                word="hola",
                language="es",
                native_language="en",
            )
        mock_storage.get_llm_cache.assert_called_with(1, "meanings", "es")

    def test_propagates_llm_error_and_writes_no_cache(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None

        service = LlmCacheService(storage=mock_storage, llm_client=None)
        with (
            patch.object(service, "_generate_content", side_effect=LLMError("LLM down")),
            pytest.raises(LLMError, match="LLM down"),
        ):
            service.get_or_generate(
                vocabulary_item_id=3,
                cache_type="usage",
                word="merci",
                language="de",
                native_language="en",
            )
        mock_storage.set_llm_cache.assert_not_called()


# --- 006: prompts name the language; the cache slot keeps the code (T080) -------------


class _RecordingLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def chat(self, messages) -> str:
        self.prompts.append(messages[-1].content)
        return "generated"


class TestPromptsNameTheLanguage:
    def _service(self, mock_storage):
        mock_storage.get_llm_cache.return_value = None
        llm = _RecordingLLM()
        return LlmCacheService(storage=mock_storage, llm_client=llm), llm

    def _assert_named(self, prompt: str) -> None:
        import re

        assert "German" in prompt
        assert not re.search(r"\b(de|en)\b", prompt)

    def test_the_fill_blank_prompt_names_german(self, mock_storage):
        service, llm = self._service(mock_storage)

        service.get_fill_blank_sentence(1, "Haus", "de", "en")

        self._assert_named(llm.prompts[-1])

    @pytest.mark.parametrize("cache_type", ["meanings", "usage", "phrases", "similar", "other"])
    def test_each_word_info_prompt_names_german_and_english(self, mock_storage, cache_type):
        service, llm = self._service(mock_storage)

        service.get_or_generate(1, cache_type, "Haus", "de", "en")

        self._assert_named(llm.prompts[-1])
        assert "English" in llm.prompts[-1]

    def test_the_cache_slot_is_still_keyed_by_the_code(self, mock_storage):
        service, _llm = self._service(mock_storage)

        service.get_or_generate(1, "meanings", "Haus", "de", "en")

        assert mock_storage.set_llm_cache.call_args.kwargs["language"] == "de"
