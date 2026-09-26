"""Whether a provider can serve requests right now, and if not, what the learner should do."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class AvailabilityReason(StrEnum):
    NOT_INSTALLED = "not_installed"
    NOT_SIGNED_IN = "not_signed_in"
    NOT_ON_PLAN = "not_on_plan"


AVAILABILITY_MESSAGES: dict[AvailabilityReason, str] = {
    AvailabilityReason.NOT_INSTALLED: "Install Claude Code to use Claude.",
    AvailabilityReason.NOT_SIGNED_IN: (
        "Sign in to Claude Code (run `claude` in a terminal) to use Claude."
    ),
    AvailabilityReason.NOT_ON_PLAN: (
        "Claude Code is signed in with an API key. Sign in with your Claude plan to use it here."
    ),
}


@dataclass(frozen=True, slots=True)
class ProviderAvailability:
    is_available: bool
    reason: AvailabilityReason | None
    message: str | None

    @classmethod
    def available(cls) -> "ProviderAvailability":
        return cls(is_available=True, reason=None, message=None)

    @classmethod
    def unavailable(cls, reason: AvailabilityReason) -> "ProviderAvailability":
        return cls(is_available=False, reason=reason, message=AVAILABILITY_MESSAGES[reason])


class ProviderAvailabilityChecker(ABC):
    @abstractmethod
    def check(self) -> ProviderAvailability: ...


class AlwaysAvailable(ProviderAvailabilityChecker):
    """For a provider whose problems surface at request time (Ollama)."""

    def check(self) -> ProviderAvailability:
        return ProviderAvailability.available()
