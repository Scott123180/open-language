"""`scaffold <code> --name <Name>`: check prerequisites, then write the pack to fill. Never overwrites."""

import argparse
from pathlib import Path

from language_kit.checking import catalogued_languages
from language_kit.commands.base import Command
from language_kit.commands.prereq import prerequisites, prerequisites_result
from language_kit.composition import Kit
from language_kit.findings import findings_as_json
from language_kit.output import EXIT_OK, CommandResult
from language_kit.pack_check import pack_path
from language_kit.prerequisites import Prerequisites
from language_kit.template import TemplateSources, full_pack


class ScaffoldCommand(Command):
    name = "scaffold"
    help = "check prerequisites, then write <out>/<code>/pack.toml to fill"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("code", help="the ISO 639-1 code of the language to add")
        parser.add_argument(
            "--name", required=True, help="the language's English name, e.g. Italian"
        )

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        code, found = arguments.code, prerequisites(kit, arguments.code)
        if not found.ok:
            return prerequisites_result(found)
        path = pack_path(kit, code, None)
        relative = kit.workspace.relative(path)
        if path.exists():
            return _existing(kit, code, relative, arguments.dry_run)
        if arguments.dry_run:
            return CommandResult("scaffold", EXIT_OK, f"scaffold {code}: would write {relative}")
        _write_pack(kit, arguments.name, found, path)
        _record(kit, found, relative)
        lines = [warning.text() for warning in found.warnings]
        return CommandResult(
            "scaffold",
            EXIT_OK,
            f"scaffold {code}: wrote {relative}",
            lines,
            f"kit.sh validate {code}",
        )


def _write_pack(kit: Kit, name: str, found: Prerequisites, path: Path) -> None:
    sources = TemplateSources(
        catalogued_languages(kit.workspace), kit.rule_context(), kit.requirements
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(full_pack(found.code, name, sources, found.candidates), encoding="utf-8")


def _record(kit: Kit, found: Prerequisites, relative: str) -> None:
    kit.record(found.code, "prereq", "ok", findings=findings_as_json(found.warnings))
    kit.record(found.code, "scaffold", "ok", files_written=[relative])


def _existing(kit: Kit, code: str, relative: str, dry_run: bool) -> CommandResult:
    if not dry_run:
        kit.record(code, "scaffold", "nothing-to-do")
    summary = f"scaffold {code}: nothing-to-do ({relative} exists; it is never overwritten)"
    return CommandResult("scaffold", EXIT_OK, summary, next_step=f"kit.sh validate {code}")
