"""T055: the subprocess boundary — scrubbed environment, empty workdir, prompt on stdin, deadlines.

A tiny Python script stands in for `claude`, so no Claude Code install is needed.
"""

import json
import os
import sys
import textwrap
import time
from pathlib import Path

import pytest

from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind
from app.services.llm.claude_code.runner import SubprocessClaudeCodeRunner, scrubbed_environment

REPORT_SCRIPT = """
import json, os, sys
stdin_text = sys.stdin.read()
print(json.dumps({"cwd": os.getcwd(), "env": sorted(os.environ), "stdin": stdin_text,
                  "argv": sys.argv[1:]}), flush=True)
"""
SLEEP_SCRIPT = """
import sys, time
sys.stdin.read()
time.sleep(float(sys.argv[1]))
print('{"type": "result"}', flush=True)
"""
PID_THEN_HANG_SCRIPT = """
import os, sys, time
print(os.getpid(), flush=True)
time.sleep(30)
"""
FAIL_SCRIPT = """
import sys
print('{"type": "result", "is_error": true}', flush=True)
sys.exit(1)
"""


def _script(tmp_path: Path, name: str, body: str) -> list[str]:
    path = tmp_path / f"{name}.py"
    path.write_text(textwrap.dedent(body))
    return [sys.executable, str(path)]


@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    return tmp_path / "claude-workdir"


@pytest.fixture()
def runner(workdir: Path) -> SubprocessClaudeCodeRunner:
    environ = {
        "PATH": os.environ["PATH"],
        "HOME": str(Path.home()),
        "ANTHROPIC_API_KEY": "sk-should-never-reach-the-child",
        "CLAUDE_CODE_SSE_PORT": "1234",
        "CLAUDECODE": "1",
        "CLAUDE_CONFIG_DIR": "/home/learner/.claude-alt",
    }
    return SubprocessClaudeCodeRunner("claude", workdir, environ)


KEPT_ENVIRONMENT = {
    "CLAUDE_CONFIG_DIR": "/cfg",
    "PATH": "/bin",
    "HOME": "/home/learner",
    "HTTPS_PROXY": "http://proxy",
    "https_proxy": "http://proxy",
}
SCRUBBED_ENVIRONMENT = {
    "ANTHROPIC_API_KEY": "k",
    "ANTHROPIC_BASE_URL": "u",
    "CLAUDE_CODE_ENTRYPOINT": "cli",
    "CLAUDE_CODE_SSE_PORT": "1",
    "CLAUDECODE": "1",
    "CLAUDE_PID": "42",
    "CLAUDE_EFFORT": "max",
}


class TestScrubbedEnvironment:
    def test_environment_scrubs_anthropic_and_claude_code_variables(self):
        environ = {**SCRUBBED_ENVIRONMENT, **KEPT_ENVIRONMENT}

        assert scrubbed_environment(environ) == KEPT_ENVIRONMENT


class TestStreamLines:
    def _report(self, runner, tmp_path) -> dict:
        argv = _script(tmp_path, "report", REPORT_SCRIPT)
        [line] = list(runner.stream_lines([*argv, "--flag"], "Hola, quiero un billete.", 5))
        return json.loads(line)

    def test_runs_in_the_app_owned_workdir_and_creates_it(self, runner, workdir, tmp_path):
        report = self._report(runner, tmp_path)

        assert Path(report["cwd"]) == workdir
        assert list(workdir.iterdir()) == []

    def test_child_gets_the_scrubbed_environment(self, runner, tmp_path):
        env = self._report(runner, tmp_path)["env"]

        assert "ANTHROPIC_API_KEY" not in env
        assert "CLAUDE_CODE_SSE_PORT" not in env and "CLAUDECODE" not in env
        assert "CLAUDE_CONFIG_DIR" in env

    def test_prompt_goes_to_stdin_not_argv(self, runner, tmp_path):
        report = self._report(runner, tmp_path)

        assert report["stdin"] == "Hola, quiero un billete."
        assert report["argv"] == ["--flag"]

    def test_a_missing_executable_is_not_installed(self, runner):
        with pytest.raises(ClaudeCodeFailure) as raised:
            list(runner.stream_lines(["/nonexistent/claude", "-p"], "hi", 5))

        assert raised.value.kind is FailureKind.NOT_INSTALLED

    def test_exceeding_the_deadline_kills_the_process_and_is_unreachable(self, runner, tmp_path):
        argv = _script(tmp_path, "sleep", SLEEP_SCRIPT)
        started = time.monotonic()

        with pytest.raises(ClaudeCodeFailure) as raised:
            list(runner.stream_lines([*argv, "1"], "", 0.2))

        assert raised.value.kind is FailureKind.UNREACHABLE
        assert time.monotonic() - started < 0.9

    def test_the_deadline_is_per_call(self, runner, tmp_path):
        argv = _script(tmp_path, "sleep", SLEEP_SCRIPT)

        with pytest.raises(ClaudeCodeFailure):
            list(runner.stream_lines([*argv, "1"], "", 0.2))
        assert list(runner.stream_lines([*argv, "1"], "", 5)) == ['{"type": "result"}']

    def test_closing_the_generator_early_kills_the_process(self, runner, tmp_path):
        argv = _script(tmp_path, "hang", PID_THEN_HANG_SCRIPT)
        lines = runner.stream_lines(argv, "", 30)
        pid = int(next(lines))

        lines.close()

        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)

    def test_a_non_zero_exit_does_not_raise_by_itself(self, runner, tmp_path):
        argv = _script(tmp_path, "fail", FAIL_SCRIPT)

        assert list(runner.stream_lines(argv, "", 5)) == ['{"type": "result", "is_error": true}']
