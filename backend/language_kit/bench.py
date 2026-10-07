"""Running the language-independent benchmarks for one language (research R8).

The benchmarks themselves live in the backend tests behind the `benchmark` marker; the kit checks
what they need first (Ollama and its model, the language's voices), so a missing piece is a plain
exit 3 that writes nothing, then runs pytest with the language and output folder in the
environment and reads back the figures they wrote.
"""

import json
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BENCHMARK_DIR = "tests/integration/practice_languages"
ADHERENCE, TRANSCRIPTION = "adherence", "transcription"
BENCHMARK_FILES = {
    ADHERENCE: "test_adherence_benchmark.py",
    TRANSCRIPTION: "test_transcription_benchmark.py",
}
LANGUAGE_VARIABLE = "OPEN_LANGUAGE_BENCH_LANGUAGE"
OUTPUT_VARIABLE = "OPEN_LANGUAGE_BENCH_OUT"
RESULTS_JSON = "benchmark-results.json"
PYTEST = (".venv/bin/pytest", "-m", "benchmark", "-s", "--no-cov")
"""Benchmarks measure the model, not the code: the coverage floor does not apply to them."""
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_TAGS = "/api/tags"
ADHERENCE_THRESHOLD = "≥ 95%"


class BenchProbe(ABC):
    @abstractmethod
    def ollama_problem(self) -> str | None:
        """What stops the adherence benchmark (Ollama down, model not pulled), or None."""


class OllamaProbe(BenchProbe):
    def __init__(
        self,
        url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        fetch: Callable[[str], bytes] | None = None,
    ) -> None:
        self._url = url
        self._model = model
        self._fetch = fetch or _fetch

    def ollama_problem(self) -> str | None:
        try:
            tags = json.loads(self._fetch(self._url + OLLAMA_TAGS))
        except (OSError, ValueError):
            return f"Ollama is not running at {self._url}: start it with `ollama serve`"
        names = {model.get("name") for model in tags.get("models", [])}
        if self._model not in names:
            return f"the Ollama model {self._model} is not pulled: run `ollama pull {self._model}`"
        return None


@dataclass(frozen=True, slots=True)
class BenchPlan:
    code: str
    kinds: tuple[str, ...]
    """The benchmarks to run."""
    not_run: tuple[dict[str, Any], ...]
    """Results for benchmarks that cannot run here (wordfreq lacks the language)."""

    def argv(self) -> list[str]:
        return [*PYTEST, *(f"{BENCHMARK_DIR}/{BENCHMARK_FILES[kind]}" for kind in self.kinds)]

    def environment(self, output: Path) -> dict[str, str]:
        return {LANGUAGE_VARIABLE: self.code, OUTPUT_VARIABLE: str(output)}


def not_run_result(code: str, kind: str, reason: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "language": code,
        "voice": None,
        "model": "",
        "passed": 0,
        "total": 0,
        "threshold": ADHERENCE_THRESHOLD,
        "met": None,
        "not_run_reason": reason,
        "results_file": None,
        "review_sheet": None,
    }


def read_results(output: Path, code: str, kinds: tuple[str, ...]) -> list[dict[str, Any]]:
    path = output / RESULTS_JSON
    if not path.is_file():
        return []
    results = json.loads(path.read_text(encoding="utf-8")).get("results", [])
    return [result for result in results if result["language"] == code and result["kind"] in kinds]


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 - local Ollama URL
        data: bytes = response.read()
    return data
