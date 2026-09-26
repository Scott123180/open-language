"""T096: the docs describe a provider-agnostic app, local by default (FR-030, FR-031, SC-009)."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = ("README.md", "CLAUDE.md", "docs/architecture.md")
LOCAL_ONLY_CLAIMS = ("no cloud", "no external services", "fully local", "local-only")
QUALIFIERS = ("default", "ollama", "piper", "faster-whisper", "whisper", "speech")
HEADING = re.compile(r"^#{1,6} ", re.MULTILINE)


def _text(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", DOCS)
def test_each_doc_says_local_by_default(name):
    assert "local by default" in _text(name).lower()


@pytest.mark.parametrize("name", DOCS)
def test_no_doc_makes_an_unqualified_local_only_claim(name):
    unqualified = [
        line.strip()
        for line in _text(name).splitlines()
        if any(claim in line.lower() for claim in LOCAL_ONLY_CLAIMS)
        and not any(qualifier in line.lower() for qualifier in QUALIFIERS)
    ]

    assert unqualified == []


def test_the_readme_explains_how_to_enable_claude():
    sections = HEADING.split(_text("README.md"))

    assert any(
        "claude code" in section.lower()
        and "sign in" in section.lower()
        and "settings" in section.lower()
        for section in sections
    )
