"""T045: `backfill` writes, per language, a partial pack holding only its failing items."""

import tomllib

import pytest

from language_kit.cli import EXIT_OK
from tests.unit.language_kit.conftest import remove_evaluation, run_kit, snapshot


@pytest.fixture(autouse=True)
def incomplete_spanish(workspace):
    remove_evaluation(workspace, "es")


def _backfill_pack(kit, code: str):
    return kit.workspace.language_dir(code) / "backfill-pack.toml"


def test_backfill_writes_the_missing_items_with_guidance(kit):
    code, output = run_kit(kit, "backfill", "es")

    document = tomllib.loads(_backfill_pack(kit, "es").read_text(encoding="utf-8"))
    assert code == EXIT_OK
    assert set(document) == {"code", "evaluation"}
    assert set(document["evaluation"]) == {"special_letters", "turns", "dictation", "loanwords"}
    assert "# Example (German):" in _backfill_pack(kit, "es").read_text(encoding="utf-8")
    assert (
        "es: 4 items → specs/008-language-onboarding-kit/languages/es/backfill-pack.toml" in output
    )


def test_backfill_ends_with_finish_and_the_pack(kit):
    _, output = run_kit(kit, "backfill", "es")

    pack = kit.workspace.relative(_backfill_pack(kit, "es"))
    assert output.splitlines()[-1] == f"→ next: kit.sh finish es --pack {pack}"


def test_a_complete_language_is_nothing_to_do(kit):
    code, output = run_kit(kit, "backfill", "de")

    assert code == EXIT_OK
    assert "de: nothing-to-do" in output
    assert not _backfill_pack(kit, "de").exists()


def test_all_lists_every_language(kit):
    _, output = run_kit(kit, "backfill", "--all")

    assert output.splitlines()[0] == "backfill: 1 pack written (es), 1 nothing-to-do (de)"


def test_an_existing_backfill_pack_is_never_overwritten(kit):
    pack = _backfill_pack(kit, "es")
    pack.parent.mkdir(parents=True)
    pack.write_text("# my edits\n", encoding="utf-8")

    _, output = run_kit(kit, "backfill", "es")

    assert pack.read_text(encoding="utf-8") == "# my edits\n"
    assert "es: nothing-to-do (backfill-pack.toml exists" in output


def test_a_dry_run_writes_nothing(kit):
    before = snapshot(kit.workspace.root)

    _, output = run_kit(kit, "backfill", "es", "--dry-run")

    assert snapshot(kit.workspace.root) == before
    assert "es: would write 4 items" in output


def test_a_failing_scenario_asks_only_for_that_scenario(kit):
    path = kit.workspace.evaluation_dir / "de.toml"
    text = path.read_text(encoding="utf-8")
    start = text.index("rent-a-car = [")
    path.write_text(text[:start] + text[text.index("]", start) + 2 :], encoding="utf-8")

    run_kit(kit, "backfill", "de")

    document = tomllib.loads(_backfill_pack(kit, "de").read_text(encoding="utf-8"))
    assert document == {"code": "de", "evaluation": {"turns": {"rent-a-car": []}}}
