"""A language pack: the one file an agent writes. Parsed strictly, merged onto existing data.

A pack may be partial (a backfill pack): only the items it holds are replaced when merged.
"""

import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from language_kit.context import RuleContext
from language_kit.findings import Finding, Severity, quoted
from language_kit.language_files import EACH, LanguageData
from language_kit.registry import REQUIREMENTS, Producer, Requirement

DERIVED_PATHS = frozenset({"order"})
"""Items `apply` derives; a pack must not hold them."""
DERIVED_VOICE_KEYS = frozenset({"locale", "quality"})
OPTIONAL_VOICE_KEYS = frozenset({"key", "display_name"})
MAX_DISPLAY_NAME_LENGTH = 40
PACK_PATH = "pack"
ITEM_KEY = "key"
_TOML_POSITION = re.compile(r"\s*\(at line (\d+), column \d+\)")


@dataclass(frozen=True, slots=True)
class LanguagePack:
    code: str
    data: LanguageData
    """The pack's values, with item defaults filled in."""
    problems: tuple[Finding, ...]
    """Syntax and structure errors: unknown keys, derived keys, a pack for another language."""
    requirements: tuple[Requirement, ...] = REQUIREMENTS

    @classmethod
    def parse(
        cls, text: str, code: str, requirements: Iterable[Requirement] = REQUIREMENTS
    ) -> "LanguagePack":
        items = tuple(requirements)
        try:
            document = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            return cls(code, LanguageData(code, {}), (_syntax_finding(code, error),), items)
        problems = _Structure(code, items).problems(document)
        return cls(
            code, _with_defaults(LanguageData(code, document), items), tuple(problems), items
        )

    def missing(self) -> tuple[str, ...]:
        """The registry paths this pack leaves out (derived items aside)."""
        return tuple(
            item.path
            for item in self.requirements
            if item.producer is not Producer.DERIVED and not self._has(item.path)
        )

    def merged_onto(self, existing: LanguageData | None) -> LanguageData:
        """The language's data with this pack's items replacing (tables: merging into) its own."""
        merged = existing if existing is not None else LanguageData(self.code, {})
        for path in self._present_items():
            merged = merged.with_value(path, _merged_value(merged.get(path), self.data.get(path)))
        return merged

    def findings(
        self,
        context: RuleContext,
        others: tuple[LanguageData, ...],
        existing: LanguageData | None = None,
        onboarding: bool = False,
    ) -> list[Finding]:
        """Structure problems, then every rule on the merged data. Valid when no error remains."""
        if any(finding.path == PACK_PATH for finding in self.problems):
            return list(self.problems)
        merged = self.merged_onto(existing)
        focused = context.for_language(merged, others)
        checked = [item for item in self.requirements if not _derived_and_absent(item, merged)]
        return [
            *self.problems,
            *(f for item in checked for f in item.findings(focused, onboarding=onboarding)),
        ]

    def _has(self, path: str) -> bool:
        if EACH not in path:
            return self.data.get(path) is not None
        values = self.data.items(path)
        return bool(values) and all(value is not None for _, value in values)

    def _present_items(self) -> list[str]:
        return [
            item.path
            for item in self.requirements
            if EACH not in item.path and self.data.get(item.path) is not None
        ]


class _Structure:
    """Finds keys a pack must not hold: unknown ones, derived ones, a bad display name."""

    def __init__(self, code: str, requirements: tuple[Requirement, ...]) -> None:
        self._code = code
        self._paths = {item.path for item in requirements}
        self._lists = {path.split(f"{EACH}.")[0] for path in self._paths if EACH in path}
        self._item_keys = OPTIONAL_VOICE_KEYS | {
            path.split(f"{EACH}.")[1] for path in self._paths if EACH in path
        }

    def problems(self, document: dict[str, Any]) -> list[Finding]:
        found = self._table(document, "")
        written_code = document.get("code")
        if isinstance(written_code, str) and written_code != self._code:
            found.append(
                self._error(
                    "code", "the pack's own language", f"The pack is for {quoted(written_code)}."
                )
            )
        return found

    def _table(self, table: dict[str, Any], prefix: str) -> list[Finding]:
        return [
            finding for key, value in table.items() for finding in self._entry(prefix + key, value)
        ]

    def _entry(self, path: str, value: Any) -> list[Finding]:
        if path in DERIVED_PATHS:
            return [self._derived(path)]
        if path in self._lists:
            return self._items(path, value)
        if path in self._paths:
            return []
        if isinstance(value, dict) and any(known.startswith(f"{path}.") for known in self._paths):
            return self._table(value, f"{path}.")
        return [
            self._error(
                path,
                "a key the registry knows",
                f"{quoted(path)} is not a pack key; check its spelling.",
            )
        ]

    def _items(self, path: str, value: Any) -> list[Finding]:
        items = value if isinstance(value, list) else []
        return [
            finding
            for index, item in enumerate(items)
            if isinstance(item, dict)
            for key, field in item.items()
            for finding in self._item_key(f"{path}[{index}].{key}", key, field)
        ]

    def _item_key(self, path: str, key: str, value: Any) -> list[Finding]:
        if key in DERIVED_VOICE_KEYS:
            return [self._derived(path)]
        if key not in self._item_keys:
            return [
                self._error(path, "a key the registry knows", f"{quoted(key)} is not a voice key.")
            ]
        if key == "display_name" and not _is_display_name(value):
            rule = f"display_name: 1–{MAX_DISPLAY_NAME_LENGTH} characters"
            return [self._error(path, rule, f"Found {quoted(value)}.")]
        return []

    def _derived(self, path: str) -> Finding:
        return self._error(path, "derived by the kit; remove it", "")

    def _error(self, path: str, rule: str, detail: str) -> Finding:
        return Finding(self._code, path, Severity.ERROR, rule, detail)


def _syntax_finding(code: str, error: tomllib.TOMLDecodeError) -> Finding:
    message = str(error)
    position = _TOML_POSITION.search(message)
    line = position.group(1) if position else "?"
    return Finding(
        code, PACK_PATH, Severity.ERROR, f"line {line}: {_TOML_POSITION.sub('', message)}", ""
    )


def _with_defaults(language: LanguageData, requirements: tuple[Requirement, ...]) -> LanguageData:
    for item in requirements:
        if item.default is None or EACH not in item.path:
            continue
        container, field = item.path.split(f"{EACH}.")
        entries = language.get(container)
        if isinstance(entries, list):
            filled = [
                (
                    entry | {field: entry.get(field, item.default)}
                    if isinstance(entry, dict)
                    else entry
                )
                for entry in entries
            ]
            language = language.with_value(container, filled)
    return language


def _merged_value(old: Any, new: Any) -> Any:
    if isinstance(old, dict) and isinstance(new, dict):
        return old | new
    if _keyed_items(old) and _keyed_items(new):
        stored = {entry[ITEM_KEY]: entry for entry in old}
        return [stored.get(entry[ITEM_KEY], {}) | entry for entry in new]
    return new


def _keyed_items(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(entry, dict) and ITEM_KEY in entry for entry in value
    )


def _is_display_name(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= MAX_DISPLAY_NAME_LENGTH


def _derived_and_absent(item: Requirement, merged: LanguageData) -> bool:
    return item.path in DERIVED_PATHS and merged.get(item.path) is None
