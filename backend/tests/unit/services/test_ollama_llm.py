"""OllamaLLMProvider over an injected client (T013): no test patches the ollama module."""

import pytest

from app.services.llm.base import ChatMessage, LLMError
from app.services.llm.ollama import OllamaLLMProvider
from app.services.llm.ollama_residency import OllamaResidency

_TTL_MINUTES = 30
_KEEP_ALIVE = f"{_TTL_MINUTES}m"


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


def _provider(
    client: FakeOllamaClient, model: str = "llama3.1", residency: OllamaResidency | None = None
) -> OllamaLLMProvider:
    return OllamaLLMProvider(client, model, residency or OllamaResidency(_TTL_MINUTES))


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
    assert client.calls == [
        {
            "model": "llama3.1",
            "messages": _WIRE_MESSAGES,
            "stream": False,
            "keep_alive": None,
        }
    ]


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

    assert client.calls == [
        {"model": "llama3.1", "messages": _WIRE_MESSAGES, "stream": True, "keep_alive": None}
    ]


def test_chat_json_passes_the_schema_as_the_response_format() -> None:
    schema = {"type": "object", "properties": {"corrections": {"type": "array"}}}
    client = FakeOllamaClient(response={"message": {"content": "{}"}})

    _provider(client).chat_json(_make_messages(), schema)

    assert client.calls == [
        {
            "model": "llama3.1",
            "messages": _WIRE_MESSAGES,
            "stream": False,
            "format": schema,
            "keep_alive": None,
        }
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


_ONE_SHOT_CALLS = {
    "chat": lambda provider: provider.chat(_make_messages()),
    "chat_stream": lambda provider: list(provider.chat_stream(_make_messages())),
    "chat_json": lambda provider: provider.chat_json(_make_messages(), {"type": "object"}),
}


@pytest.mark.parametrize("call", _ONE_SHOT_CALLS)
def test_one_shot_calls_keep_a_held_model_loaded(call) -> None:
    """A learning tool used mid-conversation must not drop the model to Ollama's 5-minute
    unload timer, or the next conversation turn stalls while it reloads (FR-S08)."""
    response = iter([]) if call == "chat_stream" else {"message": {"content": "{}"}}
    client = FakeOllamaClient(response=response)
    residency = OllamaResidency(_TTL_MINUTES)
    residency.hold("llama3.1")

    _ONE_SHOT_CALLS[call](_provider(client, residency=residency))

    assert client.calls[0]["keep_alive"] == _KEEP_ALIVE


@pytest.mark.parametrize("call", _ONE_SHOT_CALLS)
def test_one_shot_calls_without_a_live_session_leave_ollamas_default(call) -> None:
    response = iter([]) if call == "chat_stream" else {"message": {"content": "{}"}}
    client = FakeOllamaClient(response=response)

    _ONE_SHOT_CALLS[call](_provider(client))

    assert client.calls[0]["keep_alive"] is None
