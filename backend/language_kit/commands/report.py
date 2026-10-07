"""`report <code>`: regenerate report.md from the run log."""

import argparse

from language_kit.commands.base import Command
from language_kit.composition import Kit
from language_kit.errors import KitUsageError
from language_kit.language_files import read_language
from language_kit.output import EXIT_OK, CommandResult
from language_kit.report import render_report
from language_kit.run_log import RunLog

REPORT_FILE = "report.md"


class ReportCommand(Command):
    name = "report"
    help = "regenerate <out>/<code>/report.md from the run log"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("code", help="the language code")

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        return write_report(kit, arguments.code, arguments.dry_run)


def write_report(kit: Kit, code: str, dry_run: bool) -> CommandResult:
    entries = RunLog(kit.workspace).read(code)
    if not entries:
        raise KitUsageError(
            f"no run log for {code} yet: run kit.sh scaffold, finish or backfill first"
        )
    text = render_report(code, _title(kit, code), entries, kit.workspace.root)
    path = kit.workspace.language_dir(code) / REPORT_FILE
    if dry_run:
        return CommandResult(
            "report", EXIT_OK, f"report {code}: dry run; not written", text.splitlines()
        )
    path.write_text(text, encoding="utf-8")
    return CommandResult("report", EXIT_OK, f"report {code}: wrote {kit.workspace.relative(path)}")


def _title(kit: Kit, code: str) -> str:
    name = read_language(code, kit.workspace).get("name")
    return f"{name} ({code})" if isinstance(name, str) else code
