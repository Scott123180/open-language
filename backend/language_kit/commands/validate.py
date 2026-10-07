"""`validate <code> [--pack PATH]`: read-only; every finding for the pack merged onto the language."""

import argparse
from pathlib import Path

from language_kit.commands.base import Command
from language_kit.composition import Kit
from language_kit.output import CommandResult
from language_kit.pack_check import check_pack


class ValidateCommand(Command):
    name = "validate"
    help = "read-only: check a pack, merged onto the language's data"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("code", help="the language code")
        parser.add_argument("--pack", type=Path, help="the pack (default <out>/<code>/pack.toml)")

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        check = check_pack(kit, arguments.code, arguments.pack)
        summary = (
            f"validate {arguments.code}: {len(check.errors)} errors, {len(check.warnings)} warnings"
        )
        result = CommandResult.with_findings("validate", summary, check.findings)
        pack_option = f" --pack {kit.workspace.relative(check.path)}" if arguments.pack else ""
        if check.errors:
            result.next_step = f"fix the FAIL lines in the pack, then kit.sh validate {arguments.code}{pack_option}"
        else:
            result.next_step = f"kit.sh finish {arguments.code}{pack_option}"
        return result
