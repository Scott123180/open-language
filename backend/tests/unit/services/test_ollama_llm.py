"""OllamaLLMProvider over an injected client (T013): no test patches the ollama module."""

import pytest

from app.services.llm.base import ChatMessage, LLMError
from app.services.llm.ollama import OllamaLLMProvider

_TTL_MINUTES = 30


class FakeOllamaClient:
    """Records every chat call and replays a scripted response or failure."""

    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict] = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


def _provider(client: FakeOllamaClient, model: str = "llama3.1") -> OllamaLLMProvider:
    return OllamaLLMProvider(client, model, _TTL_MINUTES)


def _make_messages() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Say hello."),
    ]


_WIRE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Say hello."},
]


def test_model_name_property() -> None:
    assert _provider(FakeOllamaClient()).model_name == "llama3.1"


def test_chat_returns_content() -> None:
    client = FakeOllamaClient(response={"message": {"content": "Hello, world!"}})

    result = _provider(client).chat(_make_messages())

    assert result == "Hello, world!"
    assert client.calls == [{"model": "llama3.1", "messages": _WIRE_MESSAGES, "stream": False}]


def test_chat_raises_llm_error_on_exception() -> None:
    client = FakeOllamaClient(error=RuntimeError("connection refused"))

    with pytest.raises(LLMError, match="connection refused") as raised:
        _provider(client).chat(_make_messages())
    assert raised.value.user_message == LLMError.DEFAULT_USER_MESSAGE


def test_chat_stream_yields_tokens() -> None:
    chunks = [
        {"message": {"content": "Hello"}},
        {"message": {"content": " "}},
        {"message": {"content": "world"}},
    ]
    client = FakeOllamaClient(response=iter(chunks))

    tokens = list(_provider(client).chat_stream(_make_messages()))

    assert tokens == ["Hello", " ", "world"]


def test_chat_stream_raises_llm_error_on_exception() -> None:
    client = FakeOllamaClient(error=ConnectionError("timeout"))

    with pytest.raises(LLMError, match="timeout") as raised:
        list(_provider(client).chat_stream(_make_messages()))
    assert raised.value.user_message == LLMError.DEFAULT_USER_MESSAGE


def test_chat_stream_passes_stream_true() -> None:
    client = FakeOllamaClient(response=iter([]))

    list(_provider(client).chat_stream(_make_messages()))

    assert client.calls == [{"model": "llama3.1", "messages": _WIRE_MESSAGES, "stream": True}]


def test_chat_json_passes_the_schema_as_the_response_format() -> None:
    schema = {"type": "object", "properties": {"corrections": {"type": "array"}}}
    client = FakeOllamaClient(response={"message": {"content": "{}"}})

    _provider(client).chat_json(_make_messages(), schema)

    assert client.calls == [
        {"model": "llama3.1", "messages": _WIRE_MESSAGES, "stream": False, "format": schema}
    ]


def test_chat_json_returns_raw_content() -> None:
    payload = '{"corrections": []}'
    client = FakeOllamaClient(response={"message": {"content": payload}})

    assert _provider(client).chat_json(_make_messages(), {"type": "object"}) == payload


def test_chat_json_raises_llm_error_on_exception() -> None:
    client = FakeOllamaClient(error=RuntimeError("connection refused"))

    with pytest.raises(LLMError, match="connection refused") as raised:
        _provider(client).chat_json(_make_messages(), {"type": "object"})
    assert raised.value.user_message == LLMError.DEFAULT_USER_MESSAGE
