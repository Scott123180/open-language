"""Which provider and model a settings save selects, and whether it may (data-model §1).

`PUT /api/settings` is partial: a new provider on its own brings that provider's default model
(FR-024), and a model on its own is checked against the current provider. Pure apart from the
injected availability check, which runs only when the result is Claude.
"""

from collections.abc import Callable

from app.services.llm.availability import ProviderAvailability
from app.services.llm.catalog import (
    CLAUDE_MODEL_IDS,
    CLAUDE_PROVIDER_ID,
    OLLAMA_PROVIDER_ID,
    PROVIDER_CATALOG,
)
from app.services.llm.selection_types import LLMSelection
from app.services.storage.base import AppSettingsRecord

NOT_A_CLAUDE_MODEL = "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus."
EMPTY_LOCAL_MODEL = "Choose a local model."
CLAUDE_MODEL_ON_OLLAMA = (
    "That model belongs to Claude. Choose a local model, or switch the provider to Claude."
)
# Checkers always explain themselves; this only guards against one that doesn't.
CLAUDE_UNAVAILABLE_FALLBACK = "Claude isn't available on this computer right now."


class SelectionRejected(ValueError):  # noqa: N818 — the name is fixed by tasks.md T066
    """The requested provider and model can't be saved. `message` is shown to the learner."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def resolve_llm_selection(
    current: AppSettingsRecord,
    requested_provider: str | None,
    requested_model: str | None,
    claude_availability: Callable[[], ProviderAvailability],
) -> LLMSelection:
    selection = _requested_selection(current, requested_provider, requested_model)
    # Re-saving the stored choice selects nothing new, so a lapsed Claude sign-in doesn't block
    # saving the learner's other settings; requests then report the sign-in problem (FR-029).
    if selection == LLMSelection(current.llm_provider, current.llm_model):
        return selection
    _validate_model(selection)
    if selection.provider_id == CLAUDE_PROVIDER_ID:
        _require_available(claude_availability())
    return selection


def _requested_selection(
    current: AppSettingsRecord, requested_provider: str | None, requested_model: str | None
) -> LLMSelection:
    provider_id = requested_provider or current.llm_provider
    if requested_model is not None:
        return LLMSelection(provider_id, requested_model)
    if provider_id != current.llm_provider:
        return LLMSelection(provider_id, PROVIDER_CATALOG[provider_id].default_model)
    return LLMSelection(provider_id, current.llm_model)


def _validate_model(selection: LLMSelection) -> None:
    if selection.provider_id == CLAUDE_PROVIDER_ID and selection.model not in CLAUDE_MODEL_IDS:
        raise SelectionRejected(NOT_A_CLAUDE_MODEL)
    if selection.provider_id != OLLAMA_PROVIDER_ID:
        return
    if not selection.model.strip():
        raise SelectionRejected(EMPTY_LOCAL_MODEL)
    if selection.model in CLAUDE_MODEL_IDS:
        raise SelectionRejected(CLAUDE_MODEL_ON_OLLAMA)


def _require_available(availability: ProviderAvailability) -> None:
    if not availability.is_available:
        raise SelectionRejected(availability.message or CLAUDE_UNAVAILABLE_FALLBACK)
