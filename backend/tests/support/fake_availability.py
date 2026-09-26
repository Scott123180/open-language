"""A ProviderAvailabilityChecker that reports a fixed answer and counts its checks."""

from app.services.llm.availability import (
    AVAILABILITY_MESSAGES,
    AvailabilityReason,
    ProviderAvailability,
    ProviderAvailabilityChecker,
)

AVAILABLE = ProviderAvailability(is_available=True, reason=None, message=None)


def unavailable(reason: str) -> ProviderAvailability:
    kind = AvailabilityReason(reason)
    return ProviderAvailability(
        is_available=False, reason=kind, message=AVAILABILITY_MESSAGES[kind]
    )


class FakeAvailability(ProviderAvailabilityChecker):
    def __init__(self, answer: ProviderAvailability = AVAILABLE) -> None:
        self.answer = answer
        self.checks = 0

    def check(self) -> ProviderAvailability:
        self.checks += 1
        return self.answer
