"""T008: every voice key, for run.sh's downloads (research R6)."""

import subprocess
import sys
from pathlib import Path

from app.language_data import load_language_records, voice_keys

BACKEND = Path(__file__).resolve().parents[3]
USAGE_EXIT = 2


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.language_data", *args],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )


def test_voice_keys_follow_language_order_then_file_order():
    expected = tuple(voice.key for record in load_language_records() for voice in record.voices)

    assert voice_keys() == expected


def test_voice_keys_start_with_spanish_then_german():
    assert voice_keys()[:4] == (
        "es_ES-davefx-medium",
        "es_AR-daniela-high",
        "de_DE-thorsten-medium",
        "de_DE-kerstin-low",
    )


def test_the_command_prints_one_key_per_line():
    result = _run("voice-keys")

    assert result.returncode == 0
    assert tuple(result.stdout.splitlines()) == voice_keys()


def test_an_unknown_subcommand_exits_with_a_usage_error():
    result = _run("voices")

    assert result.returncode == USAGE_EXIT
    assert "voice-keys" in result.stderr
