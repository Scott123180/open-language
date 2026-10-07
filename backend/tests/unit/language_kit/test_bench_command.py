"""T085: `bench <code>` runs the language-independent benchmarks and reports each figure (R8)."""

import json

import pytest

from language_kit.cli import EXIT_EXTERNAL, EXIT_FINDINGS, EXIT_OK, EXIT_USAGE
from tests.unit.language_kit.conftest import (
    CATALOGUED_VOICES,
    fake_context,
    install_voices,
    make_kit,
    run_kit,
    snapshot,
)
from tests.unit.language_kit.fakes import FakeBenchProbe, FakeCommandRunner

ADHERENCE = {
    "kind": "adherence",
    "language": "de",
    "voice": None,
    "model": "llama3.1:8b",
    "passed": 48,
    "total": 50,
    "threshold": "≥ 95%",
    "met": True,
    "not_run_reason": None,
    "results_file": "specs/008-language-onboarding-kit/languages/de/benchmark-results.md",
    "review_sheet": "specs/008-language-onboarding-kit/languages/de/review-sheet.md",
}
THORSTEN = ADHERENCE | {"kind": "transcription", "voice": "de_DE-thorsten-medium", "model": "base", "passed": 19, "total": 20, "threshold": "≥ 18/20", "review_sheet": None}  # fmt: skip
KERSTIN = THORSTEN | {"voice": "de_DE-kerstin-low", "passed": 15, "met": False}


class BenchmarkRunner(FakeCommandRunner):
    """Writes benchmark-results.json where the benchmarks would, from scripted results."""

    def __init__(self, results: list[dict], exit_code: int = 0) -> None:
        super().__init__({"bench": (exit_code, "benchmark output")})
        self._results = results

    def run(self, argv, cwd, log, environment=None):
        out = environment["OPEN_LANGUAGE_BENCH_OUT"]
        from pathlib import Path

        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "benchmark-results.json").write_text(
            json.dumps({"results": self._results}), encoding="utf-8"
        )
        return super().run(argv, cwd, log, environment)


def _kit(workspace, results=(ADHERENCE, THORSTEN), exit_code=0, probe=None, context=None):
    install_voices(workspace, *CATALOGUED_VOICES)
    runner = BenchmarkRunner(list(results), exit_code)
    return make_kit(
        workspace,
        runner=runner,
        bench_probe=probe or FakeBenchProbe(),
        context=context or fake_context(),
    )


def test_bench_runs_both_benchmarks_with_the_language_and_output(workspace):
    kit = _kit(workspace)

    run_kit(kit, "bench", "de")

    (_, argv, cwd, _), environment = kit.runner.calls[0], kit.runner.environments[0]
    assert argv[:4] == [".venv/bin/pytest", "-m", "benchmark", "-s"]
    assert [a.rsplit("/", 1)[-1] for a in argv[4:]] == [
        "test_adherence_benchmark.py",
        "test_transcription_benchmark.py",
    ]
    assert cwd == kit.workspace.root / "backend"
    assert environment == {
        "OPEN_LANGUAGE_BENCH_LANGUAGE": "de",
        "OPEN_LANGUAGE_BENCH_OUT": str(kit.workspace.language_dir("de")),
    }


@pytest.mark.parametrize(("option", "file"), [("--adherence", "test_adherence_benchmark.py"), ("--transcription", "test_transcription_benchmark.py")])  # fmt: skip
def test_one_benchmark_can_be_chosen(workspace, option, file):
    kit = _kit(workspace, results=(ADHERENCE,) if option == "--adherence" else (THORSTEN,))

    run_kit(kit, "bench", "de", option)

    assert [a.rsplit("/", 1)[-1] for a in kit.runner.calls[0][1][4:]] == [file]


def test_each_figure_is_printed_against_its_threshold_with_the_files(workspace):
    code, output = run_kit(_kit(workspace), "bench", "de")

    assert code == EXIT_OK
    assert "adherence (llama3.1:8b): 48/50 against ≥ 95%: met" in output
    assert "transcription, de_DE-thorsten-medium (base): 19/20 against ≥ 18/20: met" in output
    assert "results: specs/008-language-onboarding-kit/languages/de/benchmark-results.md" in output
    assert "review sheet: specs/008-language-onboarding-kit/languages/de/review-sheet.md" in output


def test_a_missed_threshold_exits_one(workspace):
    code, output = run_kit(
        _kit(workspace, results=(ADHERENCE, THORSTEN, KERSTIN), exit_code=1), "bench", "de"
    )

    assert code == EXIT_FINDINGS
    assert "transcription, de_DE-kerstin-low (base): 15/20 against ≥ 18/20: missed" in output


def test_without_ollama_adherence_exits_three_names_it_and_writes_nothing(workspace):
    kit = _kit(
        workspace,
        probe=FakeBenchProbe(ollama_problem="Ollama is not running at http://localhost:11434"),
    )
    before = snapshot(kit.workspace.root)

    code, output = run_kit(kit, "bench", "de", "--adherence")

    assert code == EXIT_EXTERNAL
    assert "Ollama" in output
    assert kit.runner.calls == [] and snapshot(kit.workspace.root) == before


def test_a_missing_voice_stops_transcription_and_says_how_to_get_it(workspace):
    kit = _kit(workspace)
    (kit.workspace.voice_dir / "de_DE-kerstin-low.onnx").unlink()

    code, output = run_kit(kit, "bench", "de", "--transcription")

    assert code == EXIT_EXTERNAL
    assert "de_DE-kerstin-low" in output and "./run.sh --setup" in output


def test_a_language_wordfreq_lacks_gets_adherence_not_run(workspace):
    kit = _kit(
        workspace, results=(THORSTEN,), context=fake_context(wordfreq_codes=frozenset({"en"}))
    )

    code, output = run_kit(kit, "bench", "de")

    assert code == EXIT_OK
    assert "adherence: not run (wordfreq has no de" in output
    assert [a.rsplit("/", 1)[-1] for a in kit.runner.calls[0][1][4:]] == [
        "test_transcription_benchmark.py"
    ]


def test_results_are_recorded_in_the_run_log(workspace):
    kit = _kit(workspace)

    run_kit(kit, "bench", "de")

    log = kit.workspace.language_dir("de") / "run-log.jsonl"
    (entry,) = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert entry["command"] == "bench" and entry["outcome"] == "ok"
    assert [result["kind"] for result in entry["benchmarks"]] == ["adherence", "transcription"]


def test_a_crashed_run_without_results_is_an_external_failure(workspace):
    kit = _kit(workspace, results=(), exit_code=2)

    code, output = run_kit(kit, "bench", "de")

    assert code == EXIT_EXTERNAL
    assert "logs/bench.log" in output


def test_a_dry_run_writes_nothing(workspace):
    kit = _kit(workspace)
    before = snapshot(kit.workspace.root)

    code, output = run_kit(kit, "bench", "de", "--dry-run")

    assert code == EXIT_OK and kit.runner.calls == []
    assert "would run pytest -m benchmark" in output
    assert snapshot(kit.workspace.root) == before


def test_an_uncatalogued_language_is_a_usage_error(workspace):
    assert run_kit(_kit(workspace), "bench", "it")[0] == EXIT_USAGE
