"""Each practice language's benchmark inputs, from `evaluation/<code>.toml` (contracts/data-files.md).

The files are written by the language kit (`kit.sh apply`), never by hand. Reading is strict, like
the runtime loader: an unknown, missing or mistyped key raises `EvaluationSetError`.
"""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from app.practice_languages import PRACTICE_LANGUAGES

EVALUATION_DIR = Path(__file__).resolve().parent / "evaluation"
_KEYS = {"code", "special_letters", "turns", "dictation", "loanwords"}


class EvaluationSetError(ValueError):
    """An evaluation file is missing or malformed; names the file and the key."""


@dataclass(frozen=True, slots=True)
class EvaluationSet:
    code: str
    special_letters: str
    """The letters a transcript must keep; empty for a language without diacritics."""
    turns: Mapping[str, tuple[str, ...]]
    """Scripted learner turns, keyed by scenario id."""
    dictation: tuple[str, ...]
    loanwords: frozenset[str]
    """Standard words of the language that are also common elsewhere; never counted as foreign."""


def evaluation_set(code: str, directory: Path = EVALUATION_DIR) -> EvaluationSet:
    path = directory / f"{code}.toml"
    if not path.is_file():
        raise EvaluationSetError(f"{path.name}: no evaluation file for {code!r} in {directory}")
    table = tomllib.loads(path.read_text(encoding="utf-8"))
    _check_keys(path, table)
    return EvaluationSet(
        code=_typed(path, table, "code", str),
        special_letters=_typed(path, table, "special_letters", str),
        turns=MappingProxyType(_turns(path, _typed(path, table, "turns", dict))),
        dictation=_strings(path, table, "dictation"),
        loanwords=frozenset(_strings(path, table, "loanwords")),
    )


def evaluated_languages(directory: Path = EVALUATION_DIR) -> tuple[str, ...]:
    """The catalogued languages that have an evaluation file, in catalogue order."""
    with_file = {path.stem for path in directory.glob("*.toml")}
    return tuple(code for code in PRACTICE_LANGUAGES if code in with_file)


def _check_keys(path: Path, table: dict[str, Any]) -> None:
    for key in sorted(table.keys() - _KEYS):
        raise EvaluationSetError(f"{path.name}: unknown key {key!r}")
    for key in sorted(_KEYS - table.keys()):
        raise EvaluationSetError(f"{path.name}: missing key {key!r}")


def _typed(path: Path, table: dict[str, Any], key: str, expected: type) -> Any:
    if not isinstance(table[key], expected):
        raise EvaluationSetError(f"{path.name}: key {key!r} must be {expected.__name__}")
    return table[key]


def _strings(path: Path, table: dict[str, Any], key: str) -> tuple[str, ...]:
    values = table[key]
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise EvaluationSetError(f"{path.name}: key {key!r} must be a list of strings")
    return tuple(values)


def _turns(path: Path, table: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    return {scenario: _scenario_turns(path, scenario, turns) for scenario, turns in table.items()}


def _scenario_turns(path: Path, scenario: str, turns: Any) -> tuple[str, ...]:
    if not isinstance(turns, list) or not all(isinstance(turn, str) for turn in turns):
        raise EvaluationSetError(f"{path.name}: key 'turns.{scenario}' must be a list of strings")
    return tuple(turns)
