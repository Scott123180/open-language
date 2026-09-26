"""T015: build_llm_provider is the one place a provider id becomes behaviour."""

import pytest

from app.config import Settings
from app.services.conversation import SessionCapableProvider, SessionKey, SessionKind
from app.services.llm import registry
from app.services.llm.base import ChatMessage, LLMError, LLMProvider, StructuredLLMProvider
from app.services.llm.registry import UnknownProviderError, build_llm_provider
from app.services.llm.selection_types import LLMSelection
from tests.support.fake_ollama_client import ScriptedOllamaClient


@pytest.fixture()
def settings() -> Settings:
    return Settings(_env_file=None, ollama_url="http://ollama.test:1234")


@pytest.fixture()
def client_hosts(monkeypatch) -> list[str]:
    hosts: list[str] = []

    def record_client(host: str):
        hosts.append(host)
        return object()

    monkeypatch.setattr(registry, "_ollama_client_factory", record_client)
    return hosts


class TestOllama:
    def test_serves_every_capability(self, settings, client_hosts):
        provider = build_llm_provider(LLMSelection("ollama", "llama3.2"), settings)

        assert isinstance(provider, LLMProvider)
        assert isinstance(provider, StructuredLLMProvider)
        assert isinstance(provider, SessionCapableProvider)

    def test_uses_the_selected_model(self, settings, client_hosts):
        provider = build_llm_provider(LLMSelection("ollama", "llama3.2"), settings)

        assert provider.model_name == "llama3.2"

    def test_client_targets_the_configured_host(self, settings, client_hosts):
        build_llm_provider(LLMSelection("ollama", "llama3.2"), settings)

        assert client_hosts == ["http://ollama.test:1234"]

    def test_a_session_from_one_request_holds_the_model_for_the_next(self, settings, monkeypatch):
        """Providers are built per request, so residency must outlive them (T112)."""
        client = ScriptedOllamaClient()
        monkeypatch.setattr(registry, "_ollama_client_factory", lambda host: client)
        conversation = build_llm_provider(LLMSelection("ollama", "llama3.2"), settings)
        session = conversation.open_session(SessionKey(SessionKind.ROLEPLAY, "t112"), "Eres", [])
        learning_tool = build_llm_provider(LLMSelection("ollama", "llama3.2"), settings)

        learning_tool.chat([ChatMessage(role="user", content="Hola")])
        session.close()
        learning_tool.chat([ChatMessage(role="user", content="Hola")])

        assert [call["keep_alive"] for call in client.chat_calls] == ["30m", None]


def test_unknown_provider_is_rejected(settings):
    with pytest.raises(UnknownProviderError):
        build_llm_provider(LLMSelection("gpt", "gpt-5"), settings)


def test_unknown_provider_error_is_an_llm_error():
    assert issubclass(UnknownProviderError, LLMError)


class TestClaude:
    def test_builds_the_claude_provider_over_a_configured_subprocess_runner(self, tmp_path):
        from app.services.llm.claude_code import ClaudeCodeAvailability, ClaudeCodeLLMProvider
        from app.services.llm.claude_code.runner import SubprocessClaudeCodeRunner

        settings = Settings(
            _env_file=None, claude_executable="/opt/claude", claude_workdir=tmp_path / "cw"
        )

        provider = build_llm_provider(LLMSelection("claude", "haiku"), settings, "medium")

        assert isinstance(provider, ClaudeCodeLLMProvider)
        assert provider.model_name == "haiku"
        runner = provider.runner
        assert isinstance(runner, SubprocessClaudeCodeRunner)
        assert (runner.executable, runner.workdir) == ("/opt/claude", tmp_path / "cw")
        assert isinstance(provider.availability, ClaudeCodeAvailability)
        assert provider.availability.runner is runner
        assert provider.session_fingerprint("x").effort == "medium"

    def test_the_runner_starts_from_the_process_environment(self, monkeypatch):
        monkeypatch.setenv("OPEN_LANGUAGE_TEST_MARKER", "present")

        provider = build_llm_provider(LLMSelection("claude", "sonnet"), Settings(_env_file=None))

        assert provider.runner.environment["OPEN_LANGUAGE_TEST_MARKER"] == "present"
