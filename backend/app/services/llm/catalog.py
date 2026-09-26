"""The provider catalogue: the one place provider ids, their models, and effort levels are listed.

Adding a provider adds one entry here and one builder in `registry.py`, and nothing else.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.config import get_settings
from app.services.llm.selection_types import (
    DEFAULT_EFFORT,
    EFFORT_HIGH,
    EFFORT_LOW,
    EFFORT_MEDIUM,
)

OLLAMA_PROVIDER_ID = "ollama"
CLAUDE_PROVIDER_ID = "claude"
DEFAULT_PROVIDER_ID = OLLAMA_PROVIDER_ID


@dataclass(frozen=True, slots=True)
class ModelOption:
    model_id: str
    label: str


@dataclass(frozen=True, slots=True)
class EffortOption:
    effort_id: str
    label: str


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    models: tuple[ModelOption, ...]
    default_model: str
    is_local: bool
    effort_levels: tuple[EffortOption, ...]
    default_effort: str | None


_OLLAMA_MODEL_IDS = ("llama3.1:8b", "llama3.2", "mistral")

_CLAUDE_MODELS = (
    ModelOption("sonnet", "Claude Sonnet"),
    ModelOption("haiku", "Claude Haiku (fastest)"),
    ModelOption("opus", "Claude Opus (most capable, uses more of your plan)"),
)

_CLAUDE_EFFORTS = (
    EffortOption(EFFORT_LOW, "Low — fastest replies"),
    EffortOption(EFFORT_MEDIUM, "Medium"),
    EffortOption(EFFORT_HIGH, "High — deeper, slower replies"),
)

CLAUDE_MODEL_IDS = frozenset(model.model_id for model in _CLAUDE_MODELS)

_OLLAMA = ProviderDescriptor(
    provider_id=OLLAMA_PROVIDER_ID,
    display_name="Ollama (local)",
    models=tuple(ModelOption(model_id, model_id) for model_id in _OLLAMA_MODEL_IDS),
    default_model=get_settings().ollama_model,
    is_local=True,
    effort_levels=(),
    default_effort=None,
)

_CLAUDE = ProviderDescriptor(
    provider_id=CLAUDE_PROVIDER_ID,
    display_name="Claude (via Claude Code)",
    models=_CLAUDE_MODELS,
    default_model="sonnet",
    is_local=False,
    effort_levels=_CLAUDE_EFFORTS,
    default_effort=DEFAULT_EFFORT,
)

PROVIDER_CATALOG: Mapping[str, ProviderDescriptor] = MappingProxyType(
    {_OLLAMA.provider_id: _OLLAMA, _CLAUDE.provider_id: _CLAUDE}
)
