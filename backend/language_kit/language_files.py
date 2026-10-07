"""One language's data, addressed by registry path, and reading it from its two data files.

A path is dotted (`podcast.sample_line`); `voices[].gender` means that field of every voice.
Everything under `evaluation.` lives in the evaluation file, the rest in the runtime file.
"""

import copy
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from language_kit.workspace import Workspace

EVALUATION = "evaluation"
EACH = "[]"
UNORDERED = 1_000_000
"""Sorts a file whose `order` is missing or malformed after every well-formed one."""


class LanguageData:
    """Complete or partial values of one language, as a nested document."""

    def __init__(self, code: str, document: Mapping[str, Any]) -> None:
        self._code = code
        self._document = copy.deepcopy(dict(document))

    @property
    def code(self) -> str:
        return self._code

    @property
    def document(self) -> dict[str, Any]:
        return copy.deepcopy(self._document)

    def get(self, path: str) -> Any:
        """The value at `path`, or None. A list path gives every item's value (None if absent)."""
        if EACH in path:
            return [value for _, value in self.items(path)] if self._items_of(path) else None
        return _lookup(self._document, path.split("."))

    def items(self, path: str) -> list[tuple[str, Any]]:
        """`(concrete path, value)` per item for a list path; one pair for any other path."""
        if EACH not in path:
            return [(path, self.get(path))]
        container, field = path.split(f"{EACH}.")
        return [
            (f"{container}[{index}].{field}", item.get(field))
            for index, item in enumerate(self._items_of(path) or [])
        ]

    def with_value(self, path: str, value: Any) -> "LanguageData":
        document = self.document
        *parents, key = path.split(".")
        target = document
        for parent in parents:
            target = target.setdefault(parent, {})
        target[key] = copy.deepcopy(value)
        return LanguageData(self._code, document)

    def without(self, path: str) -> "LanguageData":
        document = self.document
        *parents, key = path.split(".")
        parent = _lookup(document, parents) if parents else document
        if isinstance(parent, dict):
            parent.pop(key, None)
        return LanguageData(self._code, document)

    def _items_of(self, path: str) -> list[dict[str, Any]] | None:
        items = self.get(path.split(EACH)[0])
        if isinstance(items, list) and all(isinstance(item, dict) for item in items):
            return items
        return None


def read_language(code: str, workspace: Workspace) -> LanguageData:
    """A catalogued language's runtime and evaluation files. A missing or malformed file is empty."""
    document = _read_toml(workspace.runtime_dir / f"{code}.toml")
    evaluation = _read_toml(workspace.evaluation_dir / f"{code}.toml")
    evaluation.pop("code", None)
    if evaluation:
        document[EVALUATION] = evaluation
    return LanguageData(code, document)


def catalogued_codes(workspace: Workspace) -> tuple[str, ...]:
    """Every language with a runtime file, in display order."""
    paths = sorted(workspace.runtime_dir.glob("*.toml"))
    return tuple(path.stem for path in sorted(paths, key=_display_order))


def _display_order(path: Path) -> int:
    order = _read_toml(path).get("order")
    return order if isinstance(order, int) else UNORDERED


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _lookup(document: Any, keys: list[str]) -> Any:
    for key in keys:
        if not isinstance(document, dict):
            return None
        document = document.get(key)
    return document
