"""What the language-independent benchmarks share: which language, where results go, how (R8).

`kit.sh bench <code>` sets `OPEN_LANGUAGE_BENCH_LANGUAGE` and `OPEN_LANGUAGE_BENCH_OUT`; run by
hand without them, the benchmarks cover every language with an evaluation set and write under the
current feature's `languages/<code>/`. Results are written before any assertion, so a missed
threshold still leaves the evidence (006's form: one adherence figure, one table per voice).
"""

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from app.practice_languages import language_name
from tests.integration.practice_languages.evaluation_set import evaluated_languages

REPOSITORY = Path(__file__).resolve().parents[4]
LANGUAGE_VARIABLE = "OPEN_LANGUAGE_BENCH_LANGUAGE"
OUTPUT_VARIABLE = "OPEN_LANGUAGE_BENCH_OUT"
FEATURE_FILE = REPOSITORY / ".specify" / "feature.json"
RESULTS_MARKDOWN = "benchmark-results.md"
RESULTS_JSON = "benchmark-results.json"
REVIEW_SHEET = "review-sheet.md"
REVIEW_HEADER = "| Scenario | Learner | Reply | Flagged words | Verdict |\n|---|---|---|---|---|\n"


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    kind: str
    """adherence | transcription"""
    language: str
    voice: str | None
    model: str
    passed: int
    total: int
    threshold: str
    met: bool | None
    """None when the benchmark could not run."""
    not_run_reason: str | None = None
    results_file: str | None = None
    review_sheet: str | None = None

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


def bench_languages() -> tuple[str, ...]:
    chosen = os.environ.get(LANGUAGE_VARIABLE)
    return (chosen,) if chosen else evaluated_languages()


def bench_output_dir(code: str) -> Path:
    chosen = os.environ.get(OUTPUT_VARIABLE)
    if chosen:
        return Path(chosen)
    feature = json.loads(FEATURE_FILE.read_text(encoding="utf-8"))["feature_directory"]
    return REPOSITORY / feature / "languages" / code


def record_benchmark(directory: Path, result: BenchmarkResult, section: str) -> None:
    """Store one result and its Markdown section, replacing an earlier run of the same benchmark."""
    directory.mkdir(parents=True, exist_ok=True)
    entry = {"result": _with_results_file(directory, result).as_json(), "section": section}
    stored = _replaced(_stored(directory), entry)
    (directory / RESULTS_JSON).write_text(_json(stored), encoding="utf-8")
    (directory / RESULTS_MARKDOWN).write_text(_markdown(result.language, stored), encoding="utf-8")


def write_review_sheet(
    directory: Path, code: str, others: tuple[str, ...], rows: list[tuple[str, str, str, str]]
) -> Path:
    """Every flagged reply, with an empty Verdict column for a person to fill."""
    name, other_names = language_name(code), _either(others)
    header = (
        f"# {name} review sheet\n\nEvery reply the purity check flagged. Mark each `foreign` if it "
        f"really contains a word of {other_names}, or `{name}` if the flag was wrong (a name, or a "
        f"standard {name} word).\n\n"
    )
    directory.mkdir(parents=True, exist_ok=True)
    sheet = directory / REVIEW_SHEET
    sheet.write_text(
        header + REVIEW_HEADER + "".join(_row(row) + "\n" for row in rows), encoding="utf-8"
    )
    return sheet


def _replaced(stored: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    """The entries with `entry` in place of an earlier run of the same benchmark, else appended."""
    same = [
        index
        for index, old in enumerate(stored)
        if _identity(old["result"]) == _identity(entry["result"])
    ]
    if not same:
        return [*stored, entry]
    return [entry if index == same[0] else old for index, old in enumerate(stored)]


def _stored(directory: Path) -> list[dict[str, Any]]:
    path = directory / RESULTS_JSON
    if not path.is_file():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get("entries", []))


def _json(stored: list[dict[str, Any]]) -> str:
    document = {"results": [entry["result"] for entry in stored], "entries": stored}
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def _markdown(code: str, stored: list[dict[str, Any]]) -> str:
    header = f"# Benchmark results: {language_name(code)} ({code})\n\nWritten by the benchmarks; rerun to replace.\n"
    return "\n".join([header, *(entry["section"] for entry in stored)])


def _identity(result: dict[str, Any]) -> tuple[Any, ...]:
    return result["kind"], result["language"], result["voice"]


def _with_results_file(directory: Path, result: BenchmarkResult) -> BenchmarkResult:
    sheet = _shown(Path(result.review_sheet)) if result.review_sheet else None
    return replace(result, results_file=_shown(directory / RESULTS_MARKDOWN), review_sheet=sheet)


def _shown(path: Path) -> str:
    return str(path.relative_to(REPOSITORY)) if path.is_relative_to(REPOSITORY) else str(path)


def _either(codes: tuple[str, ...]) -> str:
    names = [language_name(code) for code in codes]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]


def _row(cells: tuple[str, ...]) -> str:
    escaped = (cell.replace("|", "\\|").replace("\n", " ") for cell in cells)
    return "| " + " | ".join(escaped) + " |  |"
