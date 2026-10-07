"""T063: kit.sh, the skill's wrapper: refuses without the venv, else passes its arguments through."""

import shutil
import subprocess
from pathlib import Path

from language_kit.cli import EXIT_OK, EXIT_USAGE

REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPT = REPOSITORY / ".claude" / "skills" / "language-kit" / "kit.sh"


def test_without_the_venv_it_exits_two_and_says_how_to_set_up(tmp_path):
    copy = tmp_path / ".claude" / "skills" / "language-kit" / "kit.sh"
    copy.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, copy)
    (tmp_path / "backend").mkdir()

    result = subprocess.run(
        [str(copy), "requirements"], capture_output=True, text=True, check=False
    )

    assert result.returncode == EXIT_USAGE
    assert "backend/.venv is missing: run ./run.sh --setup" in result.stdout + result.stderr


def test_with_the_venv_it_runs_the_kit(tmp_path):
    result = subprocess.run(
        [str(SCRIPT), "requirements"], capture_output=True, text=True, check=False, cwd=tmp_path
    )

    assert result.returncode == EXIT_OK
    assert result.stdout.startswith("requirements: ")


def test_the_script_is_executable():
    assert SCRIPT.stat().st_mode & 0o111
