"""T066: resolve_llm_selection applies data-model §1's partial-update and validation rules."""

from datetime import UTC, datetime

import pytest

from app.services.llm.availability import ProviderAvailability
from app.services.llm.selection import SelectionRejected, resolve_llm_selection
from app.services.llm.selection_types import LLMSelection
from app.services.storage.base import AppSettingsRecord
from tests.support.fake_availability import AVAILABLE, unavailable

CLAUDE_MISMATCH = "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus."
EMPTY_LOCAL = "Choose a local model."
CLAUDE_ON_OLLAMA = (
    "That model belongs to Claude. Choose a local model, or switch the provider to Claude."
)


def _record(provider: str = "ollama", model: str = "llama3.1:8b") -> AppSettingsRecord:
    return AppSettingsRecord(
        llm_model=model,
        target_language="es",
        native_language="en",
        suggestion_count=1,
        whisper_model="base",
        updated_at=datetime.now(UTC),
        llm_provider=provider,
    )


class CountingAvailability:
    def __init__(self, answer: ProviderAvailability = AVAILABLE) -> None:
        self.answer = answer
        self.calls = 0

    def __call__(self) -> ProviderAvailability:
        self.calls += 1
        return self.answer


@pytest.fixture()
def claude_availability() -> CountingAvailability:
    return CountingAvailability()


def _resolve(current, provider, model, availability):
    return resolve_llm_selection(current, provider, model, availability)


class TestPartialUpdates:
    def test_neither_field_leaves_the_selection_unchanged(self, claude_availability):
        result = _resolve(_record(), None, None, claude_availability)

        assert result == LLMSelection("ollama", "llama3.1:8b")
        assert claude_availability.calls == 0

    def test_a_new_provider_alone_takes_its_default_model(self, claude_availability):
        assert _resolve(_record(), "claude", None, claude_availability) == LLMSelection(
            "claude", "sonnet"
        )

    def test_switching_back_to_ollama_takes_the_local_default(self, claude_availability):
        result = _resolve(_record("claude", "opus"), "ollama", None, claude_availability)

        assert result == LLMSelection("ollama", "llama3.1:8b")

    def test_the_same_provider_alone_changes_nothing(self, claude_availability):
        result = _resolve(_record("claude", "opus"), "claude", None, claude_availability)

        assert result == LLMSelection("claude", "opus")

    def test_a_model_alone_is_checked_against_the_current_provider(self, claude_availability):
        with pytest.raises(SelectionRejected, match=CLAUDE_MISMATCH):
            _resolve(_record("claude", "sonnet"), None, "llama3.2", claude_availability)

    def test_both_are_checked_against_the_given_provider(self, claude_availability):
        result = _resolve(_record(), "claude", "haiku", claude_availability)

        assert result == LLMSelection("claude", "haiku")


class TestRejections:
    def test_claude_with_a_local_model(self, claude_availability):
        with pytest.raises(SelectionRejected) as raised:
            _resolve(_record(), "claude", "llama3.2", claude_availability)

        assert raised.value.message == CLAUDE_MISMATCH

    @pytest.mark.parametrize("model", ["", "   "])
    def test_ollama_with_an_empty_model(self, claude_availability, model):
        with pytest.raises(SelectionRejected) as raised:
            _resolve(_record(), "ollama", model, claude_availability)

        assert raised.value.message == EMPTY_LOCAL

    def test_ollama_with_a_claude_model(self, claude_availability):
        with pytest.raises(SelectionRejected) as raised:
            _resolve(_record(), "ollama", "sonnet", claude_availability)

        assert raised.value.message == CLAUDE_ON_OLLAMA

    def test_claude_while_unavailable_gives_the_availability_message(self):
        availability = CountingAvailability(unavailable("not_signed_in"))

        with pytest.raises(SelectionRejected) as raised:
            _resolve(_record(), "claude", None, availability)

        assert raised.value.message == availability.answer.message


class TestAvailabilityChecks:
    def test_checked_when_the_result_is_claude_and_the_request_names_the_llm(
        self, claude_availability
    ):
        _resolve(_record("claude", "sonnet"), None, "haiku", claude_availability)

        assert claude_availability.calls == 1

    def test_never_checked_for_ollama(self, claude_availability):
        _resolve(_record("claude", "sonnet"), "ollama", "mistral", claude_availability)

        assert claude_availability.calls == 0


def test_an_unlisted_local_model_is_accepted(claude_availability):
    assert _resolve(_record(), None, "llama3.1", claude_availability) == LLMSelection(
        "ollama", "llama3.1"
    )


def test_resaving_an_unchanged_claude_choice_needs_no_availability_check():
    """Sign-in lost: the learner can still save other settings without switching provider."""
    availability = CountingAvailability(unavailable("not_signed_in"))

    result = _resolve(_record("claude", "sonnet"), "claude", "sonnet", availability)

    assert result == LLMSelection("claude", "sonnet")
    assert availability.calls == 0
