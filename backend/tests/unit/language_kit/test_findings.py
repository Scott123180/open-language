"""T020: a finding, and its text and JSON forms (contracts/cli.md § Output shape)."""

from language_kit.findings import (
    MAX_LINE_LENGTH,
    MAX_VALUE_LENGTH,
    Finding,
    Severity,
    findings_as_json,
    quoted,
)


def _finding(severity=Severity.ERROR, detail="Found 8. Add 2 more female names.") -> Finding:
    return Finding("de", "podcast.host_names.female", severity, "at least 10 names", detail)


def test_an_error_reads_as_a_fail_line():
    assert _finding().text() == (
        "FAIL de podcast.host_names.female: at least 10 names. Found 8. Add 2 more female names."
    )


def test_a_warning_reads_as_a_warn_line():
    assert _finding(Severity.WARNING).text().startswith("WARN de podcast.host_names.female: ")


def test_a_long_line_is_cut_to_the_limit_with_an_ellipsis():
    line = _finding(detail="x" * 300).text()

    assert len(line) == MAX_LINE_LENGTH
    assert line.endswith("…")


def test_a_quoted_value_is_cut_to_sixty_characters():
    value = quoted("y" * 100)

    assert len(value) == MAX_VALUE_LENGTH + 2
    assert value == '"' + "y" * (MAX_VALUE_LENGTH - 1) + '…"'


def test_a_short_value_is_quoted_whole():
    assert quoted("Gast") == '"Gast"'


def test_the_json_form_lists_the_five_fields():
    assert findings_as_json([_finding()]) == [
        {
            "language": "de",
            "path": "podcast.host_names.female",
            "severity": "error",
            "rule": "at least 10 names",
            "detail": "Found 8. Add 2 more female names.",
        }
    ]


def test_is_error_tells_errors_from_warnings():
    assert _finding().is_error
    assert not _finding(Severity.WARNING).is_error
