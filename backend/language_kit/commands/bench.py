"""`bench <code> [--adherence | --transcription]`: run the benchmarks; print each figure."""

import argparse
from typing import Any

from language_kit.bench import (
    ADHERENCE,
    BENCHMARK_FILES,
    TRANSCRIPTION,
    BenchPlan,
    not_run_result,
    read_results,
)
from language_kit.checking import catalogued_languages, is_installed
from language_kit.commands.base import Command
from language_kit.composition import Kit
from language_kit.errors import KitExternalError, KitUsageError
from language_kit.output import EXIT_FINDINGS, EXIT_OK, CommandResult
from language_kit.report import benchmark_line

BENCH_LOG = "logs/bench.log"


class BenchCommand(Command):
    name = "bench"
    help = "run the adherence and transcription benchmarks for a language"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("code", help="a catalogued language code")
        only = parser.add_mutually_exclusive_group()
        only.add_argument("--adherence", action="store_true", help="only the adherence benchmark")
        only.add_argument(
            "--transcription", action="store_true", help="only the transcription benchmark"
        )

    def run(self, arguments: argparse.Namespace, kit: Kit) -> CommandResult:
        plan = _plan(kit, arguments)
        if arguments.dry_run:
            line = f"would run pytest -m benchmark {' '.join(plan.argv()[4:])} (in backend)"
            return CommandResult("bench", EXIT_OK, f"bench {plan.code}: dry run", [line])
        results = [*plan.not_run, *(_run(kit, plan) if plan.kinds else [])]
        missed = any(result["met"] is False for result in results)
        kit.record(plan.code, "bench", "findings" if missed else "ok", benchmarks=results)
        return _result(kit, plan.code, results, EXIT_FINDINGS if missed else EXIT_OK)


def _plan(kit: Kit, arguments: argparse.Namespace) -> BenchPlan:
    code = arguments.code
    languages = catalogued_languages(kit.workspace)
    if code not in languages:
        raise KitUsageError(f"{code} is not catalogued; onboard it first (kit.sh prereq {code})")
    chosen = {ADHERENCE: arguments.adherence, TRANSCRIPTION: arguments.transcription}
    kinds, not_run = _runnable(
        kit, code, tuple(k for k, only in chosen.items() if only) or tuple(BENCHMARK_FILES)
    )
    _check_available(kit, code, kinds, languages[code].get("voices") or [])
    return BenchPlan(code, kinds, not_run)


def _runnable(
    kit: Kit, code: str, kinds: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[dict[str, Any], ...]]:
    """The benchmarks that can run, and a "not run" result for adherence when wordfreq lacks the code."""
    if ADHERENCE not in kinds or code in kit.rule_context().wordfreq_codes:
        return kinds, ()
    reason = f"wordfreq has no {code}, so foreign words cannot be counted"
    return tuple(kind for kind in kinds if kind != ADHERENCE), (
        not_run_result(code, ADHERENCE, reason),
    )


def _check_available(kit: Kit, code: str, kinds: tuple[str, ...], voices: list[Any]) -> None:
    if (
        ADHERENCE in kinds
        and kit.bench_probe is not None
        and (problem := kit.bench_probe.ollama_problem())
    ):
        raise KitExternalError(f"the adherence benchmark needs Ollama: {problem}")
    keys = [str(voice.get("key")) for voice in voices if isinstance(voice, dict)]
    missing = [key for key in keys if not is_installed(key, kit.workspace.voice_dir)]
    if TRANSCRIPTION in kinds and missing:
        raise KitExternalError(
            f"voices not installed: {', '.join(missing)}; run ./run.sh --setup to download them"
        )
    if kit.runner is None:
        raise KitExternalError("no command runner is configured to run the benchmarks")


def _run(kit: Kit, plan: BenchPlan) -> list[dict[str, Any]]:
    output = kit.workspace.language_dir(plan.code)
    log = output / BENCH_LOG
    kit.runner.run(plan.argv(), kit.workspace.root / "backend", log, plan.environment(output))  # type: ignore[union-attr]
    results = read_results(output, plan.code, plan.kinds)
    if {result["kind"] for result in results} != set(plan.kinds):
        raise KitExternalError(
            f"the benchmarks wrote no results; see {kit.workspace.relative(log)}"
        )
    return results


def _result(kit: Kit, code: str, results: list[dict[str, Any]], exit_code: int) -> CommandResult:
    lines = [benchmark_line(result) for result in results]
    files = {("results", r["results_file"]) for r in results if r["results_file"]}
    files |= {("review sheet", r["review_sheet"]) for r in results if r["review_sheet"]}
    lines += [f"{label}: {path}" for label, path in sorted(files)]
    met = sum(result["met"] is True for result in results)
    summary = f"bench {code}: {met} of {len(results)} benchmarks met their threshold"
    return CommandResult(
        "bench", exit_code, summary, lines, f"kit.sh report {code}", {"benchmarks": results}
    )
