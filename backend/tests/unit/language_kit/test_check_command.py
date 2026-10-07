"""T029: `check` reports pass or fail per language and requirement, and changes nothing."""

import json

from language_kit.cli import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, main
from tests.unit.language_kit.conftest import make_kit, run_kit, snapshot, write_valid_evaluation


def _break_german_host_names(workspace) -> None:
    path = workspace.runtime_dir / "de.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('    "Lena",\n    "Anna",\n', ""), encoding="utf-8")


def test_check_all_passes_complete_languages(kit):
    write_valid_evaluation(kit.workspace, "es")

    code, output = run_kit(kit, "check", "--all")

    assert code == EXIT_OK
    assert output.splitlines()[0].startswith(
        "check: 2 languages, 14 requirements, 0 failing (es ✓, de ✓)"
    )


def test_check_one_language_passes(kit):
    code, output = run_kit(kit, "check", "de")

    assert code == EXIT_OK
    assert output.startswith("check: 1 language, 14 requirements, 0 failing (de ✓)")


def test_a_failing_item_is_printed_and_marks_the_language(kit):
    _break_german_host_names(kit.workspace)

    code, output = run_kit(kit, "check", "de")

    assert code == EXIT_FINDINGS
    assert "1 failing (de ✗)" in output.splitlines()[0]
    assert output.splitlines()[1].startswith("FAIL de podcast.host_names.female: ")


def test_a_language_without_an_evaluation_set_fails_on_the_evaluation_items(kit):
    code, output = run_kit(kit, "check", "es")

    failing = [
        line.split()[2].rstrip(":") for line in output.splitlines() if line.startswith("FAIL")
    ]
    assert code == EXIT_FINDINGS
    assert failing == [
        "evaluation.special_letters",
        "evaluation.turns",
        "evaluation.dictation",
        "evaluation.loanwords",
    ]


def test_the_summary_reports_installed_voices(kit):
    (kit.workspace.voice_dir / "de_DE-thorsten-medium.onnx").write_bytes(b"x")
    (kit.workspace.voice_dir / "de_DE-thorsten-medium.onnx.json").write_bytes(b"{}")

    _, output = run_kit(kit, "check", "de")

    assert "voices installed: de 1/2" in output.splitlines()[0]


def test_failing_items_end_with_the_next_step(kit):
    _, output = run_kit(kit, "check", "es")

    assert output.splitlines()[-1] == "→ next: kit.sh backfill es"


def test_json_lists_languages_and_findings(kit):
    _break_german_host_names(kit.workspace)

    _, output = run_kit(kit, "check", "de", "--json")
    document = json.loads(output)

    assert document["command"] == "check"
    assert document["languages"] == {"de": False}
    assert document["findings"][0]["path"] == "podcast.host_names.female"


def test_check_changes_no_file(kit):
    before = snapshot(kit.workspace.root, kit.workspace.voice_dir)

    run_kit(kit, "check", "--all")

    assert snapshot(kit.workspace.root, kit.workspace.voice_dir) == before


def test_an_uncatalogued_code_is_a_usage_error(kit):
    code, output = run_kit(kit, "check", "it")

    assert code == EXIT_USAGE
    assert "it" in output


def test_check_needs_a_code_or_all(kit):
    assert run_kit(kit, "check")[0] == EXIT_USAGE


def test_check_de_passes_in_the_real_repository(capsys):
    assert main(["check", "de"]) == EXIT_OK
    assert "0 failing (de ✓)" in capsys.readouterr().out


def test_the_kit_can_be_built_over_another_output_directory(workspace, tmp_path):
    kit = make_kit(workspace).with_output(tmp_path)

    assert kit.workspace.output_root == tmp_path
