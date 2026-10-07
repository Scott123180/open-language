"""`verify [--language CODE] [--backend-only]`: run every suite; one line each, logs on disk."""

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from language_kit.commands.base import Command
from language_kit.composition import Kit
from language_kit.errors import KitExternalError
from language_kit.output import EXIT_EXTERNAL, EXIT_OK, CommandResult
from language_kit.verify import FAILED, SKIPPED, SUITES, CommandRunner, SuiteResult, run_suites

SHARED_LOGS = "_logs"
LOGS = "logs"
FAILURE_INDENT = "  "


class VerifyCommand(Command):
    name = "verify"
    help = "run the backend and frontend suites and linters"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        add_verify_options(parser)
        parser.add_argument(
            "--language", help="keep the logs and the run-log entry under this language"
        )

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        return verify(kit, arguments.language, arguments.backend_only, arguments.dry_run).result


def add_verify_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backend-only", action="store_true", help="skip the frontend suites (reported)"
    )


@dataclass(frozen=True, slots=True)
class Verified:
    result: CommandResult
    suites: list[SuiteResult]


def verify(kit: Kit, language: str | None, backend_only: bool, dry_run: bool) -> Verified:
    if dry_run:
        lines = [f"would run {suite.name} (in {suite.directory})" for suite in SUITES]
        return Verified(
            CommandResult("verify", EXIT_OK, f"verify: dry run; {len(SUITES)} suites", lines), []
        )
    logs = (
        kit.workspace.language_dir(language) / LOGS
        if language
        else kit.workspace.output_root / SHARED_LOGS
    )
    suites = run_suites(_runner(kit), kit.workspace.root, logs, SUITES, backend_only)
    suites = [_relative_log(kit, suite) for suite in suites]
    if language:
        outcome = "ok" if all(suite.ok for suite in suites) else "failed"
        kit.record(language, "verify", outcome, suites=[suite.as_json() for suite in suites])
    return Verified(_result(suites), suites)


def suite_line(suite: SuiteResult) -> str:
    if suite.status == SKIPPED:
        return f"{suite.name}: skipped (--backend-only)"
    if suite.ok:
        counts = (
            f" ({suite.passed} passed, {suite.failed} failed)"
            if suite.passed or suite.failed
            else ""
        )
        return f"{suite.name}: passed{counts}"
    return f"FAIL {suite.name}: {suite.failed} failed, {suite.passed} passed (log: {suite.log})"


def _result(suites: list[SuiteResult]) -> CommandResult:
    counts = {
        status: sum(s.status == status for s in suites) for status in ("passed", FAILED, SKIPPED)
    }
    summary = f"verify: {len(suites)} suites, " + ", ".join(
        f"{n} {status}" for status, n in counts.items()
    )
    lines = []
    for suite in suites:
        lines.append(suite_line(suite))
        lines += [FAILURE_INDENT + failure for failure in suite.failures if not suite.ok]
    exit_code = EXIT_EXTERNAL if counts[FAILED] else EXIT_OK
    return CommandResult(
        "verify", exit_code, summary, lines, data={"suites": [s.as_json() for s in suites]}
    )


def _relative_log(kit: Kit, suite: SuiteResult) -> SuiteResult:
    return replace(suite, log=kit.workspace.relative(Path(suite.log))) if suite.log else suite


def _runner(kit: Kit) -> CommandRunner:
    if kit.runner is None:
        raise KitExternalError("no command runner is configured to run the suites")
    return kit.runner
