"""T054: every `claude` invocation is stripped to a text-only chat model (FR-012–015, R-3)."""

import dataclasses
import json

import pytest

from app.services.llm.claude_code.command import (
    DEFAULT_SYSTEM_PROMPT,
    ClaudeRequest,
    ClaudeSessionRequest,
    OutputMode,
    build_claude_argv,
    build_session_argv,
)

EXECUTABLE = "/opt/claude/bin/claude"
SYSTEM_PROMPT = "Eres Lucía, taquillera."
SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string"}}}


def _one_shot(mode: OutputMode, system_prompt: str = SYSTEM_PROMPT) -> list[str]:
    schema = SCHEMA if mode is OutputMode.SCHEMA else None
    return build_claude_argv(ClaudeRequest(EXECUTABLE, "haiku", "low", system_prompt, mode, schema))


def _session(system_prompt: str = SYSTEM_PROMPT) -> list[str]:
    return build_session_argv(ClaudeSessionRequest(EXECUTABLE, "sonnet", "high", system_prompt))


ALL_ARGV = {
    "stream": lambda **kw: _one_shot(OutputMode.STREAM, **kw),
    "json": lambda **kw: _one_shot(OutputMode.JSON, **kw),
    "schema": lambda **kw: _one_shot(OutputMode.SCHEMA, **kw),
    "session": lambda **kw: _session(**kw),
}


@pytest.fixture(params=sorted(ALL_ARGV))
def argv_for(request):
    return ALL_ARGV[request.param]


def _value_after(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def test_argv_never_contains_bare(argv_for):
    assert "--bare" not in argv_for()


def test_tools_are_always_switched_off(argv_for):
    assert _value_after(argv_for(), "--tools") == ""


@pytest.mark.parametrize(
    "flag", ["--safe-mode", "--disable-slash-commands", "--no-session-persistence"]
)
def test_isolation_flags_are_always_present(argv_for, flag):
    assert flag in argv_for()


def test_system_prompt_is_always_replaced(argv_for):
    assert _value_after(argv_for(), "--system-prompt") == SYSTEM_PROMPT


def test_a_blank_system_prompt_falls_back_to_the_default(argv_for):
    assert _value_after(argv_for(system_prompt="   "), "--system-prompt") == DEFAULT_SYSTEM_PROMPT
    assert DEFAULT_SYSTEM_PROMPT.strip()


def test_starts_with_the_executable_in_print_mode(argv_for):
    assert argv_for()[:2] == [EXECUTABLE, "-p"]


def test_requests_carry_no_prompt_text():
    for request_type in (ClaudeRequest, ClaudeSessionRequest):
        names = {field.name for field in dataclasses.fields(request_type)}
        assert "prompt" not in names


def test_model_and_effort_match_the_request():
    argv = _one_shot(OutputMode.JSON)

    assert _value_after(argv, "--model") == "haiku"
    assert _value_after(argv, "--effort") == "low"


def test_stream_mode_asks_for_partial_stream_json():
    argv = _one_shot(OutputMode.STREAM)

    assert _value_after(argv, "--output-format") == "stream-json"
    assert "--verbose" in argv and "--include-partial-messages" in argv


def test_json_mode_asks_for_one_json_result():
    argv = _one_shot(OutputMode.JSON)

    assert _value_after(argv, "--output-format") == "json"
    assert "--json-schema" not in argv


def test_schema_mode_passes_the_schema_as_compact_json():
    argv = _one_shot(OutputMode.SCHEMA)

    assert _value_after(argv, "--output-format") == "json"
    assert _value_after(argv, "--json-schema") == json.dumps(SCHEMA, separators=(",", ":"))


def test_session_reads_and_writes_stream_json_at_the_learners_effort():
    argv = _session()

    assert _value_after(argv, "--input-format") == "stream-json"
    assert _value_after(argv, "--output-format") == "stream-json"
    assert "--verbose" in argv and "--include-partial-messages" in argv
    assert _value_after(argv, "--model") == "sonnet"
    assert _value_after(argv, "--effort") == "high"
