"""T008: the provider catalogue is the one place provider ids are listed."""

import dataclasses

import pytest

from app.config import Settings
from app.services.llm.catalog import CLAUDE_MODEL_IDS, PROVIDER_CATALOG


def _models(provider_id: str) -> list[tuple[str, str]]:
    return [(m.model_id, m.label) for m in PROVIDER_CATALOG[provider_id].models]


def _efforts(provider_id: str) -> list[tuple[str, str]]:
    return [(e.effort_id, e.label) for e in PROVIDER_CATALOG[provider_id].effort_levels]


def test_catalogue_lists_ollama_then_claude():
    assert tuple(PROVIDER_CATALOG) == ("ollama", "claude")


class TestOllamaEntry:
    def test_describes_the_local_provider(self):
        ollama = PROVIDER_CATALOG["ollama"]

        assert ollama.display_name == "Ollama (local)"
        assert ollama.is_local is True

    def test_lists_local_models_labelled_by_id(self):
        assert _models("ollama") == [
            ("llama3.1:8b", "llama3.1:8b"),
            ("llama3.2", "llama3.2"),
            ("mistral", "mistral"),
        ]

    def test_default_model_is_the_backend_default(self):
        assert PROVIDER_CATALOG["ollama"].default_model == Settings().ollama_model

    def test_has_no_effort_levels(self):
        assert PROVIDER_CATALOG["ollama"].effort_levels == ()
        assert PROVIDER_CATALOG["ollama"].default_effort is None


class TestClaudeEntry:
    def test_describes_the_cloud_provider(self):
        claude = PROVIDER_CATALOG["claude"]

        assert claude.display_name == "Claude (via Claude Code)"
        assert claude.is_local is False
        assert claude.default_model == "sonnet"

    def test_lists_tier_aliases(self):
        assert _models("claude") == [
            ("sonnet", "Claude Sonnet"),
            ("haiku", "Claude Haiku (fastest)"),
            ("opus", "Claude Opus (most capable, uses more of your plan)"),
        ]

    def test_lists_three_effort_levels_defaulting_to_low(self):
        assert _efforts("claude") == [
            ("low", "Low — fastest replies"),
            ("medium", "Medium"),
            ("high", "High — deeper, slower replies"),
        ]
        assert PROVIDER_CATALOG["claude"].default_effort == "low"


def test_claude_model_ids():
    assert frozenset({"sonnet", "haiku", "opus"}) == CLAUDE_MODEL_IDS


def test_catalogue_cannot_be_modified():
    with pytest.raises(TypeError):
        PROVIDER_CATALOG["gpt"] = PROVIDER_CATALOG["ollama"]  # type: ignore[index]


@pytest.mark.parametrize("provider_id", ["ollama", "claude"])
def test_every_catalogue_value_is_frozen(provider_id):
    descriptor = PROVIDER_CATALOG[provider_id]
    values = [descriptor, *descriptor.models, *descriptor.effort_levels]

    for value in values:
        field = dataclasses.fields(value)[0].name
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, field, "changed")
