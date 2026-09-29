"""T126: every function 007 adds or modifies is at most 20 lines (Constitution I).

Measured with `ast` as `end_lineno - lineno + 1`, the inclusive count plan.md's
Function-length plan uses. Whole files are checked where 007 owns or reshaped them. In files
that hold older long functions 007 does not touch, only the functions it changed are checked.
"""

import ast
from pathlib import Path

import pytest

MAX_FUNCTION_LINES = 20
APP = Path(__file__).resolve().parents[2] / "app"
WHOLE_FILES = (
    "podcasts",
    "conversation_summary",
    "conversation_turns",
    "routers/audio.py",
    "routers/chat.py",
    "routers/settings.py",
    "services/tts/selection.py",
    "services/tts/base.py",
    "services/factory.py",
    "services/conversation/session.py",
    "practice_languages",
    "models/app_settings.py",
)
NAMED_FUNCTIONS = {
    "database.py": ("init_db",),
    "services/storage/sqlite.py": ("_settings_to_record",),
}


def _sources(entry: str) -> list[Path]:
    path = APP / entry
    return sorted(path.rglob("*.py")) if path.is_dir() else [path]


def _functions(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    kinds = (ast.FunctionDef, ast.AsyncFunctionDef)
    return [node for node in ast.walk(tree) if isinstance(node, kinds)]


def _length(node: ast.AST) -> int:
    return node.end_lineno - node.lineno + 1


def _too_long(path: Path, names: tuple[str, ...] | None = None) -> list[str]:
    return [
        f"{path.relative_to(APP)}:{node.lineno} {node.name} ({_length(node)} lines)"
        for node in _functions(path)
        if (names is None or node.name in names) and _length(node) > MAX_FUNCTION_LINES
    ]


@pytest.mark.parametrize("entry", WHOLE_FILES)
def test_every_function_in_the_file_is_short(entry):
    too_long = [hit for path in _sources(entry) for hit in _too_long(path)]

    assert not too_long, "Split these functions:\n" + "\n".join(too_long)


@pytest.mark.parametrize(("entry", "names"), NAMED_FUNCTIONS.items())
def test_the_changed_functions_are_short(entry, names):
    assert not _too_long(APP / entry, names)


@pytest.mark.parametrize("entry", NAMED_FUNCTIONS)
def test_every_named_function_exists(entry):
    found = {node.name for node in _functions(APP / entry)}

    assert set(NAMED_FUNCTIONS[entry]) <= found
