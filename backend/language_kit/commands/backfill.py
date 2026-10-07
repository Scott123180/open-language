"""`backfill [<code> | --all]`: per language, a partial pack holding only its failing items."""

import argparse
from dataclasses import dataclass
from pathlib import Path

from language_kit.checking import catalogued_languages, checked, failing_items, others_than
from language_kit.commands.base import Command, add_code_or_all
from language_kit.commands.check import selected_codes
from language_kit.composition import Kit
from language_kit.findings import Finding
from language_kit.language_files import LanguageData
from language_kit.output import EXIT_OK, CommandResult
from language_kit.pack import LanguagePack
from language_kit.template import TemplateSources, partial_pack

BACKFILL_FILE = "backfill-pack.toml"


@dataclass(frozen=True, slots=True)
class Backfill:
    code: str
    items: dict[str, tuple[str, ...] | None]
    """Failing requirement paths, with the table keys that fail (None: the whole item)."""
    path: Path
    written: bool
    blocked: bool = False
    """A backfill pack is still being filled, so none is written."""


class BackfillCommand(Command):
    name = "backfill"
    help = "write a backfill pack of the failing items for each language"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        add_code_or_all(parser)

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        languages = catalogued_languages(kit.workspace)
        codes = selected_codes(arguments, tuple(languages))
        sources = TemplateSources(languages, kit.rule_context(), kit.requirements)
        backfills = [_backfill(kit, code, sources, arguments.dry_run) for code in codes]
        return _result(kit, backfills, arguments.dry_run)


def failing_requirements(
    kit: Kit, code: str, sources: TemplateSources
) -> dict[str, tuple[str, ...] | None]:
    languages = dict(sources.languages)
    found = failing_items(
        languages[code], others_than(code, languages), sources.context, checked(kit.requirements)
    )
    errors = {path: [f for f in findings if f.is_error] for path, findings in found.items()}
    return {path: _table_keys(path, findings) for path, findings in errors.items() if findings}


def _backfill(kit: Kit, code: str, sources: TemplateSources, dry_run: bool) -> Backfill:
    items = failing_requirements(kit, code, sources)
    path = kit.workspace.language_dir(code) / BACKFILL_FILE
    language = sources.languages[code]
    blocked = bool(items) and not _replaceable(path, language, kit)
    can_write = bool(items) and not blocked and not dry_run
    if can_write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(partial_pack(language, items, sources), encoding="utf-8")
        kit.record(code, "backfill", "ok", files_written=[kit.workspace.relative(path)])
    return Backfill(code, items, path, can_write, blocked)


def _replaceable(path: Path, language: LanguageData, kit: Kit) -> bool:
    """No pack yet, or one already applied (it would change nothing); never one being filled."""
    if not path.exists():
        return True
    pack = LanguagePack.parse(path.read_text(encoding="utf-8"), language.code, kit.requirements)
    return not pack.problems and pack.merged_onto(language).document == language.document


def _table_keys(path: str, findings: list[Finding]) -> tuple[str, ...] | None:
    """The table keys the findings name (`evaluation.turns.rent-a-car`), or None for the whole item."""
    keys = [finding.path.removeprefix(f"{path}.") for finding in findings]
    if any(finding.path == path or not finding.path.startswith(f"{path}.") for finding in findings):
        return None
    return tuple(dict.fromkeys(keys))


def _result(kit: Kit, backfills: list[Backfill], dry_run: bool) -> CommandResult:
    lines = [_line(kit, backfill, dry_run) for backfill in backfills]
    written = [b for b in backfills if b.written or (dry_run and b.items and not b.blocked)]
    idle = [b for b in backfills if b not in written]
    verb = "would write" if dry_run else "written"
    parts = (
        [f"{len(written)} {'pack' if len(written) == 1 else 'packs'} {verb} ({_codes(written)})"]
        if written
        else []
    )
    parts += [f"{len(idle)} nothing-to-do ({_codes(idle)})"] if idle else []
    data = {"packs": [kit.workspace.relative(b.path) for b in written]}
    return CommandResult(
        "backfill", EXIT_OK, "backfill: " + ", ".join(parts), lines, _next(kit, written), data
    )


def _line(kit: Kit, backfill: Backfill, dry_run: bool) -> str:
    target = kit.workspace.relative(backfill.path)
    if not backfill.items:
        return f"{backfill.code}: nothing-to-do"
    if dry_run and not backfill.blocked:
        return f"{backfill.code}: would write {len(backfill.items)} items → {target}"
    if not backfill.written:
        return f"{backfill.code}: nothing-to-do ({BACKFILL_FILE} exists; fill it, then kit.sh finish --pack {target})"
    return f"{backfill.code}: {len(backfill.items)} items → {target}"


def _next(kit: Kit, written: list[Backfill]) -> str | None:
    if len(written) == 1:
        return f"kit.sh finish {written[0].code} --pack {kit.workspace.relative(written[0].path)}"
    if written:
        return "fill and validate each pack, kit.sh apply each, then kit.sh finish <code> --pack <path> each"
    return None


def _codes(backfills: list[Backfill]) -> str:
    return ", ".join(backfill.code for backfill in backfills)
