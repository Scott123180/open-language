"""Pack text generated from the registry: every item with its guidance, ready to fill.

A new `Requirement` appears in every scaffolded and backfill pack with no edit here (FR-009).
TOML puts a table's plain keys before its sub-tables, so within each table the registry order is
kept except that table-valued items (host names, turns) follow the plain ones.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import tomli_w

from language_kit.context import RuleContext
from language_kit.findings import shortened
from language_kit.language_files import EACH, LanguageData
from language_kit.pack import DERIVED_PATHS
from language_kit.registry import REQUIREMENTS, Requirement
from language_kit.voices import VoiceCandidate

HEADER_WIDTH = 96
MIN_RULE_WIDTH = 3
MAX_EXAMPLE_LENGTH = 110
MEGABYTE = 1_000_000
PLACEHOLDER = "TODO"
FILLED_PATHS = ("code", "name")
FULL_INTRO = (
    "# Language pack for {name} ({code}), written by `kit.sh scaffold`. Fill every TODO and empty\n"
    "# list, then run `kit.sh validate {code}` until it reports no errors. Comments are guidance\n"
    "# and are ignored; never edit the generated data files by hand.\n"
)
PARTIAL_INTRO = (
    "# Backfill pack for {name} ({code}), written by `kit.sh backfill`: only the items that fail.\n"
    "# Fill them, run `kit.sh validate {code} --pack <this file>`, then `kit.sh finish {code} --pack`.\n"
)
VOICE_EXAMPLE = (
    "# Add one [[voices]] table per chosen voice, for example:\n"
    "# [[voices]]\n"
    '# key = "{key}"\n'
    '# gender = "female"\n'
)
DISPLAY_NAME_NOTE = (
    '# A voice may also set display_name = "<Name> (<Place>)" to override the name the kit derives\n'
    "# from the catalogue (the voice's name and country).\n"
)
CANDIDATES_HEADING = "# Candidate voices (key, locale, country, quality, download size):\n"


@dataclass(frozen=True, slots=True)
class TemplateSources:
    languages: Mapping[str, LanguageData]
    """The catalogued languages: examples come from the most recent one that passes an item."""
    context: RuleContext
    requirements: tuple[Requirement, ...] = REQUIREMENTS


def full_pack(
    code: str, name: str, sources: TemplateSources, candidates: tuple[VoiceCandidate, ...]
) -> str:
    filled = LanguageData(code, {"code": code, "name": name})
    items: dict[str, tuple[str, ...] | None] = {
        item.path: None for item in sources.requirements if item.path not in DERIVED_PATHS
    }
    return _PackWriter(filled, sources, candidates).text(items, FULL_INTRO)


def partial_pack(
    language: LanguageData, items: Mapping[str, tuple[str, ...] | None], sources: TemplateSources
) -> str:
    """A pack holding `code` and only `items`: a path, with the table keys to ask for (None: all)."""
    filled = LanguageData(language.code, {"code": language.code})
    writer = _PackWriter(filled, sources, (), existing=language)
    return writer.text({"code": None} | dict(items), PARTIAL_INTRO)


class _PackWriter:
    def __init__(
        self,
        filled: LanguageData,
        sources: TemplateSources,
        candidates: tuple[VoiceCandidate, ...],
        existing: LanguageData | None = None,
    ) -> None:
        self._filled = filled
        self._sources = sources
        self._candidates = candidates
        self._existing = existing
        self._requirements = {item.path: item for item in sources.requirements}
        self._lists = {path.split(f"{EACH}.")[0] for path in self._requirements if EACH in path}

    def text(self, items: Mapping[str, tuple[str, ...] | None], intro: str) -> str:
        named = self._existing or self._filled
        sections = [intro.format(name=named.get("name"), code=self._filled.code)]
        sections += [
            self._plain(path) for path in items if "." not in path and not self._is_list(path)
        ]
        sections += self._list_sections(items)
        sections += [self._group(group, items) for group in _groups(items)]
        return "\n".join(section for section in sections if section)

    # ── Sections ─────────────────────────────────────────────────────────────────────

    def _plain(self, path: str, keys: tuple[str, ...] | None = None) -> str:
        if self._table_keys(path, keys) is not None:
            return ""
        key = path.rsplit(".", 1)[-1]
        return self._guidance(path) + tomli_w.dumps({key: self._value(path)})

    def _table(self, path: str, keys: tuple[str, ...] | None) -> str:
        table_keys = self._table_keys(path, keys)
        if table_keys is None:
            return ""
        return self._guidance(path) + f"[{path}]\n" + tomli_w.dumps({key: [] for key in table_keys})

    def _group(self, group: str, items: Mapping[str, tuple[str, ...] | None]) -> str:
        paths = [path for path in items if path.startswith(f"{group}.")]
        plain = [self._plain(path) for path in paths]
        tables = [self._table(path, items[path]) for path in paths]
        heading = f"[{group}]\n" if any(plain) else ""
        return "\n".join(
            part for part in [heading + "\n".join(p for p in plain if p), *tables] if part
        )

    def _list_sections(self, items: Mapping[str, tuple[str, ...] | None]) -> list[str]:
        sections = []
        for container in sorted(self._lists, key=list(self._requirements).index):
            fields = [path for path in items if path.startswith(f"{container}{EACH}.")]
            if container in items:
                sections.append(self._new_items(container, fields))
            elif fields:
                sections.append(self._existing_items(container, fields))
        return sections

    def _new_items(self, container: str, fields: list[str]) -> str:
        """Guidance for choosing items (voices): the candidates and an example, all as comments."""
        text = self._guidance(container) + self._candidate_lines()
        text += "".join("\n" + self._guidance(path) for path in fields)
        first_key = self._candidates[0].key if self._candidates else "<a key from the list above>"
        return text + DISPLAY_NAME_NOTE + VOICE_EXAMPLE.format(key=first_key)

    def _existing_items(self, container: str, fields: list[str]) -> str:
        """One table per existing item, by key, asking only for the given fields."""
        entries = self._existing.get(container) if self._existing is not None else None
        tables = [
            f"[[{container}]]\n"
            + tomli_w.dumps(
                {"key": entry.get("key")} | {self._field(path): PLACEHOLDER for path in fields}
            )
            for entry in entries or []
            if isinstance(entry, dict)
        ]
        return "".join(self._guidance(path) for path in fields) + "\n".join(tables)

    # ── Pieces ───────────────────────────────────────────────────────────────────────

    def _guidance(self, path: str) -> str:
        item = self._requirements[path]
        label = f" {item.producer.value} · needed by {item.needed_by}"
        lead = f"# ── {path} "
        fill = "─" * max(MIN_RULE_WIDTH, HEADER_WIDTH - len(lead) - len(label))
        lines = [lead + fill + label, f"# {item.description}", f"# Rules: {_rules(item)}."]
        example = self._example(item)
        if example:
            lines.append(f"# Example ({example[0]}): {shortened(example[1], MAX_EXAMPLE_LENGTH)}")
        return "\n".join(lines) + "\n"

    def _candidate_lines(self) -> str:
        if not self._candidates:
            return ""
        rows = [
            f"#   {v.key:<28} {v.region:<6} {v.country:<12} {v.quality:<7} {round(v.size_bytes / MEGABYTE)} MB"
            for v in self._candidates
        ]
        return CANDIDATES_HEADING + "\n".join(rows) + "\n"

    def _value(self, path: str) -> Any:
        if path in FILLED_PATHS and self._filled.get(path) is not None:
            return self._filled.get(path)
        example = self._example_value(self._requirements[path])
        return [] if isinstance(example, list) else PLACEHOLDER

    def _table_keys(self, path: str, keys: tuple[str, ...] | None) -> tuple[str, ...] | None:
        item = self._requirements[path]
        context = self._sources.context.for_language(self._existing or self._filled, ())
        default = item.table_keys(context)
        if default is None and not isinstance(self._example_value(item), dict):
            return None
        return keys or default or ()

    def _example(self, item: Requirement) -> tuple[str, str] | None:
        language = self._example_language(item)
        if language is None:
            return None
        value = language.get(item.path)
        return str(language.get("name")), _inline(value[0] if EACH in item.path else _first(value))

    def _example_value(self, item: Requirement) -> Any:
        language = self._example_language(item)
        return language.get(item.path) if language is not None else None

    def _example_language(self, item: Requirement) -> LanguageData | None:
        """The most recently added catalogued language (highest order) whose data passes the item."""
        languages = self._sources.languages
        candidates = [language for code, language in languages.items() if code != self._filled.code]
        for language in sorted(candidates, key=_order, reverse=True):
            others = tuple(other for other in languages.values() if other is not language)
            context = self._sources.context.for_language(language, others)
            if language.get(item.path) is not None and not any(
                f.is_error for f in item.findings(context)
            ):
                return language
        return None

    def _is_list(self, path: str) -> bool:
        return path in self._lists or EACH in path

    @staticmethod
    def _field(path: str) -> str:
        return path.split(f"{EACH}.")[1]


def _groups(items: Mapping[str, tuple[str, ...] | None]) -> list[str]:
    groups = [path.split(".")[0] for path in items if "." in path and EACH not in path]
    return list(dict.fromkeys(groups))


def _rules(item: Requirement) -> str:
    return "; ".join(rule.describe() for rule in item.rules)


def _order(language: LanguageData) -> int:
    order = language.get("order")
    return order if isinstance(order, int) else 0


def _first(value: Any) -> Any:
    """What an example shows: a table's first entry, or a list of tables' first table."""
    if isinstance(value, dict) and value:
        key = next(iter(value))
        return {key: value[key]}
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return value


def _inline(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key} = {_inline(entry)}" for key, entry in value.items())
    if isinstance(value, list):
        return "[" + ", ".join(_inline(entry) for entry in value) + "]"
    return json.dumps(value, ensure_ascii=False)
