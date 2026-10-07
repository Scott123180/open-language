"""T058: `verify` runs every suite in its own directory and prints one line per suite (R10)."""

import pytest

from language_kit.cli import EXIT_EXTERNAL, EXIT_OK
from language_kit.verify import MAX_FAILURE_IDS, SubprocessCommandRunner, summarise
from tests.unit.language_kit.conftest import make_kit, run_kit, snapshot
from tests.unit.language_kit.fakes import FakeCommandRunner

PYTEST_PASS = "2201 passed, 35 deselected in 180.2s"
EXPECTED = [
    ("pytest", ".venv/bin/pytest", "backend"),
    ("ruff", ".venv/bin/ruff check .", "backend"),
    ("black", ".venv/bin/black --check .", "backend"),
    ("mypy", ".venv/bin/mypy language_kit app/language_data", "backend"),
    ("eslint", "npm run lint", "frontend"),
    ("vitest", "npm test -- --run", "frontend"),
    ("playwright", "npm run test:e2e", "frontend"),
]


@pytest.fixture
def runner():
    return FakeCommandRunner({"pytest": (0, PYTEST_PASS)})


@pytest.fixture
def kit(workspace, runner):
    return make_kit(workspace, runner=runner)


def test_every_suite_runs_with_its_command_in_its_directory(kit, runner):
    run_kit(kit, "verify")

    root = kit.workspace.root
    assert [(name, " ".join(argv), cwd) for name, argv, cwd, _ in runner.calls] == [
        (name, command, root / directory) for name, command, directory in EXPECTED
    ]


def test_passing_suites_give_one_line_each_and_exit_zero(kit):
    code, output = run_kit(kit, "verify")

    lines = output.splitlines()
    assert code == EXIT_OK
    assert lines[0] == "verify: 7 suites, 7 passed, 0 failed, 0 skipped"
    assert "pytest: passed (2201 passed, 0 failed)" in lines


def test_a_failing_suite_lists_its_test_ids_and_log_and_exits_three(workspace):
    failures = "\n".join(
        f"FAILED tests/unit/test_x.py::test_{n} - AssertionError" for n in range(25)
    )
    runner = FakeCommandRunner({"pytest": (1, f"{failures}\n25 failed, 2176 passed in 170s")})
    kit = make_kit(workspace, runner=runner)

    code, output = run_kit(kit, "verify")

    assert code == EXIT_EXTERNAL
    assert any(
        line.startswith("FAIL pytest: 25 failed, 2176 passed (log: ")
        for line in output.splitlines()
    )
    assert (
        sum("tests/unit/test_x.py::test_" in line for line in output.splitlines())
        == MAX_FAILURE_IDS
    )


def test_logs_go_under_the_language_with_language(kit, runner):
    run_kit(kit, "verify", "--language", "it")

    logs = {log for _, _, _, log in runner.calls}
    assert logs == {
        kit.workspace.language_dir("it") / "logs" / f"{name}.log" for name, _, _ in EXPECTED
    }


def test_logs_go_under_logs_without_a_language(kit, runner):
    run_kit(kit, "verify")

    assert {log.parent for _, _, _, log in runner.calls} == {kit.workspace.output_root / "_logs"}


def test_backend_only_skips_the_frontend_suites_and_says_so(kit, runner):
    _, output = run_kit(kit, "verify", "--backend-only")

    assert [name for name, *_ in runner.calls] == ["pytest", "ruff", "black", "mypy"]
    assert "verify: 7 suites, 4 passed, 0 failed, 3 skipped" in output
    assert "eslint: skipped (--backend-only)" in output


def test_a_dry_run_runs_nothing_and_writes_no_log(kit, runner):
    before = snapshot(kit.workspace.root)

    code, output = run_kit(kit, "verify", "--dry-run")

    assert code == EXIT_OK and runner.calls == []
    assert "would run pytest (in backend)" in output
    assert snapshot(kit.workspace.root) == before


@pytest.mark.parametrize(
    ("name", "text", "counts"),
    [
        ("pytest", "3 failed, 10 passed, 2 skipped in 1s", (10, 3, 2)),
        ("vitest", " Tests  290 passed (290)\n", (290, 0, 0)),
        ("vitest", " Tests  2 failed | 288 passed (290)\n", (288, 2, 0)),
        ("playwright", "  120 passed (1.2m)\n", (120, 0, 0)),
        ("playwright", "  1 failed\n  119 passed (1.2m)\n", (119, 1, 0)),
        ("ruff", "All checks passed!", (0, 0, 0)),
    ],
)
def test_summaries_read_each_runners_counts(name, text, counts):
    result = summarise(name, 0, text)

    assert (result.passed, result.failed, result.skipped) == counts


def test_a_non_zero_exit_is_a_failure_even_without_counts():
    assert not summarise("ruff", 1, "E501 line too long").ok


def test_the_subprocess_runner_captures_output_and_exit_code(tmp_path):
    log = tmp_path / "logs" / "echo.log"

    run = SubprocessCommandRunner().run(["python3", "-c", "print('3 passed')"], tmp_path, log)

    assert run.exit_code == 0 and "3 passed" in run.output
    assert log.read_text(encoding="utf-8") == run.output


def test_a_missing_program_is_a_failed_run(tmp_path):
    run = SubprocessCommandRunner().run(["no-such-program-xyz"], tmp_path, tmp_path / "x.log")

    assert run.exit_code != 0 and "no-such-program-xyz" in run.output


def test_terminal_escape_codes_do_not_hide_the_counts():
    output = "\x1b[2m[WebServer] \x1b[22mstarting\n\x1b[1A\x1b[2K  285 passed (20.7s)\n"

    assert summarise("playwright", 0, output).passed == 285


def test_a_suite_without_counts_reads_as_just_passed():
    from language_kit.commands.verify import suite_line

    assert suite_line(summarise("ruff", 0, "All checks passed!")) == "ruff: passed"
