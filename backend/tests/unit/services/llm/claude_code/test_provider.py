"""T062: ClaudeCodeLLMProvider — one-shot calls through a scripted runner."""

import json

import pytest

from app.config import Settings
from app.corrections.services.evaluator import _parse_findings
from app.services.llm.base import ChatMessage
from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from app.services.llm.claude_code.provider import (
    ONE_SHOT_EFFORT,
    STRUCTURED_EFFORT,
    ClaudeCodeLLMProvider,
)
from tests.support.fake_availability import FakeAvailability, unavailable
from tests.support.scripted_claude_runner import ScriptedClaudeCodeRunner

MESSAGES = [
    ChatMessage("system", "Eres un profesor de gramática."),
    ChatMessage("user", "Corrige: yo es cansado."),
]
SCHEMA = {"type": "object"}


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        _env_file=None,
        claude_executable="/opt/claude",
        claude_request_timeout_seconds=90.0,
        correction_timeout_seconds=6.5,
    )


@pytest.fixture()
def runner() -> ScriptedClaudeCodeRunner:
    return ScriptedClaudeCodeRunner()


@pytest.fixture()
def availability() -> FakeAvailability:
    return FakeAvailability()


@pytest.fixture()
def provider(runner, availability, settings) -> ClaudeCodeLLMProvider:
    return ClaudeCodeLLMProvider(runner, availability, settings, "haiku", "high")


def _flag(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


CALLS = {
    "chat_stream": lambda provider: list(provider.chat_stream(MESSAGES)),
    "chat": lambda provider: provider.chat(MESSAGES),
    "chat_json": lambda provider: provider.chat_json(MESSAGES, SCHEMA),
}


def test_fixed_effort_levels():
    assert (ONE_SHOT_EFFORT, STRUCTURED_EFFORT) == ("low", "medium")


def test_chat_stream_yields_the_deltas_in_stream_mode_at_low_effort(provider, runner):
    assert list(provider.chat_stream(MESSAGES)) == ["¡Hola! ", "¿Adónde ", "viaja?"]

    [call] = runner.prompt_calls
    assert _flag(call.argv, "--output-format") == "stream-json"
    assert _flag(call.argv, "--effort") == "low"


def test_chat_returns_the_result_in_json_mode_at_low_effort(provider, runner):
    assert provider.chat(MESSAGES) == "¡Hola! ¿Adónde viaja?"

    [call] = runner.prompt_calls
    assert _flag(call.argv, "--output-format") == "json"
    assert _flag(call.argv, "--effort") == "low"


def test_chat_json_uses_schema_mode_at_medium_effort(provider, runner):
    provider.chat_json(MESSAGES, SCHEMA)

    [call] = runner.prompt_calls
    assert _flag(call.argv, "--json-schema") == json.dumps(SCHEMA, separators=(",", ":"))
    assert _flag(call.argv, "--effort") == "medium"


def test_chat_json_output_is_accepted_by_the_correction_parser(provider):
    findings = _parse_findings(provider.chat_json(MESSAGES, SCHEMA))

    assert [finding.error_fragment for finding in findings] == ["yo es", "la problema"]


@pytest.mark.parametrize("method", ["chat_stream", "chat"])
def test_conversational_calls_use_the_request_deadline(provider, runner, method):
    CALLS[method](provider)

    assert runner.prompt_calls[0].timeout_seconds == 90.0


def test_structured_calls_use_the_correction_budget(provider, runner):
    provider.chat_json(MESSAGES, SCHEMA)

    assert runner.prompt_calls[0].timeout_seconds == 6.5


@pytest.mark.parametrize("method", sorted(CALLS))
def test_every_call_checks_availability_once_first(provider, availability, method):
    CALLS[method](provider)

    assert availability.checks == 1


@pytest.mark.parametrize("method", sorted(CALLS))
@pytest.mark.parametrize("reason", ["not_on_plan", "not_signed_in", "not_installed"])
def test_an_unavailable_claude_sends_no_prompt(provider, runner, availability, method, reason):
    availability.answer = unavailable(reason)

    with pytest.raises(ClaudeCodeFailure) as raised:
        CALLS[method](provider)

    assert raised.value.kind is FailureKind(reason)
    assert runner.calls == []


def test_the_prompt_goes_to_stdin_and_the_system_prompt_to_its_flag(provider, runner):
    provider.chat(MESSAGES)

    [call] = runner.prompt_calls
    assert call.stdin_text == "Corrige: yo es cansado."
    assert _flag(call.argv, "--system-prompt") == "Eres un profesor de gramática."
    assert "Corrige: yo es cansado." not in call.argv


def test_the_learners_effort_is_not_used_for_one_shot_calls(provider, runner):
    for method in CALLS.values():
        method(provider)

    assert all(_flag(call.argv, "--effort") != "high" for call in runner.prompt_calls)


def test_model_name_is_the_alias(provider, runner):
    provider.chat(MESSAGES)

    assert provider.model_name == "haiku"
    assert _flag(runner.prompt_calls[0].argv, "--model") == "haiku"


@pytest.mark.parametrize(
    ("fixture", "kind"),
    [
        ("auth_failed.ndjson", FailureKind.NOT_SIGNED_IN),
        ("rate_limit_rejected.ndjson", FailureKind.USAGE_LIMIT),
        ("model_404.ndjson", FailureKind.MODEL_UNAVAILABLE),
        ("garbage.ndjson", FailureKind.UNEXPECTED_RESPONSE),
    ],
)
@pytest.mark.parametrize("method", sorted(CALLS))
def test_each_failure_fixture_raises_its_kind(provider, runner, fixture, kind, method):
    runner.fixtures = {mode: fixture for mode in ("stream", "json", "schema")}

    with pytest.raises(ClaudeCodeFailure) as raised:
        CALLS[method](provider)

    assert raised.value.kind is kind
