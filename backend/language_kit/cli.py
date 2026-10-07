"""The kit's command line: parse, dispatch to a command, print its result, return its exit code."""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn, TextIO

from language_kit.commands.apply import ApplyCommand
from language_kit.commands.backfill import BackfillCommand
from language_kit.commands.base import Command
from language_kit.commands.bench import BenchCommand
from language_kit.commands.check import CheckCommand
from language_kit.commands.finish import FinishCommand
from language_kit.commands.prereq import PrereqCommand
from language_kit.commands.report import ReportCommand
from language_kit.commands.requirements import RequirementsCommand
from language_kit.commands.scaffold import ScaffoldCommand
from language_kit.commands.validate import ValidateCommand
from language_kit.commands.verify import VerifyCommand
from language_kit.composition import Kit, build_kit
from language_kit.errors import KitExternalError, KitUsageError
from language_kit.output import EXIT_EXTERNAL, EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, emit

__all__ = ["COMMANDS", "EXIT_EXTERNAL", "EXIT_FINDINGS", "EXIT_OK", "EXIT_USAGE", "main"]

PROGRAM = "kit.sh"
COMMANDS: tuple[Command, ...] = (
    PrereqCommand(),
    ScaffoldCommand(),
    ValidateCommand(),
    ApplyCommand(),
    VerifyCommand(),
    CheckCommand(),
    BackfillCommand(),
    ReportCommand(),
    FinishCommand(),
    BenchCommand(),
    RequirementsCommand(),
)


class _Parser(argparse.ArgumentParser):
    """Usage errors become one line and exit 2, instead of argparse's usage dump."""

    def error(self, message: str) -> NoReturn:
        raise KitUsageError(message)


def main(argv: list[str] | None = None, kit_factory: Callable[[], Kit] = build_kit) -> int:
    try:
        kit = kit_factory()
    except KitUsageError as error:
        return _usage_error(sys.stdout, error)
    try:
        return _run(_parser(), kit, sys.argv[1:] if argv is None else argv)
    except KitUsageError as error:
        return _usage_error(kit.out, error)
    except KitExternalError as error:
        kit.out.write(f"{PROGRAM}: {error}\n")
        return EXIT_EXTERNAL


def _run(parser: argparse.ArgumentParser, kit: Kit, argv: list[str]) -> int:
    try:
        arguments = parser.parse_args(argv)
    except SystemExit:  # only --help gets here: usage errors raise KitUsageError
        return EXIT_OK
    if arguments.command is None:
        kit.out.write(parser.format_usage())
        return EXIT_USAGE
    if arguments.out is not None:
        kit = kit.with_output(kit.workspace.resolve(arguments.out))
    command: Command = arguments.handler
    result = command.run(arguments, kit)
    emit(result, kit.out, arguments.json)
    return result.exit_code


def _parser() -> argparse.ArgumentParser:
    common = _Parser(add_help=False)
    common.add_argument(
        "--dry-run", action="store_true", help="report what would change; change nothing"
    )
    common.add_argument("--json", action="store_true", help="one JSON document instead of text")
    common.add_argument("--out", type=Path, help="the per-language output root")
    parser = _Parser(prog=PROGRAM, description="The language onboarding kit.")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>", parser_class=_Parser)
    for command in COMMANDS:
        sub = subparsers.add_parser(command.name, help=command.help, parents=[common])
        command.add_arguments(sub)
        sub.set_defaults(handler=command)
    return parser


def _usage_error(out: TextIO, error: KitUsageError) -> int:
    out.write(f"{PROGRAM}: {error} (see {PROGRAM} --help)\n")
    return EXIT_USAGE
