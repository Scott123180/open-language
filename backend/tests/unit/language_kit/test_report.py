"""T060: `report` regenerates report.md in full from the run log (R11, FR-027)."""

import pytest

from language_kit.cli import EXIT_OK, EXIT_USAGE
from language_kit.run_log import RunLog, RunLogEntry
from tests.unit.language_kit.conftest import run_kit, snapshot

SECTIONS = ["## Applied", "## Checks", "## Benchmarks", "## Open items", "## Not checked"]
NOT_CHECKED = [
    "Listening to the voices",
    "Voice genders: asserted from the voice's name or model card, not checked by listening",
    "A screen-reader pass",
    "Offline use",
    "A human speaking into the microphone",
]
PYTEST = {
    "name": "pytest",
    "passed": 2200,
    "failed": 0,
    "skipped": 0,
    "status": "passed",
    "log": "logs/pytest.log",
}
ESLINT = {
    "name": "eslint",
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "status": "skipped",
    "log": None,
}
WARNING = {
    "language": "it",
    "path": "voices",
    "severity": "warning",
    "rule": "two or more voices",
    "detail": "Only one voice.",
}
ADHERENCE = {
    "kind": "adherence",
    "language": "it",
    "voice": None,
    "model": "llama3.1:8b",
    "passed": 46,
    "total": 50,
    "threshold": "≥ 95%",
    "met": False,
    "not_run_reason": None,
    "results_file": "specs/x/it/benchmark-results.md",
    "review_sheet": "specs/x/it/review-sheet.md",
}
TRANSCRIPTION = ADHERENCE | {
    "kind": "transcription",
    "voice": "it_IT-paola-medium",
    "model": "small",
    "passed": 19,
    "total": 20,
    "threshold": "≥ 18/20",
    "met": True,
}


@pytest.fixture
def logged(kit):
    log = RunLog(kit.workspace)
    entries = [
        RunLogEntry(at="2026-10-06T12:00:00+00:00", command="prereq", outcome="ok"),
        RunLogEntry(
            at="2026-10-06T12:20:00+00:00",
            command="apply",
            outcome="ok",
            findings=[WARNING],
            files_written=["backend/app/language_data/languages/it.toml"],
            voices_downloaded=["it_IT-paola-medium"],
        ),
        RunLogEntry(
            at="2026-10-06T12:25:00+00:00", command="verify", outcome="ok", suites=[PYTEST, ESLINT]
        ),
        RunLogEntry(at="2026-10-06T12:26:00+00:00", command="check", outcome="ok"),
        RunLogEntry(
            at="2026-10-06T13:00:00+00:00",
            command="bench",
            outcome="findings",
            benchmarks=[ADHERENCE, TRANSCRIPTION],
        ),
    ]
    for entry in entries:
        log.append("it", entry)
    return kit


def _report(kit) -> str:
    return (kit.workspace.language_dir("it") / "report.md").read_text(encoding="utf-8")


def test_the_report_has_a_header_and_the_five_sections_in_order(logged):
    code, output = run_kit(logged, "report", "it")

    text = _report(logged)
    assert code == EXIT_OK
    assert text.startswith("# Onboarding report: it\n")
    assert "2026-10-06T12:00:00+00:00 to 2026-10-06T13:00:00+00:00" in text
    assert "Kit commands run: prereq, apply, verify, check, bench" in text
    assert [text.index(section) for section in SECTIONS] == sorted(text.index(s) for s in SECTIONS)
    assert output.startswith(
        "report it: wrote specs/008-language-onboarding-kit/languages/it/report.md"
    )


def test_applied_lists_files_and_voices(logged):
    run_kit(logged, "report", "it")

    applied = _report(logged).split("## Applied")[1].split("##")[0]
    assert (
        "backend/app/language_data/languages/it.toml" in applied and "it_IT-paola-medium" in applied
    )


def test_checks_state_the_suites_and_a_skipped_frontend_suite(logged):
    run_kit(logged, "report", "it")

    checks = _report(logged).split("## Checks")[1].split("##")[0]
    assert "pytest: passed (2200 passed, 0 failed)" in checks
    assert "eslint: skipped" in checks
    assert "Completeness check: passed" in checks


def test_benchmarks_show_each_figure_against_its_threshold(logged):
    run_kit(logged, "report", "it")

    benchmarks = _report(logged).split("## Benchmarks")[1].split("##")[0]
    assert "adherence (llama3.1:8b): 46/50 against ≥ 95%: missed" in benchmarks
    assert "transcription, it_IT-paola-medium (small): 19/20 against ≥ 18/20: met" in benchmarks


def test_open_items_hold_misses_and_warnings(logged):
    run_kit(logged, "report", "it")

    open_items = _report(logged).split("## Open items")[1].split("##")[0]
    assert "adherence missed" in open_items
    assert "WARN it voices: two or more voices. Only one voice." in open_items


def test_a_benchmark_not_run_says_why(kit):
    not_run = ADHERENCE | {
        "met": None,
        "passed": 0,
        "total": 0,
        "not_run_reason": "wordfreq has no it",
    }
    RunLog(kit.workspace).append(
        "it", RunLogEntry(at="t", command="bench", outcome="ok", benchmarks=[not_run])
    )

    run_kit(kit, "report", "it")

    assert "adherence: not run (wordfreq has no it)" in _report(kit)


def test_without_benchmarks_the_section_says_not_run(kit):
    RunLog(kit.workspace).append("it", RunLogEntry(at="t", command="apply", outcome="ok"))

    run_kit(kit, "report", "it")

    assert "Not run yet: kit.sh bench it" in _report(kit)


def test_not_checked_is_the_fixed_list(logged):
    run_kit(logged, "report", "it")

    not_checked = _report(logged).split("## Not checked")[1]
    assert [line.removeprefix("- ") for line in not_checked.strip().splitlines()] == NOT_CHECKED


def test_review_sheet_rows_without_a_verdict_are_open(logged):
    sheet = logged.workspace.root / "specs/x/it/review-sheet.md"
    sheet.parent.mkdir(parents=True)
    sheet.write_text(
        "| a | b | c | d | Verdict |\n|---|---|---|---|---|\n| s | l | r | the |  |\n| s | l | r | x | ok |\n",
        encoding="utf-8",
    )

    run_kit(logged, "report", "it")

    assert "1 review-sheet row still to judge: specs/x/it/review-sheet.md" in _report(logged)


def test_regenerating_gives_the_same_bytes(logged):
    run_kit(logged, "report", "it")
    first = _report(logged)

    run_kit(logged, "report", "it")

    assert _report(logged) == first


def test_a_dry_run_prints_the_report_without_writing(logged):
    before = snapshot(logged.workspace.root)

    _, output = run_kit(logged, "report", "it", "--dry-run")

    assert "## Not checked" in output
    assert snapshot(logged.workspace.root) == before


def test_a_language_with_no_run_log_has_nothing_to_report(kit):
    assert run_kit(kit, "report", "it")[0] == EXIT_USAGE


def test_a_linter_without_counts_is_reported_as_passed(kit):
    ruff = PYTEST | {"name": "ruff", "passed": 0}
    RunLog(kit.workspace).append("it", RunLogEntry(at="t", command="verify", outcome="ok", suites=[ruff]))

    run_kit(kit, "report", "it")

    assert "- ruff: passed\n" in _report(kit)
