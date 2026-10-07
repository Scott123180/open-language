"""`check [<code> | --all]`: read-only; does each catalogued language meet every requirement?"""

import argparse
from collections.abc import Callable

from language_kit.checking import (
    catalogued_languages,
    checked,
    failing_items,
    installed_voices,
    others_than,
)
from language_kit.commands.base import Command, add_code_or_all
from language_kit.composition import Kit
from language_kit.findings import Finding
from language_kit.language_files import LanguageData
from language_kit.output import CommandResult
from language_kit.workspace import KitUsageError

PASSED, FAILED = "✓", "✗"


class CheckCommand(Command):
    name = "check"
    help = "read-only: check catalogued languages against every requirement"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        add_code_or_all(parser)

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        return check_languages(kit, lambda catalogued: selected_codes(arguments, catalogued))


def check_languages(
    kit: Kit, select: Callable[[tuple[str, ...]], tuple[str, ...]]
) -> CommandResult:
    """Check the languages `select` picks from the catalogued ones."""
    languages = catalogued_languages(kit.workspace)
    codes = select(tuple(languages))
    requirements = checked(kit.requirements)
    results = {
        code: failing_items(
            languages[code], others_than(code, languages), kit.rule_context(), requirements
        )
        for code in codes
    }
    return _result(kit, results, {code: languages[code] for code in codes}, len(requirements))


def selected_codes(arguments: argparse.Namespace, catalogued: tuple[str, ...]) -> tuple[str, ...]:
    """The languages a `<code> | --all` command acts on; a usage error for anything else."""
    if arguments.all:
        return catalogued
    if arguments.code is None:
        raise KitUsageError("give a language code or --all")
    if arguments.code not in catalogued:
        raise KitUsageError(
            f"{arguments.code} is not catalogued; to add it, run kit.sh prereq {arguments.code}"
        )
    return (arguments.code,)


def _result(
    kit: Kit,
    results: dict[str, dict[str, list[Finding]]],
    languages: dict[str, LanguageData],
    count: int,
) -> CommandResult:
    findings = [
        finding for items in results.values() for found in items.values() for finding in found
    ]
    passed = {code: not _has_error(items) for code, items in results.items()}
    voices = {
        code: installed_voices(language, kit.workspace.voice_dir)
        for code, language in languages.items()
    }
    summary = _summary(passed, count, _failing_count(results), voices)
    data = {"languages": passed, "voices_installed": voices}
    result = CommandResult.with_findings("check", summary, findings, data=data)
    result.next_step = _next_step(passed)
    return result


def _has_error(items: dict[str, list[Finding]]) -> bool:
    return any(finding.is_error for found in items.values() for finding in found)


def _failing_count(results: dict[str, dict[str, list[Finding]]]) -> int:
    """How many (language, requirement) items have an error."""
    return sum(
        _has_error({path: found}) for items in results.values() for path, found in items.items()
    )


def _summary(
    passed: dict[str, bool], count: int, failing: int, voices: dict[str, tuple[int, int]]
) -> str:
    noun = "language" if len(passed) == 1 else "languages"
    marks = ", ".join(f"{code} {PASSED if ok else FAILED}" for code, ok in passed.items())
    installed = ", ".join(f"{code} {have}/{total}" for code, (have, total) in voices.items())
    return f"check: {len(passed)} {noun}, {count} requirements, {failing} failing ({marks}); voices installed: {installed}"


def _next_step(passed: dict[str, bool]) -> str | None:
    failing = [code for code, ok in passed.items() if not ok]
    if not failing:
        return None
    return f"kit.sh backfill {failing[0]}" if len(failing) == 1 else "kit.sh backfill --all"
