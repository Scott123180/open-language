"""`apply <code> [--pack PATH]`: validate, fetch voices, write the two data files atomically."""

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from language_kit.apply import ApplyPlan, ensure_voices, plan_apply, write_atomically
from language_kit.checking import is_installed
from language_kit.commands.base import Command
from language_kit.composition import Kit
from language_kit.errors import KitExternalError
from language_kit.findings import Finding, findings_as_json
from language_kit.output import EXIT_FINDINGS, EXIT_OK, CommandResult
from language_kit.pack_check import check_pack
from language_kit.voices import VoiceCandidate, VoiceDownload

MEGABYTE = 1_000_000


class ApplyCommand(Command):
    name = "apply"
    help = "write a valid pack into the data files (fetches its voices first)"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("code", help="the language code")
        parser.add_argument("--pack", type=Path, help="the pack (default <out>/<code>/pack.toml)")

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        code, dry_run = arguments.code, arguments.dry_run
        try:
            applied = apply_pack(kit, code, arguments.pack, dry_run)
        except KitExternalError:
            if not dry_run:
                kit.record(code, "apply", "failed")
            raise
        if not dry_run:
            record_apply(kit, code, applied)
        return applied.result


@dataclass(slots=True)
class Applied:
    """What `apply` did, for `finish` and the run log."""

    result: CommandResult
    files_written: list[str] = field(default_factory=list)
    downloads: list[VoiceDownload] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    @property
    def is_rejected(self) -> bool:
        """The pack had errors, so nothing was written."""
        return self.result.exit_code == EXIT_FINDINGS


def record_apply(kit: Kit, code: str, applied: Applied) -> None:
    """The run-log entry for an apply that went ahead; a rejected pack changed nothing, so none."""
    if applied.is_rejected:
        return
    fetched = [download.key for download in applied.downloads if download.downloaded]
    kit.record(
        code,
        "apply",
        "ok" if applied.files_written or fetched else "nothing-to-do",
        findings=findings_as_json(applied.warnings),
        files_written=applied.files_written,
        voices_downloaded=fetched,
        download_seconds=sum(download.seconds for download in applied.downloads),
    )


def apply_pack(kit: Kit, code: str, pack: Path | None, dry_run: bool) -> Applied:
    check = check_pack(kit, code, pack)
    if check.errors:
        summary = f"apply {code}: {len(check.errors)} errors; nothing changed"
        result = CommandResult.with_findings("apply", summary, check.findings)
        result.next_step = f"fix the FAIL lines, then kit.sh validate {code}"
        return Applied(result)
    plan = plan_apply(kit, check)
    if plan.is_empty:
        result = CommandResult("apply", EXIT_OK, f"apply {code}: nothing-to-do")
        return Applied(result, warnings=check.warnings)
    if dry_run:
        return Applied(_dry_run(kit, code, plan))
    downloads = ensure_voices(kit, plan.voices)
    write_atomically(plan.changes)
    applied = _applied(kit, code, plan, downloads)
    applied.warnings = check.warnings
    applied.result.lines = [warning.text() for warning in check.warnings]
    return applied


def _applied(kit: Kit, code: str, plan: ApplyPlan, downloads: list[VoiceDownload]) -> Applied:
    written = [kit.workspace.relative(change.path) for change in plan.changes]
    fetched = [download.key for download in downloads if download.downloaded]
    summary = f"apply {code}: wrote {len(written)} files, downloaded {len(fetched)} voices"
    data = {"files_written": written, "voices_downloaded": fetched}
    result = CommandResult(
        "apply", EXIT_OK, summary, next_step=f"kit.sh verify --language {code}", data=data
    )
    return Applied(result, written, downloads)


def _dry_run(kit: Kit, code: str, plan: ApplyPlan) -> CommandResult:
    lines = [
        f"would write {kit.workspace.relative(change.path)} (+{change.added} −{change.removed} lines)"
        for change in plan.changes
    ]
    lines += [_voice_line(kit, voice) for voice in plan.voices]
    summary = f"apply {code}: dry run; {len(plan.changes)} files and {len(plan.voices)} voices would change"
    return CommandResult("apply", EXIT_OK, summary, lines)


def _voice_line(kit: Kit, voice: VoiceCandidate) -> str:
    if is_installed(voice.key, kit.workspace.voice_dir):
        return f"would verify {voice.key} (installed)"
    return f"would download {voice.key} ({round(voice.size_bytes / MEGABYTE)} MB)"
