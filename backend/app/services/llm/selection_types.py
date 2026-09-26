"""Which provider and model serve a request, and the effort levels a provider may take.

A leaf module with no app imports, so both `services/llm/` and `services/conversation/`
can depend on it without depending on each other.
"""

from dataclasses import dataclass

EFFORT_LOW = "low"
EFFORT_MEDIUM = "medium"
EFFORT_HIGH = "high"
EFFORT_LEVELS = (EFFORT_LOW, EFFORT_MEDIUM, EFFORT_HIGH)
DEFAULT_EFFORT = EFFORT_LOW


@dataclass(frozen=True, slots=True)
class LLMSelection:
    """A provider id from the catalogue and a model that provider understands."""

    provider_id: str
    model: str
