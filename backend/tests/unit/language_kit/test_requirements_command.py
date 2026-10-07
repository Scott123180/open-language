"""T046: `requirements` prints the registry as a table."""

import json

from language_kit.cli import EXIT_OK
from language_kit.registry import REQUIREMENTS
from tests.unit.language_kit.conftest import run_kit, snapshot


def test_requirements_lists_every_item_with_producer_and_feature(kit):
    code, output = run_kit(kit, "requirements")

    lines = output.splitlines()
    assert code == EXIT_OK
    assert lines[0] == f"requirements: {len(REQUIREMENTS)} per-language items"
    assert any(line.split()[:3] == ["podcast.sample_line", "agent", "007"] for line in lines)
    assert all(len(line) <= 120 for line in lines)


def test_requirements_shows_each_items_rules(kit):
    _, output = run_kit(kit, "requirements")

    row = next(line for line in output.splitlines() if line.startswith("podcast.sample_line"))
    assert "contains {name} exactly once" in row


def test_requirements_as_json(kit):
    _, output = run_kit(kit, "requirements", "--json")

    items = json.loads(output)["requirements"]
    assert [item["path"] for item in items] == [item.path for item in REQUIREMENTS]
    assert items[0] == {
        "path": "code",
        "destination": "runtime",
        "producer": "derived",
        "needed_by": "006",
        "description": REQUIREMENTS[0].description,
        "rules": [rule.describe() for rule in REQUIREMENTS[0].rules],
    }


def test_requirements_changes_nothing(kit):
    before = snapshot(kit.workspace.root)

    run_kit(kit, "requirements")

    assert snapshot(kit.workspace.root) == before
