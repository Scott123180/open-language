"""Running the suites: each in its own directory, output to a log, one summary line each (R10)."""

import os
import re
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

MAX_FAILURE_IDS = 20
NOT_FOUND_EXIT = 127
PASSED, FAILED, SKIPPED = "passed", "failed", "skipped"
_PYTEST_SUMMARY = re.compile(r"\d+ (passed|failed|error)")
_VITEST_SUMMARY = re.compile(r"^\s*Tests\s")
_PLAYWRIGHT_SUMMARY = re.compile(r"^\s*\d+ (passed|failed|skipped|flaky)")
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
"""Terminal colour and cursor codes, which Playwright and Vite put before their summaries."""
_FAILURE_LINE = re.compile(r"^(FAILED |FAIL |\s*✘)")


@dataclass(frozen=True, slots=True)
class CompletedRun:
    exit_code: int
    output: str


class CommandRunner(ABC):
    @abstractmethod
    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        log: Path,
        environment: Mapping[str, str] | None = None,
    ) -> CompletedRun:
        """Run a command in `cwd`, its output (stdout and stderr) written to `log`."""


class SubprocessCommandRunner(CommandRunner):
    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        log: Path,
        environment: Mapping[str, str] | None = None,
    ) -> CompletedRun:
        log.parent.mkdir(parents=True, exist_ok=True)
        try:
            run = _completed(argv, cwd, os.environ | dict(environment or {}))
        except OSError as error:
            run = CompletedRun(NOT_FOUND_EXIT, f"{argv[0]}: could not be run ({error})\n")
        log.write_text(run.output, encoding="utf-8")
        return run


def _completed(argv: Sequence[str], cwd: Path, environment: Mapping[str, str]) -> CompletedRun:
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        env=dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return CompletedRun(completed.returncode, completed.stdout)


@dataclass(frozen=True, slots=True)
class Suite:
    name: str
    argv: tuple[str, ...]
    directory: str
    """`backend` or `frontend`, under the repository root."""

    @property
    def is_frontend(self) -> bool:
        return self.directory == "frontend"


SUITES = (
    Suite("pytest", (".venv/bin/pytest",), "backend"),
    Suite("ruff", (".venv/bin/ruff", "check", "."), "backend"),
    Suite("black", (".venv/bin/black", "--check", "."), "backend"),
    Suite("mypy", (".venv/bin/mypy", "language_kit", "app/language_data"), "backend"),
    Suite("eslint", ("npm", "run", "lint"), "frontend"),
    Suite("vitest", ("npm", "test", "--", "--run"), "frontend"),
    Suite("playwright", ("npm", "run", "test:e2e"), "frontend"),
)


@dataclass(frozen=True, slots=True)
class SuiteResult:
    name: str
    status: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: tuple[str, ...] = ()
    """Up to 20 failing test ids."""
    log: str | None = None

    @property
    def ok(self) -> bool:
        return self.status != FAILED

    def as_json(self) -> dict[str, object]:
        fields = ("name", "passed", "failed", "skipped", "status", "log")
        return {field: getattr(self, field) for field in fields}


def summarise(name: str, exit_code: int, output: str) -> SuiteResult:
    output = _ANSI_ESCAPE.sub("", output)
    lines = _summary_lines(name, output.splitlines())
    passed, failed = _count(lines, "passed"), _count(lines, "failed") + _count(lines, "error")
    status = PASSED if exit_code == 0 and failed == 0 else FAILED
    return SuiteResult(name, status, passed, failed, _count(lines, "skipped"), _failure_ids(output))


def run_suites(
    runner: CommandRunner, root: Path, logs: Path, suites: Iterable[Suite], skip_frontend: bool
) -> list[SuiteResult]:
    return [
        (
            SuiteResult(suite.name, SKIPPED)
            if skip_frontend and suite.is_frontend
            else _run(runner, root, logs, suite)
        )
        for suite in suites
    ]


def _run(runner: CommandRunner, root: Path, logs: Path, suite: Suite) -> SuiteResult:
    log = logs / f"{suite.name}.log"
    completed = runner.run(suite.argv, root / suite.directory, log)
    return replace(summarise(suite.name, completed.exit_code, completed.output), log=str(log))


def _summary_lines(name: str, lines: list[str]) -> list[str]:
    if name == "pytest":
        return [line for line in lines if _PYTEST_SUMMARY.search(line)][-1:]
    if name == "vitest":
        return [line for line in lines if _VITEST_SUMMARY.match(line)][-1:]
    if name == "playwright":
        return [line for line in lines if _PLAYWRIGHT_SUMMARY.match(line)]
    return []


def _count(lines: list[str], word: str) -> int:
    return sum(int(number) for line in lines for number in re.findall(rf"(\d+) {word}", line))


def _failure_ids(output: str) -> tuple[str, ...]:
    failing = [line for line in output.splitlines() if _FAILURE_LINE.match(line)]
    return tuple(_failure_id(line) for line in failing[:MAX_FAILURE_IDS])


def _failure_id(line: str) -> str:
    stripped = line.strip()
    return stripped.split()[1] if stripped.startswith("FAILED ") else stripped
