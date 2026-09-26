"""The one place a provider id becomes a provider (FR-004, Principle VI).

Feature code asks `services/factory.py` for an `LLMProvider`, a `StructuredLLMProvider`, or a
`SessionCapableProvider`. The factory asks this module, which alone knows the concrete classes.
"""

import os
from collections.abc import Callable, Iterator, Mapping, Sequence
from functools import lru_cache
from typing import Protocol

import ollama

from app.config import Settings
from app.services.conversation.session import (
    ConversationSession,
    SavedTurn,
    SessionFingerprint,
    SessionKey,
)
from app.services.llm.availability import AlwaysAvailable, ProviderAvailabilityChecker
from app.services.llm.base import ChatMessage, LLMError
from app.services.llm.catalog import CLAUDE_PROVIDER_ID, OLLAMA_PROVIDER_ID
from app.services.llm.claude_code import ClaudeCodeAvailability, ClaudeCodeLLMProvider
from app.services.llm.claude_code.runner import SubprocessClaudeCodeRunner
from app.services.llm.ollama import OllamaLLMProvider
from app.services.llm.ollama_residency import OllamaResidency
from app.services.llm.selection_types import DEFAULT_EFFORT, LLMSelection


class ConfiguredLLMProvider(Protocol):
    """Every capability at once: `LLMProvider`, `StructuredLLMProvider`, `SessionCapableProvider`."""

    @property
    def model_name(self) -> str: ...

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]: ...

    def chat(self, messages: list[ChatMessage]) -> str: ...

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str: ...

    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint: ...

    def open_session(
        self, key: SessionKey, standing_prompt: str, history: Sequence[SavedTurn]
    ) -> ConversationSession: ...


class UnknownProviderError(LLMError):
    """The saved provider id matches no catalogue entry (only a hand-edited DB can do this)."""


_ollama_client_factory: Callable[..., ollama.Client] = ollama.Client

_Builder = Callable[[LLMSelection, Settings, str], ConfiguredLLMProvider]


def build_llm_provider(
    selection: LLMSelection, settings: Settings, effort: str = DEFAULT_EFFORT
) -> ConfiguredLLMProvider:
    builder = _BUILDERS.get(selection.provider_id)
    if builder is None:
        raise UnknownProviderError(f"No provider is registered as {selection.provider_id!r}")
    return builder(selection, settings, effort)


def _build_ollama(selection: LLMSelection, settings: Settings, _effort: str) -> OllamaLLMProvider:
    client = _ollama_client_factory(host=settings.ollama_url)
    residency = _ollama_residency(settings.session_idle_ttl_minutes)
    return OllamaLLMProvider(client, selection.model, residency)


@lru_cache
def _ollama_residency(session_keep_alive_minutes: int) -> OllamaResidency:
    """One per process: providers are built per request, but sessions outlive them."""
    return OllamaResidency(session_keep_alive_minutes)


def _build_claude(
    selection: LLMSelection, settings: Settings, effort: str
) -> ClaudeCodeLLMProvider:
    runner = _claude_runner(settings)
    availability = ClaudeCodeAvailability(runner, settings.claude_executable)
    return ClaudeCodeLLMProvider(runner, availability, settings, selection.model, effort)


def _claude_runner(settings: Settings) -> SubprocessClaudeCodeRunner:
    return SubprocessClaudeCodeRunner(
        settings.claude_executable, settings.claude_workdir, os.environ
    )


_BUILDERS: dict[str, _Builder] = {
    OLLAMA_PROVIDER_ID: _build_ollama,
    CLAUDE_PROVIDER_ID: _build_claude,
}


def build_availability_checkers(settings: Settings) -> Mapping[str, ProviderAvailabilityChecker]:
    """Each catalogue provider's checker, keyed by provider id."""
    return {
        OLLAMA_PROVIDER_ID: AlwaysAvailable(),
        CLAUDE_PROVIDER_ID: ClaudeCodeAvailability(
            _claude_runner(settings), settings.claude_executable
        ),
    }
