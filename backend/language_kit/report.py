"""report.md, rendered in full from the run log: written by a script, never by hand (R11, FR-027)."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from language_kit.findings import Finding, Severity
from language_kit.run_log import RunLogEntry

NOT_CHECKED = (
    "Listening to the voices",
    "Voice genders: asserted from the voice's name or model card, not checked by listening",
    "A screen-reader pass",
    "Offline use",
    "A human speaking into the microphone",
)
TABLE_SEPARATOR = "|---"


def render_report(code: str, title: str, entries: list[RunLogEntry], root: Path) -> str:
    sections = [
        _header(code, title, entries),
        _section("Applied", _applied(entries)),
        _section("Checks", _checks(entries)),
        _section("Benchmarks", _benchmarks(code, entries)),
        _section("Open items", _open_items(entries, root) or ["None."]),
        _section("Not checked", list(NOT_CHECKED)),
    ]
    return "\n".join(sections)


def _header(code: str, title: str, entries: list[RunLogEntry]) -> str:
    commands = ", ".join(dict.fromkeys(entry.command for entry in entries))
    return (
        f"# Onboarding report: {title}\n\n"
        f"Written by `kit.sh report {code}` from run-log.jsonl; regenerated in full, never edited by hand.\n\n"
        f"- Runs: {entries[0].at} to {entries[-1].at}\n"
        f"- Kit commands run: {commands}\n"
    )


def _section(heading: str, bullets: list[str]) -> str:
    return f"## {heading}\n\n" + "".join(f"- {bullet}\n" for bullet in bullets)


def _applied(entries: list[RunLogEntry]) -> list[str]:
    applies = [entry for entry in entries if entry.command == "apply"]
    files = list(dict.fromkeys(path for entry in applies for path in entry.files_written))
    voices = list(dict.fromkeys(key for entry in applies for key in entry.voices_downloaded))
    return [
        f"Data files: {', '.join(files) or 'none yet'}",
        f"Voices downloaded: {', '.join(voices) or 'none'}",
    ]


def _checks(entries: list[RunLogEntry]) -> list[str]:
    verify = _last(entries, "verify")
    suites = [_suite(suite) for suite in verify.suites] if verify else ["Suites: not run yet"]
    check = _last(entries, "check")
    state = (
        "not run yet" if check is None else ("passed" if check.outcome == "ok" else "failing items")
    )
    return [*suites, f"Completeness check: {state}"]


def _suite(suite: dict[str, Any]) -> str:
    if suite["status"] == "skipped":
        return f"{suite['name']}: skipped (--backend-only)"
    if not suite["passed"] and not suite["failed"]:
        return f"{suite['name']}: {suite['status']}"
    return (
        f"{suite['name']}: {suite['status']} ({suite['passed']} passed, {suite['failed']} failed)"
    )


def _benchmarks(code: str, entries: list[RunLogEntry]) -> list[str]:
    bench = _last(entries, "bench")
    if bench is None or not bench.benchmarks:
        return [f"Not run yet: kit.sh bench {code}"]
    return [benchmark_line(result) for result in bench.benchmarks]


def benchmark_line(result: dict[str, Any]) -> str:
    """One benchmark figure against its threshold, or why it did not run."""
    label = _benchmark_label(result)
    if result["met"] is None:
        return f"{result['kind']}: not run ({result['not_run_reason']})"
    verdict = "met" if result["met"] else "missed"
    return f"{label} ({result['model']}): {result['passed']}/{result['total']} against {result['threshold']}: {verdict}"


def _benchmark_label(result: dict[str, Any]) -> str:
    return f"{result['kind']}, {result['voice']}" if result.get("voice") else str(result["kind"])


def _open_items(entries: list[RunLogEntry], root: Path) -> list[str]:
    bench = _last(entries, "bench")
    results = bench.benchmarks if bench else []
    missed = [
        f"{_benchmark_label(r)} missed: {r['passed']}/{r['total']} against {r['threshold']}"
        for r in results
        if r["met"] is False
    ]
    return [*missed, *_failures(entries), *_warnings(entries), *_review_rows(results, root)]


def _failures(entries: list[RunLogEntry]) -> list[str]:
    verify = _last(entries, "verify")
    failing = (
        [suite["name"] for suite in verify.suites if suite["status"] == "failed"] if verify else []
    )
    return [f"Failing suite: {name} (see its log)" for name in failing]


def _warnings(entries: list[RunLogEntry]) -> list[str]:
    latest = [entry for command in ("apply", "check") if (entry := _last(entries, command))]
    lines = [_as_finding(f).text() for entry in latest for f in entry.findings]
    return list(dict.fromkeys(lines))


def _as_finding(document: dict[str, Any]) -> Finding:
    severity = Severity(document["severity"])
    return Finding(
        document["language"], document["path"], severity, document["rule"], document["detail"]
    )


def _review_rows(results: Iterable[dict[str, Any]], root: Path) -> list[str]:
    sheets = dict.fromkeys(r["review_sheet"] for r in results if r.get("review_sheet"))
    counts = {sheet: _unjudged_rows(root / sheet) for sheet in sheets}
    return [
        f"{count} review-sheet {'row' if count == 1 else 'rows'} still to judge: {sheet}"
        for sheet, count in counts.items()
        if count
    ]


def _unjudged_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [
        line for line in lines if line.startswith("|") and not line.startswith(TABLE_SEPARATOR)
    ][1:]
    return sum(not row.rstrip().rstrip("|").rsplit("|", 1)[-1].strip() for row in rows)


def _last(entries: list[RunLogEntry], command: str) -> RunLogEntry | None:
    return next((entry for entry in reversed(entries) if entry.command == command), None)
