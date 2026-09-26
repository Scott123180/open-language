"""Contract tests for StructuredLLMProvider (contracts/api.md §3.1)."""

import json

import pytest

from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

_SCHEMA = {
    "type": "object",
    "properties": {"corrections": {"type": "array"}},
    "required": ["corrections"],
}


class StubStructuredLLMProvider(StructuredLLMProvider):
    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        return json.dumps({"corrections": []})


class FailingStructuredLLMProvider(StructuredLLMProvider):
    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        raise LLMError("model unavailable")


def test_chat_json_returns_schema_valid_json() -> None:
    provider = StubStructuredLLMProvider()

    raw = provider.chat_json([ChatMessage(role="user", content="hola")], _SCHEMA)

    parsed = json.loads(raw)
    assert "corrections" in parsed
    assert isinstance(parsed["corrections"], list)


def test_chat_json_surfaces_llm_error() -> None:
    provider = FailingStructuredLLMProvider()

    with pytest.raises(LLMError):
        provider.chat_json([ChatMessage(role="user", content="hola")], _SCHEMA)


def test_structured_provider_is_a_separate_abstraction_from_llm_provider() -> None:
    """ISP: streaming consumers must not be forced to depend on chat_json."""
    from app.services.llm.base import LLMProvider

    assert not issubclass(StructuredLLMProvider, LLMProvider)
    assert not hasattr(LLMProvider, "chat_json")
