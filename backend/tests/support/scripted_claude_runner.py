"""A ClaudeCodeRunner that replays recorded `claude` output instead of starting a process.

One-shot calls replay a fixture chosen by the argv's output mode. Session processes replay one
scripted turn per `read_lines_until_result`. Everything the provider sends is recorded.
"""

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from app.services.llm.claude_code.runner import ClaudeCodeRunner, InteractiveProcess
from tests.support.claude_fixtures import load_fixture_lines

ONE_SHOT_FIXTURES = {
    "stream": "stream_ok.ndjson",
    "json": "json_ok.ndjson",
    "schema": "schema_ok.ndjson",
    "auth": "auth_status_signed_in.json",
}


def _one_shot_mode(argv: Sequence[str]) -> str:
    if "auth" in argv:
        return "auth"
    if "--json-schema" in argv:
        return "schema"
    return "stream" if "stream-json" in argv else "json"


def success_turn(text: str = "Buenos días.") -> list[str]:
    delta = {"type": "stream_event", "event": {"delta": {"type": "text_delta", "text": text}}}
    result = {"type": "result", "is_error": False, "result": text}
    return [json.dumps(delta, ensure_ascii=False), json.dumps(result, ensure_ascii=False)]


@dataclass
class OneShotCall:
    argv: list[str]
    stdin_text: str
    timeout_seconds: float


class ScriptedInteractiveProcess(InteractiveProcess):
    def __init__(self, runner: "ScriptedClaudeCodeRunner") -> None:
        self._runner = runner
        self.sent_lines: list[str] = []
        self.close_count = 0

    def send_line(self, line: str) -> None:
        if self.close_count or self._runner.is_dead:
            raise ClaudeCodeFailure(FailureKind.UNREACHABLE, "scripted process is gone")
        self.sent_lines.append(line)

    def read_lines_until_result(self, timeout_seconds: float) -> Iterator[str]:
        self._runner.read_timeouts.append(timeout_seconds)
        if self._runner.is_dead:
            raise ClaudeCodeFailure(FailureKind.UNREACHABLE, "scripted process exited")
        turn = self._runner.session_turns.pop(0) if self._runner.session_turns else success_turn()
        yield from turn

    @property
    def is_alive(self) -> bool:
        return not self.close_count and not self._runner.is_dead

    def close(self) -> None:
        self.close_count += 1

    @property
    def sent_messages(self) -> list[dict]:
        return [json.loads(line) for line in self.sent_lines]


@dataclass
class ScriptedClaudeCodeRunner(ClaudeCodeRunner):
    fixtures: dict[str, str] = field(default_factory=lambda: dict(ONE_SHOT_FIXTURES))
    error: Exception | None = None
    session_turns: list[list[str]] = field(default_factory=list)
    spawn_error: Exception | None = None
    is_dead: bool = False
    calls: list[OneShotCall] = field(default_factory=list)
    spawns: list[tuple[list[str], Path]] = field(default_factory=list)
    processes: list[ScriptedInteractiveProcess] = field(default_factory=list)
    read_timeouts: list[float] = field(default_factory=list)

    def stream_lines(
        self, argv: Sequence[str], stdin_text: str, timeout_seconds: float
    ) -> Iterator[str]:
        self.calls.append(OneShotCall(list(argv), stdin_text, timeout_seconds))
        if self.error is not None:
            raise self.error
        yield from load_fixture_lines(self.fixtures[_one_shot_mode(argv)])

    def spawn_interactive(self, argv: Sequence[str], log_path: Path) -> InteractiveProcess:
        self.spawns.append((list(argv), log_path))
        if self.spawn_error is not None:
            raise self.spawn_error
        process = ScriptedInteractiveProcess(self)
        self.processes.append(process)
        return process

    @property
    def prompt_calls(self) -> list[OneShotCall]:
        """Calls that sent a prompt, leaving out `auth status` pre-flight checks."""
        return [call for call in self.calls if "auth" not in call.argv]
