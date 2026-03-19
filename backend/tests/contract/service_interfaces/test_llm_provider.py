from app.services.llm.base import LLMProvider, ChatMessage, LLMError
import pytest


class StubLLMProvider(LLMProvider):
    @property
    def model_name(self) -> str:
        return "stub-model"

    def chat_stream(self, messages):
        yield "hello"
        yield " world"

    def chat(self, messages) -> str:
        return "".join(self.chat_stream(messages))


def test_chat_returns_string():
    p = StubLLMProvider()
    result = p.chat([ChatMessage(role="user", content="hi")])
    assert isinstance(result, str)
    assert len(result) > 0


def test_chat_stream_yields_tokens():
    p = StubLLMProvider()
    tokens = list(p.chat_stream([ChatMessage(role="user", content="hi")]))
    assert len(tokens) >= 1
    assert all(isinstance(t, str) for t in tokens)


def test_chat_equals_stream_concatenation():
    p = StubLLMProvider()
    msg = [ChatMessage(role="user", content="hi")]
    assert p.chat(msg) == "".join(p.chat_stream(msg))


def test_model_name_is_string():
    assert isinstance(StubLLMProvider().model_name, str)
