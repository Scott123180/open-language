"""T014: the one-shot provider contract (contracts/api.md §2.1), run over every provider.

Adding a provider means adding one entry to `_HARNESSES`. The test bodies never change.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from app.config import Settings
from app.services.llm.base import ChatMessage, LLMError
from app.services.llm.claude_code import ClaudeCodeLLMProvider
from app.services.llm.ollama import OllamaLLMProvider
from tests.support.fake_availability import FakeAvailability
from tests.support.fake_ollama_client import ScriptedOllamaClient
from tests.support.scripted_claude_runner import ScriptedClaudeCodeRunner

_MESSAGES = [
    ChatMessage(role="system", content="Eres Lucía, taquillera en una estación."),
    ChatMessage(role="user", content="Hola, quiero un billete."),
]
_SCHEMA = {"type": "object"}
_MODEL = {"ollama": "llama3.2", "claude": "sonnet"}
_TTL_MINUTES = 30


@dataclass(frozen=True)
class ProviderHarness:
    """Builds a provider over a scripted backend that succeeds or fails."""

    model: str
    working: Callable[[], object]
    failing: Callable[[], object]


def _ollama_harness() -> ProviderHarness:
    model = _MODEL["ollama"]

    def build(client: ScriptedOllamaClient):
        return OllamaLLMProvider(client, model, _TTL_MINUTES)

    return ProviderHarness(
        model=model,
        working=lambda: build(ScriptedOllamaClient()),
        failing=lambda: build(ScriptedOllamaClient(error=ConnectionError("refused"))),
    )


def _claude_harness() -> ProviderHarness:
    model = _MODEL["claude"]
    garbage = {mode: "garbage.ndjson" for mode in ("stream", "json", "schema")}

    def build(runner: ScriptedClaudeCodeRunner):
        settings = Settings(_env_file=None)
        return ClaudeCodeLLMProvider(runner, FakeAvailability(), settings, model, "low")

    return ProviderHarness(
        model=model,
        working=lambda: build(ScriptedClaudeCodeRunner()),
        failing=lambda: build(ScriptedClaudeCodeRunner(fixtures=garbage)),
    )


_HARNESSES: dict[str, Callable[[], ProviderHarness]] = {
    "ollama": _ollama_harness,
    "claude": _claude_harness,
}


@pytest.fixture(params=sorted(_HARNESSES))
def provider_factory(request) -> ProviderHarness:
    return _HARNESSES[request.param]()


def test_chat_equals_the_joined_stream(provider_factory):
    streamed = "".join(provider_factory.working().chat_stream(_MESSAGES))

    assert provider_factory.working().chat(_MESSAGES) == streamed


def test_chat_stream_yields_only_non_empty_strings(provider_factory):
    tokens = list(provider_factory.working().chat_stream(_MESSAGES))

    assert tokens
    assert all(isinstance(token, str) and token for token in tokens)


def test_chat_json_returns_parseable_json(provider_factory):
    raw = provider_factory.working().chat_json(_MESSAGES, _SCHEMA)

    json.loads(raw)


@pytest.mark.parametrize(
    "call",
    [
        lambda provider: list(provider.chat_stream(_MESSAGES)),
        lambda provider: provider.chat(_MESSAGES),
        lambda provider: provider.chat_json(_MESSAGES, _SCHEMA),
    ],
    ids=["chat_stream", "chat", "chat_json"],
)
def test_backend_failure_raises_llm_error_with_a_user_message(provider_factory, call):
    with pytest.raises(LLMError) as raised:
        call(provider_factory.failing())

    assert raised.value.user_message.strip()


def test_model_name_is_the_model_it_was_built_with(provider_factory):
    assert provider_factory.working().model_name == provider_factory.model
