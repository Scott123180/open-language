"""`requirements`: read-only; the registry as a table, for feature authors and agents."""

import argparse

from language_kit.commands.base import Command
from language_kit.composition import Kit
from language_kit.findings import shortened
from language_kit.output import EXIT_OK, CommandResult
from language_kit.registry import Requirement


class RequirementsCommand(Command):
    name = "requirements"
    help = "read-only: list every per-language requirement and its rules"

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        items = kit.requirements
        rows = [_row(item) for item in items]
        summary = f"requirements: {len(items)} per-language items"
        return CommandResult(
            "requirements",
            EXIT_OK,
            summary,
            rows,
            data={"requirements": [_as_json(i) for i in items]},
        )


def _row(item: Requirement) -> str:
    rules = "; ".join(rule.describe() for rule in item.rules)
    return shortened(f"{item.path:<27} {item.producer.value:<7} {item.needed_by:<4} {rules}")


def _as_json(item: Requirement) -> dict[str, object]:
    return {
        "path": item.path,
        "destination": item.destination.value,
        "producer": item.producer.value,
        "needed_by": item.needed_by,
        "description": item.description,
        "rules": [rule.describe() for rule in item.rules],
    }
