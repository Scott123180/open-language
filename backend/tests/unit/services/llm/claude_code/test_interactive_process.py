"""T056: a long-lived session process — one line in, events out until each turn's result."""

import json
import sys
import textwrap
import time
from pathlib import Path

import pytest

from app.services.llm.claude_code import runner as runner_module
from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from app.services.llm.claude_code.runner import SubprocessClaudeCodeRunner

ECHO_SCRIPT = """
import json, sys
sys.stderr.write("session started\\n")
sys.stderr.flush()
for line in sys.stdin:
    text = json.loads(line)["message"]["content"]
    delta = {"type": "stream_event", "event": {"delta": {"type": "text_delta", "text": text}}}
    print(json.dumps(delta), flush=True)
    print(json.dumps({"type": "result", "is_error": False, "result": text}), flush=True)
"""
STUBBORN_SCRIPT = """
import signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print("ready", flush=True)
time.sleep(30)
"""


def _user_line(text: str) -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": text}})


@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    return tmp_path / "claude-workdir"


@pytest.fixture()
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "claude-logs" / "session-roleplay-7.log"


@pytest.fixture()
def spawn(tmp_path, workdir, log_path):
    runner = SubprocessClaudeCodeRunner("claude", workdir, {"PATH": "/usr/bin:/bin"})
    processes = []

    def _spawn(body: str = ECHO_SCRIPT):
        script = tmp_path / "session.py"
        script.write_text(textwrap.dedent(body))
        process = runner.spawn_interactive([sys.executable, str(script)], log_path)
        processes.append(process)
        return process

    yield _spawn
    for process in processes:
        process.close()


def test_each_turn_reads_up_to_and_including_its_result(spawn):
    process = spawn()

    process.send_line(_user_line("uno"))
    first = list(process.read_lines_until_result(5))
    process.send_line(_user_line("dos"))
    second = list(process.read_lines_until_result(5))

    assert len(first) == 2 and '"result": "uno"' in first[-1]
    assert len(second) == 2 and '"result": "dos"' in second[-1]


def test_stderr_goes_to_the_log_file_not_the_workdir(spawn, log_path, workdir):
    process = spawn()
    process.send_line(_user_line("uno"))
    list(process.read_lines_until_result(5))
    process.close()

    assert "session started" in log_path.read_text()
    assert list(workdir.iterdir()) == []


def test_the_log_is_truncated_on_spawn(spawn, log_path):
    log_path.parent.mkdir(parents=True)
    log_path.write_text("an earlier session's noise\n")

    process = spawn()
    process.send_line(_user_line("uno"))
    list(process.read_lines_until_result(5))
    process.close()

    assert "earlier" not in log_path.read_text()


def test_a_turn_past_its_deadline_kills_the_process(spawn):
    process = spawn()

    with pytest.raises(ClaudeCodeFailure) as raised:
        list(process.read_lines_until_result(0.2))

    assert raised.value.kind is FailureKind.UNREACHABLE
    assert process.is_alive is False


def test_is_alive_follows_the_process(spawn):
    process = spawn()
    assert process.is_alive is True

    process.close()

    assert process.is_alive is False


def test_close_is_idempotent(spawn):
    process = spawn()

    process.close()
    process.close()

    assert process.is_alive is False


def test_close_kills_a_process_that_ignores_terminate(spawn, monkeypatch):
    monkeypatch.setattr(runner_module, "TERMINATE_GRACE_SECONDS", 0.2)
    process = spawn(STUBBORN_SCRIPT)
    time.sleep(0.3)  # let the script install its SIGTERM handler

    process.close()

    assert process.is_alive is False


def test_a_process_that_exits_mid_turn_is_unreachable(spawn):
    process = spawn('print("partial", flush=True)\n')

    with pytest.raises(ClaudeCodeFailure) as raised:
        list(process.read_lines_until_result(5))

    assert raised.value.kind is FailureKind.UNREACHABLE
