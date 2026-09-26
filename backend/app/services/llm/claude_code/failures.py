"""How a Claude Code failure reaches the learner: seven kinds, each naming a next step (R-7)."""

from enum import StrEnum

from app.services.llm.base import LLMError


class FailureKind(StrEnum):
    NOT_INSTALLED = "not_installed"
    NOT_SIGNED_IN = "not_signed_in"
    NOT_ON_PLAN = "not_on_plan"
    USAGE_LIMIT = "usage_limit"
    MODEL_UNAVAILABLE = "model_unavailable"
    UNREACHABLE = "unreachable"
    UNEXPECTED_RESPONSE = "unexpected_response"


USER_MESSAGES: dict[FailureKind, str] = {
    FailureKind.NOT_INSTALLED: (
        "Claude Code isn't installed on this computer. "
        "Install it, or switch to the local model in Settings."
    ),
    FailureKind.NOT_SIGNED_IN: (
        "Claude Code isn't signed in. Run `claude` in a terminal and sign in, "
        "or switch to the local model in Settings."
    ),
    FailureKind.NOT_ON_PLAN: (
        "Claude Code is signed in with an API key, which would bill a separate account. "
        "Sign in with your Claude plan, or switch to the local model in Settings."
    ),
    FailureKind.USAGE_LIMIT: (
        "You've reached your Claude plan's usage limit. "
        "Switch to the local model in Settings until it resets."
    ),
    FailureKind.MODEL_UNAVAILABLE: (
        "That Claude model isn't available on your plan. "
        "Choose a different Claude model in Settings."
    ),
    FailureKind.UNREACHABLE: (
        "Claude couldn't be reached. Try again, or switch to the local model in Settings."
    ),
    FailureKind.UNEXPECTED_RESPONSE: (
        "Claude sent a response the app couldn't read. Try again. "
        "If it keeps happening, update Claude Code or switch to the local model."
    ),
}

# Failures a fresh session cannot fix: retrying would only repeat them (FR-S11).
ACCOUNT_LEVEL_KINDS = frozenset(
    {
        FailureKind.NOT_INSTALLED,
        FailureKind.NOT_SIGNED_IN,
        FailureKind.NOT_ON_PLAN,
        FailureKind.USAGE_LIMIT,
        FailureKind.MODEL_UNAVAILABLE,
    }
)


class ClaudeCodeFailure(LLMError):  # noqa: N818 — the name is fixed by contracts/api.md
    def __init__(self, kind: FailureKind, detail: str) -> None:
        super().__init__(
            detail,
            user_message=USER_MESSAGES[kind],
            can_retry=kind not in ACCOUNT_LEVEL_KINDS,
        )
        self._kind = kind

    @property
    def kind(self) -> FailureKind:
        return self._kind


def failure_for_availability(reason: str) -> ClaudeCodeFailure:
    """The request-time failure for an availability reason code (same names, by design)."""
    kind = FailureKind(reason)
    return ClaudeCodeFailure(kind, f"Pre-flight check refused the request: {reason}")
