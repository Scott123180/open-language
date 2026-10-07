"""`finish <code> [--pack PATH] [--backend-only]`: apply → verify → check → report, in one command.

It is what an agent runs once a pack validates, for a full pack or a backfill pack alike, so
every run ends with the suites and a report (FR-018, FR-027). It stops at the first step that
fails outside the kit (exit ≥ 2) and still writes the report; a pack with errors stops it
before anything is written.
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from language_kit.commands.apply import apply_pack, record_apply
from language_kit.commands.base import Command
from language_kit.commands.check import check_languages
from language_kit.commands.report import write_report
from language_kit.commands.verify import add_verify_options, verify
from language_kit.composition import Kit
from language_kit.errors import KitExternalError
from language_kit.output import EXIT_EXTERNAL, EXIT_FINDINGS, EXIT_OK, CommandResult


class FinishCommand(Command):
    name = "finish"
    help = "apply a valid pack, then verify, check and report"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("code", help="the language code")
        parser.add_argument("--pack", type=Path, help="the pack (default <out>/<code>/pack.toml)")
        add_verify_options(parser)

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        steps = _Steps(kit, arguments.code, arguments.dry_run)
        rejected = steps.apply(arguments.pack)
        if rejected is not None:
            return rejected
        if steps.exit_code == EXIT_OK and steps.verify(arguments.backend_only):
            steps.check()
        return steps.report()


@dataclass(slots=True)
class _Steps:
    kit: Kit
    code: str
    dry_run: bool
    done: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    exit_code: int = EXIT_OK

    def apply(self, pack: Path | None) -> CommandResult | None:
        """Apply the pack; returns its result only when its errors stop everything."""
        try:
            applied = apply_pack(self.kit, self.code, pack, self.dry_run)
        except KitExternalError as error:
            self._record("apply", "failed")
            self._failed("apply", str(error))
            return None
        if applied.is_rejected:
            return applied.result
        if not self.dry_run:
            record_apply(self.kit, self.code, applied)
        self.lines += applied.result.lines
        self.done.append(f"apply {_state(applied.result.summary, self.dry_run)}")
        return None

    def verify(self, backend_only: bool) -> bool:
        verified = verify(self.kit, self.code, backend_only, self.dry_run)
        self.lines += [
            line
            for line in verified.result.lines
            if self.dry_run or line.startswith(("FAIL", "  "))
        ]
        if verified.result.exit_code != EXIT_OK:
            self._failed("verify", "")
            return False
        self.done.append("verify dry run" if self.dry_run else "verify ok")
        return True

    def check(self) -> None:
        if self.dry_run:  # the language may not be catalogued until apply really runs
            self.done.append("check dry run")
            return
        result = check_languages(self.kit, lambda catalogued: (self.code,))
        failing = result.exit_code == EXIT_FINDINGS
        self._record("check", "findings" if failing else "ok", findings=result.data["findings"])
        self.lines += result.lines
        self.done.append("check failed" if failing else "check ok")
        self.exit_code = EXIT_FINDINGS if failing else self.exit_code

    def report(self) -> CommandResult:
        report = write_report(self.kit, self.code, self.dry_run) if self._has_log() else None
        self.done.append("report written" if report and not self.dry_run else "report not written")
        summary = f"finish {self.code}: " + ", ".join(self.done)
        return CommandResult("finish", self.exit_code, summary, self.lines, self._next_step())

    def _failed(self, step: str, detail: str) -> None:
        self.done.append(f"{step} failed")
        self.lines += [detail] if detail else []
        self.exit_code = EXIT_EXTERNAL

    def _record(self, command: str, outcome: str, **details: object) -> None:
        if not self.dry_run:
            self.kit.record(self.code, command, outcome, **details)

    def _has_log(self) -> bool:
        return (self.kit.workspace.language_dir(self.code) / "run-log.jsonl").is_file()

    def _next_step(self) -> str | None:
        if self.exit_code == EXIT_OK:
            return f"kit.sh bench {self.code}"
        return f"fix what failed above, then kit.sh finish {self.code}"


def _state(summary: str, dry_run: bool) -> str:
    if dry_run:
        return "dry run"
    return "nothing-to-do" if summary.endswith("nothing-to-do") else "ok"
