"""Load recorded `claude -p` output shapes from tests/fixtures/claude_code/."""

from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "claude_code"


def load_fixture_lines(name: str) -> list[str]:
    """Return the fixture's lines without their trailing newlines."""
    return (FIXTURE_DIR / name).read_text(encoding="utf-8").splitlines()


def load_fixture_text(name: str) -> str:
    """Return the whole fixture as one string."""
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")
