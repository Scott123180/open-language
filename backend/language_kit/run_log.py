"""The run log: one JSON line per acting command in `<out>/<code>/run-log.jsonl` (R11).

Commands that write append to it; read-only commands never do, so they change no file.
`report` renders the log; nothing is appended by hand.
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from language_kit.workspace import Workspace

RUN_LOG_FILE = "run-log.jsonl"


@dataclass(frozen=True, slots=True)
class RunLogEntry:
    at: str
    command: str
    """prereq | scaffold | validate | apply | verify | check | backfill | bench"""
    outcome: str
    """ok | findings | failed | nothing-to-do | dry-run"""
    findings: list[dict[str, Any]] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    voices_downloaded: list[str] = field(default_factory=list)
    download_seconds: float = 0.0
    """Time spent downloading voices, so it can be subtracted from working time (SC-002)."""
    suites: list[dict[str, Any]] = field(default_factory=list)
    benchmarks: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_json(cls, document: dict[str, Any]) -> "RunLogEntry":
        known = {name: document[name] for name in cls.__dataclass_fields__ if name in document}
        return cls(**known)


class RunLog:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    def append(self, code: str, entry: RunLogEntry) -> None:
        path = self._workspace.language_dir(code) / RUN_LOG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def read(self, code: str) -> list[RunLogEntry]:
        path = self._workspace.language_dir(code) / RUN_LOG_FILE
        if not path.is_file():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [RunLogEntry.from_json(json.loads(line)) for line in lines if line.strip()]
