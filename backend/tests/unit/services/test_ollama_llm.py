from unittest.mock import patch

import pytest

from app.services.llm.base import ChatMessage, LLMError
from app.services.llm.ollama import OllamaLLMProvider


def _make_messages() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Say hello."),
    ]


def test_model_name_property() -> None:
    provider = OllamaLLMProvider(model="llama3.1")
    assert provider.model_name == "llama3.1"


def test_chat_returns_content() -> None:
    mock_response = {"message": {"content": "Hello, world!"}}
    with patch("ollama.chat", return_value=mock_response) as mock_chat:
        provider = OllamaLLMProvider(model="llama3.1")
        result = provider.chat(_make_messages())

    assert result == "Hello, world!"
    mock_chat.assert_called_once_with(
        model="llama3.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello."},
        ],
        stream=False,
    )


def test_chat_raises_llm_error_on_exception() -> None:
    with patch("ollama.chat", side_effect=RuntimeError("connection refused")):
        provider = OllamaLLMProvider(model="llama3.1")
        with pytest.raises(LLMError, match="connection refused"):
            provider.chat(_make_messages())


def test_chat_stream_yields_tokens() -> None:
    chunks = [
        {"message": {"content": "Hello"}},
        {"message": {"content": " "}},
        {"message": {"content": "world"}},
    ]
    with patch("ollama.chat", return_value=iter(chunks)):
        provider = OllamaLLMProvider(model="llama3.1")
        tokens = list(provider.chat_stream(_make_messages()))

    assert tokens == ["Hello", " ", "world"]


def test_chat_stream_raises_llm_error_on_exception() -> None:
    with patch("ollama.chat", side_effect=ConnectionError("timeout")):
        provider = OllamaLLMProvider(model="llama3.1")
        with pytest.raises(LLMError, match="timeout"):
            list(provider.chat_stream(_make_messages()))


def test_chat_stream_passes_stream_true() -> None:
    with patch("ollama.chat", return_value=iter([])) as mock_chat:
        provider = OllamaLLMProvider(model="llama3.1")
        list(provider.chat_stream(_make_messages()))

    _, kwargs = mock_chat.call_args
    assert kwargs.get("stream") is True or mock_chat.call_args[1].get("stream") is True
