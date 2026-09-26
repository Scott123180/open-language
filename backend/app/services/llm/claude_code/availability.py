"""Is Claude Code installed and signed in with a Claude plan? (research R-8)

`claude auth status --json` makes no model call, so checking costs no plan usage. Only
`loggedIn` and `authMethod` are read; email, organisation, and subscription details are
discarded inside `_sign_in_state` and never logged or returned (FR-011).
"""

import json
import logging
from collections.abc import Sequence

from app.services.llm.availability import (
    AvailabilityReason,
    ProviderAvailability,
    ProviderAvailabilityChecker,
)
from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from app.services.llm.claude_code.runner import ClaudeCodeRunner

logger = logging.getLogger(__name__)

AUTH_STATUS_ARGS = ("auth", "status", "--json")
AVAILABILITY_TIMEOUT_SECONDS = 10.0
CLAUDE_PLAN_AUTH_METHOD = "claude.ai"


class ClaudeCodeAvailability(ProviderAvailabilityChecker):
    def __init__(self, runner: ClaudeCodeRunner, executable: str) -> None:
        self._runner = runner
        self._executable = executable

    @property
    def runner(self) -> ClaudeCodeRunner:
        return self._runner

    def check(self) -> ProviderAvailability:
        state = self._sign_in_state()
        if state is None:
            return ProviderAvailability.unavailable(AvailabilityReason.NOT_INSTALLED)
        is_logged_in, auth_method = state
        if not is_logged_in:
            return ProviderAvailability.unavailable(AvailabilityReason.NOT_SIGNED_IN)
        if auth_method != CLAUDE_PLAN_AUTH_METHOD:
            return ProviderAvailability.unavailable(AvailabilityReason.NOT_ON_PLAN)
        return ProviderAvailability.available()

    def _sign_in_state(self) -> tuple[bool, object] | None:
        """(loggedIn, authMethod), or None when Claude Code can't answer at all."""
        argv = [self._executable, *AUTH_STATUS_ARGS]
        try:
            lines = list(self._runner.stream_lines(argv, "", AVAILABILITY_TIMEOUT_SECONDS))
        except ClaudeCodeFailure as exc:
            if exc.kind is not FailureKind.NOT_INSTALLED:
                logger.warning("Claude Code's sign-in status could not be read (%s)", exc.kind)
            return None
        return _read_two_fields(lines)


def _read_two_fields(lines: Sequence[str]) -> tuple[bool, object] | None:
    try:
        status = json.loads("\n".join(lines))
    except json.JSONDecodeError:
        logger.warning("Claude Code's sign-in status was not JSON; treating Claude as unusable")
        return None
    if not isinstance(status, dict):
        return None
    return bool(status.get("loggedIn")), status.get("authMethod")
