"""T062: FR-005. With --dry-run, writing commands change nothing; read-only commands never do."""

import pytest

from tests.unit.language_kit.conftest import (
    CATALOGUED_VOICES,
    install_voices,
    italian_catalogue,
    italian_pack_text,
    make_kit,
    run_kit,
    snapshot,
)
from tests.unit.language_kit.fakes import FakeCommandRunner, FakeVoiceDownloader

DRY_RUNS = [
    ("scaffold", "fr", "--name", "French"),
    ("apply", "it"),
    ("backfill", "--all"),
    ("verify", "--language", "it"),
    ("finish", "it"),
    ("report", "it"),
    ("bench", "de"),
]
READ_ONLY = [("check", "--all"), ("validate", "it"), ("requirements",), ("prereq", "it")]


@pytest.fixture
def kit(workspace, tmp_path):
    install_voices(workspace, *CATALOGUED_VOICES)
    pack = workspace.language_dir("it") / "pack.toml"
    pack.parent.mkdir(parents=True)
    pack.write_text(italian_pack_text(), encoding="utf-8")
    (workspace.language_dir("it") / "run-log.jsonl").write_text(
        '{"at": "t", "command": "prereq", "outcome": "ok"}\n', encoding="utf-8"
    )
    return make_kit(
        workspace,
        voice_catalogue=italian_catalogue(),
        downloader=FakeVoiceDownloader(workspace.voice_dir),
        runner=FakeCommandRunner(),
    )


def _everything(kit) -> dict[str, bytes]:
    return snapshot(kit.workspace.root, kit.workspace.voice_dir)


@pytest.mark.parametrize("argv", DRY_RUNS, ids=lambda argv: argv[0])
def test_a_dry_run_changes_nothing(kit, argv):
    before = _everything(kit)

    run_kit(kit, *argv, "--dry-run")

    assert _everything(kit) == before
    assert kit.runner.calls == [] and kit.downloader.ensured == []


@pytest.mark.parametrize("argv", READ_ONLY, ids=lambda argv: argv[0])
def test_a_read_only_command_changes_nothing(kit, argv):
    before = _everything(kit)

    run_kit(kit, *argv)

    assert _everything(kit) == before
