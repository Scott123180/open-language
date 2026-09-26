"""T056: seven failure kinds, each with an actionable message and a retry hint (R-7)."""

import pytest

from app.services.llm.base import LLMError
from app.services.llm.claude_code.failures import (
    ClaudeCodeFailure,
    FailureKind,
    failure_for_availability,
)

EXPECTED_MESSAGES = {
    "not_installed": "Claude Code isn't installed on this computer. Install it, or switch to the local model in Settings.",
    "not_signed_in": "Claude Code isn't signed in. Run `claude` in a terminal and sign in, or switch to the local model in Settings.",
    "not_on_plan": "Claude Code is signed in with an API key, which would bill a separate account. Sign in with your Claude plan, or switch to the local model in Settings.",
    "usage_limit": "You've reached your Claude plan's usage limit. Switch to the local model in Settings until it resets.",
    "model_unavailable": "That Claude model isn't available on your plan. Choose a different Claude model in Settings.",
    "unreachable": "Claude couldn't be reached. Try again, or switch to the local model in Settings.",
    "unexpected_response": "Claude sent a response the app couldn't read. Try again. If it keeps happening, update Claude Code or switch to the local model.",
}
RETRYABLE = {"unreachable", "unexpected_response"}


def test_there_are_exactly_seven_kinds():
    assert {kind.value for kind in FailureKind} == set(EXPECTED_MESSAGES)


@pytest.mark.parametrize("kind", sorted(EXPECTED_MESSAGES))
def test_each_kind_carries_its_research_message(kind):
    assert ClaudeCodeFailure(FailureKind(kind), "detail").user_message == EXPECTED_MESSAGES[kind]


@pytest.mark.parametrize("kind", sorted(EXPECTED_MESSAGES))
def test_only_session_level_kinds_can_retry(kind):
    assert ClaudeCodeFailure(FailureKind(kind), "detail").can_retry is (kind in RETRYABLE)


def test_a_failure_is_an_llm_error_that_keeps_its_kind_and_detail():
    failure = ClaudeCodeFailure(FailureKind.USAGE_LIMIT, "rate_limit_event rejected")

    assert isinstance(failure, LLMError)
    assert failure.kind is FailureKind.USAGE_LIMIT
    assert "rate_limit_event rejected" in str(failure)


@pytest.mark.parametrize("reason", ["not_installed", "not_signed_in", "not_on_plan"])
def test_availability_reasons_map_to_the_same_kind(reason):
    failure = failure_for_availability(reason)

    assert failure.kind is FailureKind(reason)
    assert failure.can_retry is False
