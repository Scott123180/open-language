"""T064: the skill stays short, static and free of requirement lists (contracts/cli.md § Skill)."""

import re
from pathlib import Path

from language_kit.registry import REQUIREMENTS

SKILL = Path(__file__).resolve().parents[4] / ".claude" / "skills" / "language-kit" / "SKILL.md"
MAX_LINES = 150
SECTIONS = (
    "When to use",
    "Onboard a language",
    "Backfill after a new requirement",
    "Adding a per-language requirement",
    "Rules",
)
TRIGGERS = (
    "add a language",
    "support Italian",
    "new practice language",
    "per-language data",
    "backfill languages",
)


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _frontmatter() -> str:
    match = re.match(r"^---\n(.*?)\n---\n", _text(), re.DOTALL)
    assert match, "SKILL.md needs YAML frontmatter"
    return match.group(1)


def test_the_skill_is_at_most_150_lines():
    assert len(_text().splitlines()) <= MAX_LINES


def test_the_frontmatter_names_the_skill_and_its_triggers():
    frontmatter = _frontmatter()

    assert re.search(r"^name: language-kit$", frontmatter, re.MULTILINE)
    assert all(trigger in frontmatter for trigger in TRIGGERS)


def test_the_five_sections_appear_in_order():
    headings = re.findall(r"^## (.+)$", _text(), re.MULTILINE)

    assert [h for h in headings if h in SECTIONS] == list(SECTIONS)


def test_no_registry_path_appears_so_a_new_requirement_needs_no_skill_edit():
    dotted = [item.path for item in REQUIREMENTS if "." in item.path]

    assert [path for path in dotted if path in _text()] == []
