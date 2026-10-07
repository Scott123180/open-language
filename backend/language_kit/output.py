"""Exit codes and the one shape every command's output takes (contracts/cli.md § Output shape)."""

import json
from dataclasses import dataclass, field
from typing import Any, TextIO

from language_kit.findings import Finding, findings_as_json

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_EXTERNAL = 3
NEXT_STEP_PREFIX = "→ next: "


@dataclass(slots=True)
class CommandResult:
    """What a command did: one summary line, the lines that need attention, the next step."""

    command: str
    exit_code: int
    summary: str
    lines: list[str] = field(default_factory=list)
    next_step: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    """Extra fields for `--json`."""

    @classmethod
    def with_findings(
        cls, command: str, summary: str, findings: list[Finding], **extra: Any
    ) -> "CommandResult":
        """A result whose attention lines are findings: exit 1 when any is an error."""
        exit_code = EXIT_FINDINGS if any(finding.is_error for finding in findings) else EXIT_OK
        data = extra.pop("data", {}) | {"findings": findings_as_json(findings)}
        lines = [finding.text() for finding in findings]
        return cls(command, exit_code, summary, lines, data=data, **extra)


def emit(result: CommandResult, out: TextIO, as_json: bool) -> None:
    if as_json:
        out.write(json.dumps(_as_json(result), ensure_ascii=False, indent=2) + "\n")
        return
    lines = [result.summary, *result.lines]
    if result.next_step:
        lines.append(NEXT_STEP_PREFIX + result.next_step)
    out.write("".join(f"{line}\n" for line in lines))


def _as_json(result: CommandResult) -> dict[str, Any]:
    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "summary": result.summary,
        "next": result.next_step,
    } | result.data
