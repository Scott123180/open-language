"""The exact `claude` argv, built by pure functions so the isolation flags are asserted directly.

Every invocation, one-shot or session, runs as a text-only chat model: no tools, no personal or
project configuration, no slash commands, no saved session, and a replaced system prompt (R-3).
The prompt itself never appears here: it goes to stdin, off the process list.
"""

import json
from dataclasses import dataclass
from enum import StrEnum

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant inside a language-learning app. Reply with text only."
)

PRINT_FLAG = "-p"
SAFE_MODE_FLAG = "--safe-mode"
TOOLS_FLAG = "--tools"
NO_TOOLS = ""
DISABLE_SLASH_COMMANDS_FLAG = "--disable-slash-commands"
NO_SESSION_PERSISTENCE_FLAG = "--no-session-persistence"
MODEL_FLAG = "--model"
EFFORT_FLAG = "--effort"
SYSTEM_PROMPT_FLAG = "--system-prompt"
OUTPUT_FORMAT_FLAG = "--output-format"
INPUT_FORMAT_FLAG = "--input-format"
JSON_SCHEMA_FLAG = "--json-schema"
VERBOSE_FLAG = "--verbose"
PARTIAL_MESSAGES_FLAG = "--include-partial-messages"
STREAM_JSON_FORMAT = "stream-json"
JSON_FORMAT = "json"
_COMPACT_JSON_SEPARATORS = (",", ":")


class OutputMode(StrEnum):
    STREAM = "stream"
    JSON = "json"
    SCHEMA = "schema"


@dataclass(frozen=True, slots=True)
class ClaudeRequest:
    """One one-shot invocation. The prompt is not here: it is written to stdin."""

    executable: str
    model: str
    effort: str
    system_prompt: str
    output_mode: OutputMode
    json_schema: dict | None = None


@dataclass(frozen=True, slots=True)
class ClaudeSessionRequest:
    """One long-lived session process, fed a line per turn on stdin."""

    executable: str
    model: str
    effort: str
    system_prompt: str


def build_claude_argv(request: ClaudeRequest) -> list[str]:
    base = _isolated_base(request.executable, request.model, request.effort, request.system_prompt)
    return base + _output_flags(request)


def build_session_argv(request: ClaudeSessionRequest) -> list[str]:
    base = _isolated_base(request.executable, request.model, request.effort, request.system_prompt)
    return base + [INPUT_FORMAT_FLAG, STREAM_JSON_FORMAT, *_streaming_output_flags()]


def _isolated_base(executable: str, model: str, effort: str, system_prompt: str) -> list[str]:
    return [
        executable,
        PRINT_FLAG,
        *_isolation_flags(),
        MODEL_FLAG,
        model,
        EFFORT_FLAG,
        effort,
        SYSTEM_PROMPT_FLAG,
        system_prompt if system_prompt.strip() else DEFAULT_SYSTEM_PROMPT,
    ]


def _isolation_flags() -> list[str]:
    # Never `--bare`: it switches authentication to API keys only, bypassing the plan (R-2).
    return [
        SAFE_MODE_FLAG,
        TOOLS_FLAG,
        NO_TOOLS,
        DISABLE_SLASH_COMMANDS_FLAG,
        NO_SESSION_PERSISTENCE_FLAG,
    ]


def _output_flags(request: ClaudeRequest) -> list[str]:
    if request.output_mode is OutputMode.STREAM:
        return _streaming_output_flags()
    flags = [OUTPUT_FORMAT_FLAG, JSON_FORMAT]
    if request.output_mode is OutputMode.SCHEMA:
        schema = json.dumps(request.json_schema, separators=_COMPACT_JSON_SEPARATORS)
        flags += [JSON_SCHEMA_FLAG, schema]
    return flags


def _streaming_output_flags() -> list[str]:
    return [OUTPUT_FORMAT_FLAG, STREAM_JSON_FORMAT, VERBOSE_FLAG, PARTIAL_MESSAGES_FLAG]
