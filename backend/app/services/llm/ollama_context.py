"""How much context a request to a local model asks for (011 research R18).

Ollama gives a model a 4,096-token context unless the request asks for more, and a long podcast
episode outgrows it: the oldest turns are cut without a word. A small model therefore asks for a
larger window, which still fits beside it on a consumer GPU. A large model keeps Ollama's
default, because its larger window would cost memory the machine may not have.

Ollama reloads a model whenever a request asks for a different window, so each model's answer is
looked up once and then kept for the life of the process.
"""

import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

_LATEST_TAG = ":latest"
_TAG_SEPARATOR = ":"
_CONTEXT_OPTION = "num_ctx"


class _ModelLister(Protocol):
    def list(self): ...


@dataclass(frozen=True, slots=True)
class ContextPolicy:
    small_model_max_bytes: int
    """A model this size on disk or smaller is small."""
    small_model_context_tokens: int

    def __post_init__(self) -> None:
        if self.small_model_context_tokens <= 0:
            raise ValueError("A small model's context window must be a positive token count.")


class OllamaContextWindow:
    """One per process, shared by the providers the registry builds for each request."""

    def __init__(self, policy: ContextPolicy) -> None:
        self._policy = policy
        self._known: dict[str, Mapping[str, int] | None] = {}
        self._lock = threading.Lock()

    def options_for(self, client: _ModelLister, model: str) -> Mapping[str, int] | None:
        """The request options for `model`; None leaves Ollama's default window."""
        name = _tagged(model)
        with self._lock:
            if name in self._known:
                return self._known[name]
        sizes = _model_sizes(client)
        if sizes is None:
            return None
        options = self._options(sizes.get(name))
        with self._lock:
            self._known[name] = options
        return options

    def _options(self, size: int | None) -> Mapping[str, int] | None:
        if size is None or size > self._policy.small_model_max_bytes:
            return None
        return {_CONTEXT_OPTION: self._policy.small_model_context_tokens}


def _tagged(model: str) -> str:
    return model if _TAG_SEPARATOR in model else model + _LATEST_TAG


def _model_sizes(client: _ModelLister) -> dict[str, int] | None:
    """Each installed model's size on disk, or None when Ollama cannot be asked now."""
    try:
        listing = client.list()
        return {entry["model"]: entry["size"] for entry in listing["models"]}
    except Exception as exc:  # noqa: BLE001 — the request itself reports an unreachable Ollama
        logger.warning("Could not read the installed Ollama models' sizes: %s", exc)
        return None
