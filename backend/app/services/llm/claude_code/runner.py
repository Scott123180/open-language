"""The subprocess boundary: the only code that starts a `claude` process (DIP).

Every process runs in the app-owned empty working directory, with an environment scrubbed of
anything that could switch billing away from the learner's plan (R-2), and is killed at its
deadline or when its reader stops early (FR-019).
"""

import logging
import subprocess
import threading
from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import IO

from app.services.llm.claude_code.events import is_result_line
from app.services.llm.claude_code.failures import ClaudeCodeFailure, FailureKind

logger = logging.getLogger(__name__)

SCRUBBED_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_")
SCRUBBED_KEYS = frozenset({"CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT"})
TERMINATE_GRACE_SECONDS = 2.0
_ENCODING = "utf-8"
_LINE_BUFFERED = 1


class InteractiveProcess(ABC):
    """A long-lived session process: one stdin line per turn, events until that turn's result."""

    @abstractmethod
    def send_line(self, line: str) -> None: ...

    @abstractmethod
    def read_lines_until_result(self, timeout_seconds: float) -> Iterator[str]:
        """Yield lines up to and including the next result line. Raises ClaudeCodeFailure."""

    @property
    @abstractmethod
    def is_alive(self) -> bool: ...

    @abstractmethod
    def close(self) -> None:
        """Terminate, then kill after a grace period. Idempotent."""


class ClaudeCodeRunner(ABC):
    @abstractmethod
    def stream_lines(
        self, argv: Sequence[str], stdin_text: str, timeout_seconds: float
    ) -> Iterator[str]:
        """Yield stdout lines. Kill the process when timeout_seconds elapses or the generator
        closes. Raise ClaudeCodeFailure(not_installed) if the executable is missing.
        A non-zero exit code alone does not raise: the caller classifies from the lines."""

    @abstractmethod
    def spawn_interactive(self, argv: Sequence[str], log_path: Path) -> InteractiveProcess:
        """Start a session process whose stderr goes to `log_path`, truncated on spawn."""


def scrubbed_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """The environment minus every variable that could redirect billing or attach to a parent
    Claude Code session. `CLAUDE_CONFIG_DIR` is kept, so a relocated sign-in still works."""
    return {
        name: value
        for name, value in environ.items()
        if not name.startswith(SCRUBBED_PREFIXES) and name not in SCRUBBED_KEYS
    }


class SubprocessClaudeCodeRunner(ClaudeCodeRunner):
    def __init__(self, executable: str, workdir: Path, environ: Mapping[str, str]) -> None:
        self._executable = executable
        self._workdir = workdir
        self._environ = scrubbed_environment(environ)

    @property
    def executable(self) -> str:
        return self._executable

    @property
    def workdir(self) -> Path:
        return self._workdir

    @property
    def environment(self) -> Mapping[str, str]:
        """The scrubbed environment every child process receives."""
        return dict(self._environ)

    def stream_lines(
        self, argv: Sequence[str], stdin_text: str, timeout_seconds: float
    ) -> Iterator[str]:
        process = self._spawn(argv, stderr=subprocess.DEVNULL)
        deadline = _Deadline(process, timeout_seconds)
        try:
            _write_and_close(process.stdin, stdin_text)
            for line in iter(process.stdout.readline, ""):
                yield line.rstrip("\n")
        finally:
            deadline.cancel()
            _stop(process)
        if deadline.has_expired:
            raise ClaudeCodeFailure(FailureKind.UNREACHABLE, f"Timed out after {timeout_seconds}s")

    def spawn_interactive(self, argv: Sequence[str], log_path: Path) -> InteractiveProcess:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "w", encoding=_ENCODING)  # noqa: SIM115 — owned by the process
        try:
            process = self._spawn(argv, stderr=log_file)
        except ClaudeCodeFailure:
            log_file.close()
            raise
        return _SubprocessInteractiveProcess(process, log_file)

    def _spawn(self, argv: Sequence[str], stderr) -> subprocess.Popen:
        self._workdir.mkdir(parents=True, exist_ok=True)
        try:
            return subprocess.Popen(
                list(argv),
                cwd=self._workdir,
                env=self._environ,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
                text=True,
                encoding=_ENCODING,
                bufsize=_LINE_BUFFERED,
            )
        except FileNotFoundError as exc:
            detail = f"Claude Code was not found (configured as {self._executable!r})"
            raise ClaudeCodeFailure(FailureKind.NOT_INSTALLED, detail) from exc


class _SubprocessInteractiveProcess(InteractiveProcess):
    def __init__(self, process: subprocess.Popen, log_file: IO[str]) -> None:
        self._process = process
        self._log_file = log_file
        self._is_closed = False

    def send_line(self, line: str) -> None:
        try:
            self._process.stdin.write(line + "\n")
            self._process.stdin.flush()
        except OSError as exc:
            raise ClaudeCodeFailure(
                FailureKind.UNREACHABLE, f"Session stdin closed: {exc}"
            ) from exc

    def read_lines_until_result(self, timeout_seconds: float) -> Iterator[str]:
        deadline = _Deadline(self._process, timeout_seconds)
        try:
            for line in iter(self._process.stdout.readline, ""):
                yield line.rstrip("\n")
                if is_result_line(line):
                    return
        finally:
            deadline.cancel()
        reason = "timed out" if deadline.has_expired else "exited before finishing its reply"
        raise ClaudeCodeFailure(FailureKind.UNREACHABLE, f"The session process {reason}")

    @property
    def is_alive(self) -> bool:
        return self._process.poll() is None

    def close(self) -> None:
        if self._is_closed:
            return
        self._is_closed = True
        _stop(self._process)
        self._log_file.close()


class _Deadline:
    """Kills the process when the time runs out, and remembers that it did."""

    def __init__(self, process: subprocess.Popen, seconds: float) -> None:
        self._expired = threading.Event()
        self._timer = threading.Timer(seconds, self._expire, args=(process,))
        self._timer.daemon = True
        self._timer.start()

    @property
    def has_expired(self) -> bool:
        return self._expired.is_set()

    def cancel(self) -> None:
        self._timer.cancel()

    def _expire(self, process: subprocess.Popen) -> None:
        self._expired.set()
        process.kill()


def _write_and_close(stream: IO[str], text: str) -> None:
    try:
        stream.write(text)
    except BrokenPipeError:
        logger.debug("claude exited before reading its prompt; its output says why")
    _close_stream(stream)


def _stop(process: subprocess.Popen) -> None:
    """Terminate, then kill after the grace period, and reap the process."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=TERMINATE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
    process.wait()
    for stream in (process.stdin, process.stdout):
        _close_stream(stream)


def _close_stream(stream: IO[str] | None) -> None:
    if stream is None or stream.closed:
        return
    try:
        stream.close()
    except BrokenPipeError:
        # Closing flushes; the reader is gone, so the unsent text has nowhere to go.
        logger.debug("Discarded unsent input to a claude process that had exited")
