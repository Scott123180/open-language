"""T100: no code outside the catalogues names a language code (Constitution V, plan.md).

Every language difference is catalogue data, so adding a language never means hunting for a
hard-coded "es". Defaults come from `DEFAULT_PRACTICE_LANGUAGE`.
"""

import re
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
LANGUAGE_LITERAL = re.compile(r"""(["'])(es|de)\1""")
BACKEND_ALLOWED = {
    REPOSITORY / "backend/app/practice_languages/catalog.py",
    REPOSITORY / "backend/app/services/tts/voices.py",
}


def _backend_sources() -> list[Path]:
    return [
        path for path in (REPOSITORY / "backend/app").rglob("*.py") if path not in BACKEND_ALLOWED
    ]


def _frontend_sources() -> list[Path]:
    sources = [
        *(REPOSITORY / "frontend/src").rglob("*.ts"),
        *(REPOSITORY / "frontend/src").rglob("*.tsx"),
    ]
    return [path for path in sources if ".test." not in path.name]


def _hits(paths: list[Path]) -> list[str]:
    return [
        f"{path.relative_to(REPOSITORY)}:{number}: {line.strip()}"
        for path in paths
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if LANGUAGE_LITERAL.search(line)
    ]


@pytest.mark.parametrize(
    "sources", [_backend_sources, _frontend_sources], ids=["backend", "frontend"]
)
def test_no_language_code_is_hard_coded(sources):
    hits = _hits(sources())

    assert not hits, "Use the language catalogue instead of a literal:\n" + "\n".join(hits)


def test_the_scan_finds_a_literal():
    assert LANGUAGE_LITERAL.search("language = 'de'")
    assert not LANGUAGE_LITERAL.search('voice = "de_DE-thorsten-medium"')
