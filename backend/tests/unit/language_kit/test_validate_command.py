"""T044: `validate` parses a pack, merges it onto the language's data and prints every finding."""

from language_kit.cli import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE
from tests.unit.language_kit.conftest import (
    italian_pack_document,
    italian_pack_text,
    run_kit,
    snapshot,
)


def _write_pack(kit, text: str, name: str = "pack.toml"):
    path = kit.workspace.language_dir("it") / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_pack_is_valid_and_points_to_finish(kit):
    _write_pack(kit, italian_pack_text())

    code, output = run_kit(kit, "validate", "it")

    assert code == EXIT_OK
    assert output.splitlines()[0] == "validate it: 0 errors, 0 warnings"
    assert output.splitlines()[-1] == "→ next: kit.sh finish it"


def test_warnings_alone_exit_zero(kit):
    voices = [{"key": "it_IT-paola-medium", "gender": "female"}]
    podcast = italian_pack_document()["podcast"] | {
        "host_names": {"female": italian_pack_document()["podcast"]["host_names"]["female"]}
    }
    _write_pack(kit, italian_pack_text(voices=voices, podcast=podcast))

    code, output = run_kit(kit, "validate", "it")

    assert code == EXIT_OK
    assert "WARN it voices" in output


def test_errors_exit_one_and_are_all_printed(kit):
    _write_pack(kit, italian_pack_text(name="", default_voice="TODO"))

    code, output = run_kit(kit, "validate", "it")

    assert code == EXIT_FINDINGS
    assert output.splitlines()[0] == "validate it: 2 errors, 0 warnings"
    assert {line.split()[2] for line in output.splitlines() if line.startswith("FAIL")} == {
        "name:",
        "default_voice:",
    }
    assert (
        output.splitlines()[-1] == "→ next: fix the FAIL lines in the pack, then kit.sh validate it"
    )


def test_another_pack_path_can_be_given(kit, tmp_path):
    path = tmp_path / "other.toml"
    path.write_text(italian_pack_text(), encoding="utf-8")

    code, output = run_kit(kit, "validate", "it", "--pack", str(path))

    assert code == EXIT_OK
    assert output.splitlines()[-1] == f"→ next: kit.sh finish it --pack {path}"


def test_a_partial_pack_is_merged_onto_the_catalogued_language(kit, tmp_path):
    path = tmp_path / "de-pack.toml"
    path.write_text(
        'code = "de"\n[podcast]\nsample_line = "Servus, ich bin {name}!"\n', encoding="utf-8"
    )

    assert run_kit(kit, "validate", "de", "--pack", str(path))[0] == EXIT_OK


def test_validate_changes_nothing(kit):
    _write_pack(kit, italian_pack_text(name=""))
    before = snapshot(kit.workspace.root)

    run_kit(kit, "validate", "it")

    assert snapshot(kit.workspace.root) == before


def test_a_missing_pack_points_to_scaffold(kit):
    code, output = run_kit(kit, "validate", "it")

    assert code == EXIT_USAGE
    assert "kit.sh scaffold it --name <Name>" in output
