from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str
    ai_context_prompt: str
    target_language_hint: str | None = None


class ScenarioProvider(ABC):
    @abstractmethod
    def get_random(self, exclude_id: str | None = None) -> Scenario:
        """Return a random scenario, never the one with exclude_id."""
        ...

    @abstractmethod
    def get_all(self) -> list[Scenario]:
        """Return all available scenarios."""
        ...
