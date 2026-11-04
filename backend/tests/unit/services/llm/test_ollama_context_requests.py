"""011 R18: every request for a small model asks for the same larger window, sessions included."""

import pytest

from app.services.conversation.session import SavedTurn, SessionKey, SessionKind
from app.services.llm.base import ChatMessage
from app.services.llm.ollama import OllamaLLMProvider
from app.services.llm.ollama_context import ContextPolicy, OllamaContextWindow
from app.services.llm.ollama_residency import OllamaResidency
from tests.support.fake_ollama_client import ScriptedOllamaClient

GIGABYTE = 1_000_000_000
WINDOW = {"num_ctx": 8192}
KEY = SessionKey(SessionKind.PODCAST, "11")
HELLO = [ChatMessage(role="user", content="Hola")]


def _provider(client, model: str = "llama3.1:8b") -> OllamaLLMProvider:
    window = OllamaContextWindow(ContextPolicy(10 * GIGABYTE, 8192))
    return OllamaLLMProvider(client, model, OllamaResidency(30), window)


@pytest.fixture()
def client() -> ScriptedOllamaClient:
    return ScriptedOllamaClient(sizes={"llama3.1:8b": 5 * GIGABYTE, "big:latest": 40 * GIGABYTE})


def test_chat_stream_and_structured_calls_ask_for_the_larger_window(client):
    provider = _provider(client)

    provider.chat(HELLO)
    list(provider.chat_stream(HELLO))
    provider.chat_json(HELLO, {"type": "object"})

    assert [call["options"] for call in client.chat_calls] == [WINDOW] * 3


def test_a_session_warms_replies_and_hands_back_with_the_same_window(client):
    session = _provider(client).open_session(KEY, "Eres Hugo.", [SavedTurn("m1", "user", "Hola")])

    session.warm()
    list(session.reply([], None))
    session.close()

    assert client.chat_calls[0]["options"] == WINDOW
    assert [call["options"] for call in client.generate_calls] == [WINDOW, WINDOW]


def test_a_large_model_sends_no_window_at_all(client):
    provider = _provider(client, "big")

    provider.chat(HELLO)
    provider.open_session(KEY, "Eres Hugo.", []).warm()

    assert "options" not in client.chat_calls[0]
    assert "options" not in client.generate_calls[0]
