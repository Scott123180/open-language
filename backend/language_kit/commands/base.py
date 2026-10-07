"""The interface every kit command implements."""

import argparse
from abc import ABC, abstractmethod
from typing import ClassVar

from language_kit.composition import Kit
from language_kit.output import CommandResult


class Command(ABC):
    name: ClassVar[str]
    help: ClassVar[str]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:  # noqa: B027
        """Declare the command's own arguments; the common options are added for it."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult: ...


def add_code_or_all(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("code", nargs="?", help="a catalogued language code")
    parser.add_argument("--all", action="store_true", help="every catalogued language")
