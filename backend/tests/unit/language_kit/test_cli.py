"""T037: the command line: usage errors, help and dispatch."""

import subprocess
import sys
from pathlib import Path

from language_kit.cli import COMMANDS, EXIT_OK, EXIT_USAGE, main
from tests.unit.language_kit.conftest import run_kit

BACKEND = Path(__file__).resolve().parents[3]


def test_an_unknown_command_is_a_one_line_usage_error(kit):
    code, output = run_kit(kit, "onboard", "it")

    assert code == EXIT_USAGE
    assert len(output.strip().splitlines()) == 1
    assert "onboard" in output


def test_a_bad_option_is_a_usage_error(kit):
    assert run_kit(kit, "check", "--everything")[0] == EXIT_USAGE


def test_help_lists_every_command(kit, capsys):
    code = main(["--help"], kit_factory=lambda: kit)

    assert code == EXIT_OK
    help_text = capsys.readouterr().out
    assert all(command.name in help_text for command in COMMANDS)


def test_no_command_prints_usage_and_exits_two(kit):
    code, output = run_kit(kit)

    assert code == EXIT_USAGE
    assert "usage" in output


def test_the_module_runs_as_a_program():
    result = subprocess.run(
        [sys.executable, "-m", "language_kit"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == EXIT_USAGE
    assert "usage" in result.stdout


def test_a_kit_that_cannot_be_built_is_a_usage_error(capsys):
    from language_kit.workspace import KitUsageError

    def no_repository():
        raise KitUsageError("no repository found")

    assert main(["check", "de"], kit_factory=no_repository) == EXIT_USAGE
    assert "no repository found" in capsys.readouterr().out


def test_out_moves_the_output_root(kit, tmp_path, monkeypatch):
    seen = []
    original = type(kit).with_output
    monkeypatch.setattr(
        type(kit), "with_output", lambda self, out: seen.append(out) or original(self, out)
    )

    run_kit(kit, "check", "de", "--out", str(tmp_path))

    assert seen == [tmp_path]


def test_a_pack_path_relative_to_the_root_is_found(kit):
    pack = kit.workspace.root / "specs" / "it-pack.toml"
    pack.parent.mkdir(parents=True, exist_ok=True)
    pack.write_text('code = "it"\n', encoding="utf-8")

    _, output = run_kit(kit, "validate", "it", "--pack", "specs/it-pack.toml")

    assert output.startswith("validate it: ")
