"""T059: the run log: one JSON line per acting command in `<out>/<code>/run-log.jsonl` (R11).

Read-only commands (prereq, validate, check, requirements) never write it, so they leave
`git status` unchanged (quickstart §4); `scaffold` records its prerequisite check and `finish`
records its apply, verify and check steps. A dry run writes no line.
"""

import json

import pytest

from language_kit.run_log import RunLog, RunLogEntry
from tests.unit.language_kit.conftest import (
    CATALOGUED_VOICES,
    install_voices,
    italian_catalogue,
    italian_pack_text,
    make_kit,
    remove_evaluation,
    run_kit,
)
from tests.unit.language_kit.fakes import FakeCommandRunner, FakeVoiceDownloader


@pytest.fixture
def kit(workspace):
    install_voices(workspace, *CATALOGUED_VOICES)
    return make_kit(
        workspace,
        voice_catalogue=italian_catalogue(),
        downloader=FakeVoiceDownloader(workspace.voice_dir),
        runner=FakeCommandRunner(),
    )


def _entries(kit, code: str) -> list[dict]:
    path = kit.workspace.language_dir(code) / "run-log.jsonl"
    return (
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if path.exists()
        else []
    )


def _write_pack(kit) -> None:
    path = kit.workspace.language_dir("it") / "pack.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(italian_pack_text(), encoding="utf-8")


def test_scaffold_records_the_prerequisite_check_and_itself(kit):
    run_kit(kit, "scaffold", "it", "--name", "Italian")

    entries = _entries(kit, "it")
    assert [(e["command"], e["outcome"]) for e in entries] == [("prereq", "ok"), ("scaffold", "ok")]
    assert entries[1]["files_written"] == [
        "specs/008-language-onboarding-kit/languages/it/pack.toml"
    ]


def test_an_entry_has_every_field(kit):
    run_kit(kit, "scaffold", "it", "--name", "Italian")

    entry = _entries(kit, "it")[0]
    assert set(entry) == {
        "at",
        "command",
        "outcome",
        "findings",
        "files_written",
        "voices_downloaded",
        "download_seconds",
        "suites",
        "benchmarks",
    }
    assert entry["at"] == "2026-10-06T12:00:00+00:00"


def test_apply_records_files_and_voices(kit):
    _write_pack(kit)

    run_kit(kit, "apply", "it")

    (entry,) = _entries(kit, "it")
    assert entry["command"] == "apply" and entry["outcome"] == "ok"
    assert entry["files_written"] == [
        "backend/app/language_data/languages/it.toml",
        "backend/tests/integration/practice_languages/evaluation/it.toml",
    ]
    assert entry["voices_downloaded"] == ["it_IT-paola-medium", "it_IT-riccardo-x_low"]
    assert entry["download_seconds"] == 3.0


def test_apply_records_the_warnings_of_the_pack(kit):
    path = kit.workspace.language_dir("it") / "pack.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        italian_pack_text(
            voices=[{"key": "it_IT-paola-medium", "gender": "female"}],
            podcast=_one_gender_podcast(),
        ),
        encoding="utf-8",
    )

    run_kit(kit, "apply", "it")

    (entry,) = _entries(kit, "it")
    assert entry["outcome"] == "ok"
    assert {finding["severity"] for finding in entry["findings"]} == {"warning"}


def test_a_rejected_pack_writes_no_line(kit):
    path = kit.workspace.language_dir("it") / "pack.toml"
    path.parent.mkdir(parents=True)
    path.write_text(italian_pack_text(name=""), encoding="utf-8")

    run_kit(kit, "apply", "it")

    assert _entries(kit, "it") == []


def _one_gender_podcast() -> dict:
    from tests.unit.language_kit.conftest import italian_pack_document

    podcast = italian_pack_document()["podcast"]
    return podcast | {"host_names": {"female": podcast["host_names"]["female"]}}


def test_verify_with_a_language_records_its_suites(kit):
    run_kit(kit, "verify", "--language", "it", "--backend-only")

    (entry,) = _entries(kit, "it")
    assert entry["command"] == "verify"
    assert entry["suites"][0] == {
        "name": "pytest",
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "status": "passed",
        "log": "specs/008-language-onboarding-kit/languages/it/logs/pytest.log",
    }
    assert entry["suites"][-1]["status"] == "skipped"


def test_backfill_records_the_pack_it_wrote(kit):
    remove_evaluation(kit.workspace, "es")
    run_kit(kit, "backfill", "es")

    (entry,) = _entries(kit, "es")
    assert entry["command"] == "backfill"
    assert entry["files_written"] == [
        "specs/008-language-onboarding-kit/languages/es/backfill-pack.toml"
    ]


@pytest.mark.parametrize(
    "argv", [("check", "es"), ("validate", "it"), ("prereq", "it"), ("requirements",)]
)
def test_read_only_commands_write_no_line(kit, argv):
    _write_pack(kit)

    run_kit(kit, *argv)

    assert _entries(kit, "it") == [] and _entries(kit, "es") == []


def test_a_dry_run_writes_no_line(kit):
    _write_pack(kit)

    run_kit(kit, "apply", "it", "--dry-run")
    run_kit(kit, "scaffold", "fr", "--name", "French", "--dry-run")

    assert _entries(kit, "it") == [] and _entries(kit, "fr") == []


def test_entries_read_back_in_order(workspace):
    log = RunLog(workspace)
    log.append("it", RunLogEntry(at="t1", command="prereq", outcome="ok"))
    log.append("it", RunLogEntry(at="t2", command="scaffold", outcome="ok"))

    assert [entry.command for entry in log.read("it")] == ["prereq", "scaffold"]


def test_a_language_with_no_log_reads_as_empty(workspace):
    assert RunLog(workspace).read("it") == []
