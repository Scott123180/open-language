"""What a rule found, and how it is shown: one line per finding, or JSON (contracts/cli.md)."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

MAX_LINE_LENGTH = 120
MAX_VALUE_LENGTH = 60
ELLIPSIS = "…"


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


_LABELS = {Severity.ERROR: "FAIL", Severity.WARNING: "WARN"}


@dataclass(frozen=True, slots=True)
class Finding:
    language: str
    path: str
    severity: Severity
    rule: str
    """The rule the value broke, as a short sentence."""
    detail: str
    """What was found and what to change."""

    @property
    def is_error(self) -> bool:
        return self.severity is Severity.ERROR

    def text(self) -> str:
        label = _LABELS[self.severity]
        return shortened(f"{label} {self.language} {self.path}: {self.rule}. {self.detail}")

    def as_json(self) -> dict[str, str]:
        return {
            "language": self.language,
            "path": self.path,
            "severity": self.severity.value,
            "rule": self.rule,
            "detail": self.detail,
        }


def findings_as_json(findings: Iterable[Finding]) -> list[dict[str, str]]:
    return [finding.as_json() for finding in findings]


def shortened(text: str, limit: int = MAX_LINE_LENGTH) -> str:
    """The text cut to `limit` characters, ending in an ellipsis when cut."""
    return text if len(text) <= limit else text[: limit - 1] + ELLIPSIS


def quoted(value: object) -> str:
    """A value for a detail: double-quoted, cut to 60 characters."""
    return f'"{shortened(str(value), MAX_VALUE_LENGTH)}"'
