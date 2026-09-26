"""T065: ClaudeCodeAvailability reads only `loggedIn` and `authMethod` (R-8, FR-011)."""

import logging

import pytest

from app.services.llm.availability import AVAILABILITY_MESSAGES, AvailabilityReason
from app.services.llm.claude_code import ClaudeCodeAvailability
from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from tests.support.scripted_claude_runner import ScriptedClaudeCodeRunner

DECOYS = ("decoy-learner@example.com", "Decoy Org Ltd")


def _check(fixture: str | None = None, error: Exception | None = None):
    runner = ScriptedClaudeCodeRunner(error=error)
    if fixture is not None:
        runner.fixtures["auth"] = fixture
    return ClaudeCodeAvailability(runner, "/opt/claude").check(), runner


def test_runs_auth_status_as_json_with_no_prompt():
    _, runner = _check()

    [call] = runner.calls
    assert call.argv == ["/opt/claude", "auth", "status", "--json"]
    assert call.stdin_text == ""


def test_signed_in_on_a_plan_is_available():
    result, _ = _check("auth_status_signed_in.json")

    assert (result.is_available, result.reason, result.message) == (True, None, None)


@pytest.mark.parametrize(
    ("fixture", "error", "reason"),
    [
        ("auth_status_signed_out.json", None, AvailabilityReason.NOT_SIGNED_IN),
        ("auth_status_api_key.json", None, AvailabilityReason.NOT_ON_PLAN),
        (None, ClaudeCodeFailure(FailureKind.NOT_INSTALLED, "missing"), "not_installed"),
    ],
)
def test_each_unavailable_state_names_its_reason(fixture, error, reason):
    result, _ = _check(fixture, error)

    assert result.is_available is False
    assert result.reason == reason
    assert result.message == AVAILABILITY_MESSAGES[AvailabilityReason(reason)]


def test_availability_messages_are_the_data_model_texts():
    assert AVAILABILITY_MESSAGES == {
        AvailabilityReason.NOT_INSTALLED: "Install Claude Code to use Claude.",
        AvailabilityReason.NOT_SIGNED_IN: (
            "Sign in to Claude Code (run `claude` in a terminal) to use Claude."
        ),
        AvailabilityReason.NOT_ON_PLAN: (
            "Claude Code is signed in with an API key. "
            "Sign in with your Claude plan to use it here."
        ),
    }


def test_unreadable_status_output_is_not_available():
    result, _ = _check("garbage.ndjson")

    assert result.is_available is False


@pytest.mark.parametrize("fixture", ["auth_status_signed_in.json", "auth_status_api_key.json"])
def test_account_details_never_leave_the_check(fixture, caplog):
    with caplog.at_level(logging.DEBUG):
        result, _ = _check(fixture)

    exposed = repr(result) + caplog.text
    assert not any(decoy in exposed for decoy in DECOYS)
