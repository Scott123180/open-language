"""`build_kit()`: the one place the kit's real collaborators are made. Tests pass fakes."""

import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TextIO

from language_kit.bench import BenchProbe, OllamaProbe
from language_kit.clock import Clock, SystemClock
from language_kit.context import RuleContext, gather_rule_context
from language_kit.registry import REQUIREMENTS, Requirement
from language_kit.run_log import RunLog, RunLogEntry
from language_kit.verify import CommandRunner, SubprocessCommandRunner
from language_kit.voices import (
    HttpVoiceDownloader,
    PiperVoiceCatalogue,
    VoiceCatalogue,
    VoiceDownloader,
)
from language_kit.workspace import Workspace


@dataclass(slots=True)
class Kit:
    workspace: Workspace
    clock: Clock
    out: TextIO
    context: RuleContext | None = None
    """Gathered from the app on first use when not given."""
    requirements: tuple[Requirement, ...] = REQUIREMENTS
    voice_catalogue: VoiceCatalogue | None = None
    downloader: VoiceDownloader | None = None
    runner: CommandRunner | None = None
    bench_probe: BenchProbe | None = None

    def rule_context(self) -> RuleContext:
        if self.context is None:
            self.context = gather_rule_context(self.workspace)
        return self.context

    def record(self, code: str, command: str, outcome: str, **details: object) -> None:
        """Append a run-log entry for `code`, stamped with the kit's clock."""
        entry = RunLogEntry(at=self.clock.now().isoformat(), command=command, outcome=outcome, **details)  # type: ignore[arg-type]
        RunLog(self.workspace).append(code, entry)

    def with_output(self, out: Path) -> "Kit":
        return replace(self, workspace=self.workspace.with_output(out))


def build_kit() -> Kit:
    workspace = Workspace.discover(Path.cwd())
    clock = SystemClock()
    return Kit(
        workspace=workspace,
        clock=clock,
        out=sys.stdout,
        voice_catalogue=PiperVoiceCatalogue(clock=clock),
        downloader=HttpVoiceDownloader(workspace.voice_dir),
        runner=SubprocessCommandRunner(),
        bench_probe=OllamaProbe(),
    )
