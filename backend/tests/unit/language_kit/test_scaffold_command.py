"""T057: `scaffold` runs prereq, then writes the pack from the template with the candidate voices."""

import tomllib

import pytest

from language_kit.cli import EXIT_OK, EXIT_USAGE
from tests.unit.language_kit.conftest import italian_catalogue, make_kit, run_kit, snapshot


@pytest.fixture
def kit(workspace):
    return make_kit(workspace, voice_catalogue=italian_catalogue())


def _pack(kit):
    return kit.workspace.language_dir("it") / "pack.toml"


def test_scaffold_writes_the_pack_with_the_candidates(kit):
    code, output = run_kit(kit, "scaffold", "it", "--name", "Italian")

    text = _pack(kit).read_text(encoding="utf-8")
    assert code == EXIT_OK
    assert tomllib.loads(text)["name"] == "Italian"
    assert "it_IT-riccardo-x_low" in text
    assert (
        output.splitlines()[0]
        == "scaffold it: wrote specs/008-language-onboarding-kit/languages/it/pack.toml"
    )
    assert output.splitlines()[-1] == "→ next: kit.sh validate it"


def test_a_failing_prerequisite_writes_nothing(kit):
    before = snapshot(kit.workspace.root)

    code, _ = run_kit(kit, "scaffold", "de", "--name", "German")

    assert code == EXIT_USAGE
    assert snapshot(kit.workspace.root) == before


def test_an_existing_pack_is_never_overwritten(kit):
    _pack(kit).parent.mkdir(parents=True)
    _pack(kit).write_text("# my work\n", encoding="utf-8")

    code, output = run_kit(kit, "scaffold", "it", "--name", "Italian")

    assert code == EXIT_OK
    assert output.startswith("scaffold it: nothing-to-do")
    assert _pack(kit).read_text(encoding="utf-8") == "# my work\n"


def test_the_name_is_required(kit):
    assert run_kit(kit, "scaffold", "it")[0] == EXIT_USAGE


def test_a_dry_run_writes_nothing(kit):
    before = snapshot(kit.workspace.root)

    code, output = run_kit(kit, "scaffold", "it", "--name", "Italian", "--dry-run")

    assert code == EXIT_OK
    assert output.startswith("scaffold it: would write")
    assert snapshot(kit.workspace.root) == before


def test_rerunning_scaffold_after_onboarding_is_nothing_to_do(kit):
    pack = kit.workspace.language_dir("de") / "pack.toml"
    pack.parent.mkdir(parents=True)
    pack.write_text("# filled\n", encoding="utf-8")

    code, output = run_kit(kit, "scaffold", "de", "--name", "German")

    assert code == EXIT_OK
    assert output.startswith("scaffold de: nothing-to-do")
