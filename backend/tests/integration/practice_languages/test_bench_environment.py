"""T084: the plumbing the language-independent benchmarks share. Runs in CI."""

import json
from pathlib import Path

import pytest

from tests.integration.practice_languages.bench_environment import (
    LANGUAGE_VARIABLE,
    OUTPUT_VARIABLE,
    REPOSITORY,
    RESULTS_JSON,
    RESULTS_MARKDOWN,
    REVIEW_SHEET,
    BenchmarkResult,
    bench_languages,
    bench_output_dir,
    record_benchmark,
    write_review_sheet,
)
from tests.integration.practice_languages.evaluation_set import evaluated_languages


def _adherence(**changes) -> BenchmarkResult:
    fields = {
        "kind": "adherence",
        "language": "de",
        "voice": None,
        "model": "llama3.1:8b",
        "passed": 48,
        "total": 50,
        "threshold": "≥ 95%",
        "met": True,
    }
    return BenchmarkResult(**(fields | changes))


def test_languages_default_to_every_evaluated_language(monkeypatch):
    monkeypatch.delenv(LANGUAGE_VARIABLE, raising=False)

    assert bench_languages() == evaluated_languages()


def test_the_language_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv(LANGUAGE_VARIABLE, "de")

    assert bench_languages() == ("de",)


def test_the_output_defaults_to_the_feature_languages_folder(monkeypatch):
    monkeypatch.delenv(OUTPUT_VARIABLE, raising=False)
    feature = json.loads((REPOSITORY / ".specify/feature.json").read_text(encoding="utf-8"))

    assert bench_output_dir("de") == REPOSITORY / feature["feature_directory"] / "languages" / "de"


def test_the_output_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(OUTPUT_VARIABLE, str(tmp_path))

    assert bench_output_dir("de") == tmp_path


def test_a_result_is_written_as_markdown_and_json(tmp_path):
    record_benchmark(tmp_path, _adherence(), "## Adherence\n\n48/50 clean replies.\n")

    stored = json.loads((tmp_path / RESULTS_JSON).read_text(encoding="utf-8"))
    assert stored["results"] == [
        _adherence().as_json() | {"results_file": str(tmp_path / RESULTS_MARKDOWN)}
    ]
    assert set(stored["results"][0]) == {
        "kind", "language", "voice", "model", "passed", "total", "threshold",
        "met", "not_run_reason", "results_file", "review_sheet",
    }  # fmt: skip
    assert "48/50 clean replies." in (tmp_path / RESULTS_MARKDOWN).read_text(encoding="utf-8")


def test_one_table_per_voice_and_reruns_replace_their_own_section(tmp_path):
    record_benchmark(tmp_path, _adherence(), "## Adherence\n\nfirst\n")
    paola = _adherence(kind="transcription", voice="it_IT-paola-medium", threshold="≥ 18/20")
    record_benchmark(tmp_path, paola, "## Transcription: it_IT-paola-medium\n\n| # |\n")
    record_benchmark(tmp_path, _adherence(passed=49), "## Adherence\n\nsecond\n")

    markdown = (tmp_path / RESULTS_MARKDOWN).read_text(encoding="utf-8")
    stored = json.loads((tmp_path / RESULTS_JSON).read_text(encoding="utf-8"))["results"]
    assert "second" in markdown and "first" not in markdown
    assert "## Transcription: it_IT-paola-medium" in markdown
    assert [(r["kind"], r["passed"]) for r in stored] == [("adherence", 49), ("transcription", 48)]


def test_a_result_names_its_files(tmp_path):
    record_benchmark(tmp_path, _adherence(), "x\n")

    (stored,) = json.loads((tmp_path / RESULTS_JSON).read_text(encoding="utf-8"))["results"]
    assert stored["results_file"].endswith(RESULTS_MARKDOWN)


def test_the_review_sheet_names_the_language_and_the_others(tmp_path):
    path = write_review_sheet(
        tmp_path, "de", ("en", "es"), [("rent-a-car", "Hallo", "the car", "the")]
    )

    text = path.read_text(encoding="utf-8")
    assert path.name == REVIEW_SHEET
    assert text.startswith("# German review sheet")
    assert "English or Spanish" in text
    assert "| Scenario | Learner | Reply | Flagged words | Verdict |" in text
    assert text.rstrip().endswith("| rent-a-car | Hallo | the car | the |  |")


@pytest.mark.parametrize("cell", ["a|b", "line\nbreak"])
def test_review_cells_are_escaped(tmp_path, cell):
    text = write_review_sheet(tmp_path, "de", ("en",), [(cell, "l", "r", "w")]).read_text(
        encoding="utf-8"
    )

    assert "a\\|b" in text or "line break" in text


def test_the_markdown_starts_with_a_language_header(tmp_path):
    record_benchmark(tmp_path, _adherence(), "x\n")

    assert (
        (tmp_path / RESULTS_MARKDOWN)
        .read_text(encoding="utf-8")
        .startswith("# Benchmark results: German (de)")
    )


def test_paths_outside_the_repository_are_kept_absolute(tmp_path):
    record_benchmark(tmp_path, _adherence(), "x\n")

    (stored,) = json.loads((tmp_path / RESULTS_JSON).read_text(encoding="utf-8"))["results"]
    assert Path(stored["results_file"]).is_absolute()
