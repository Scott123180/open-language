"""Rules: whether one value is acceptable. Each is one class behind one interface.

Every rule honours `check(value, context) -> list[Finding]` and never raises for bad input: a
missing value, a wrong type or a wrong shape is a finding (LSP). Thresholds are constructor
arguments, so the registry reads as the data model.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, ClassVar

from language_kit.context import RuleContext
from language_kit.findings import Finding, Severity, quoted

PLACEHOLDER_VALUE = "TODO"
VOICE_GENDERS = ("female", "male")
SPEAKING_RATES = ("natural", "fast", "slow")
MAX_NAME_LENGTH = 20
RIGHT_TO_LEFT = frozenset({"ar", "he", "fa", "ur", "yi", "ps", "sd", "ug", "dv"})
UNSPACED = frozenset({"zh", "ja", "th", "lo", "km", "my", "bo"})
SPECIAL_LETTERS_PATH = "evaluation.special_letters"
_SINGLE_WORD = re.compile(r"[^\W\d_]+")
_DIGIT = re.compile(r"\d")


class Rule(ABC):
    severity: ClassVar[Severity] = Severity.ERROR
    onboarding_only: ClassVar[bool] = False
    """True for rules that only make sense before a language is catalogued; `check` skips them."""

    @abstractmethod
    def check(self, value: Any, context: RuleContext) -> list[Finding]: ...

    @abstractmethod
    def describe(self) -> str:
        """The rule as a short sentence, for packs, findings and `kit requirements`."""

    def table_keys(self, context: RuleContext) -> tuple[str, ...] | None:
        """For a rule on a table value: the keys the table needs. None for other rules."""
        return None

    def _finding(self, context: RuleContext, detail: str, suffix: str = "") -> Finding:
        return Finding(context.code, context.path + suffix, self.severity, self.describe(), detail)

    def _fail(self, context: RuleContext, detail: str, suffix: str = "") -> list[Finding]:
        return [self._finding(context, detail, suffix)]


# ── Generic rules ─────────────────────────────────────────────────────────────────────


class Required(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if value is None:
            return self._fail(context, "Missing; add it.")
        if _is_placeholder(value):
            return self._fail(context, f'Still "{PLACEHOLDER_VALUE}"; fill it in.')
        if isinstance(value, str | list | dict) and not _has_content(value):
            return self._fail(context, "Empty; fill it in.")
        return []

    def describe(self) -> str:
        return "required"


class Present(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if value is None:
            return self._fail(context, "Missing; add it (it may be empty).")
        if _is_placeholder(value):
            return self._fail(
                context, f'Still "{PLACEHOLDER_VALUE}"; fill it in or leave it empty.'
            )
        return []

    def describe(self) -> str:
        return "required (may be empty)"


class MinCount(Rule):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if not isinstance(value, list):
            return self._fail(context, "Expected a list.")
        if len(value) < self.minimum:
            return self._fail(context, f"Found {len(value)}; add {self.minimum - len(value)} more.")
        return []

    def describe(self) -> str:
        return f"at least {_count(self.minimum, 'item')}"


class ExactCount(Rule):
    def __init__(self, count: int) -> None:
        self.count = count

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if not isinstance(value, list):
            return self._fail(context, "Expected a list.")
        if len(value) < self.count:
            return self._fail(context, f"Found {len(value)}; add {self.count - len(value)} more.")
        if len(value) > self.count:
            return self._fail(context, f"Found {len(value)}; remove {len(value) - self.count}.")
        return []

    def describe(self) -> str:
        return f"exactly {_count(self.count, 'item')}"


class UniqueCasefold(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        strings = _strings(value)
        if strings is None:
            return self._fail(context, "Expected a list of text values.")
        return [self._finding(context, f"Repeated: {quoted(text)}.") for text in _repeats(strings)]

    def describe(self) -> str:
        return "unique (case-insensitive)"


class MatchesPattern(Rule):
    """A text, or every text of a list, matches a pattern; `hint` says what the pattern means."""

    def __init__(self, pattern: str, hint: str) -> None:
        self._pattern = re.compile(pattern)
        self._hint = hint

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if isinstance(value, str):
            return (
                []
                if self._pattern.search(value)
                else self._fail(context, f"Found {quoted(value)}.")
            )
        strings = _strings(value)
        if strings is None:
            return self._fail(context, "Expected text or a list of text values.")
        return [
            self._finding(context, f"Item {index}, {quoted(text)}, does not fit.")
            for index, text in enumerate(strings, start=1)
            if not self._pattern.search(text)
        ]

    def describe(self) -> str:
        return self._hint


class OneOf(Rule):
    def __init__(self, values: tuple[str, ...]) -> None:
        self.values = values

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if value in self.values:
            return []
        return self._fail(context, f"Found {quoted(value)}; use {_choices(self.values)}.")

    def describe(self) -> str:
        return f"one of {_choices(self.values)}"


class ExactlyOnePlaceholder(Rule):
    def __init__(self, placeholder: str) -> None:
        self.placeholder = placeholder

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if not isinstance(value, str):
            return self._fail(context, "Expected text.")
        count = value.count(self.placeholder)
        if count != 1:
            return self._fail(
                context, f"Found {self.placeholder} {count} times in {quoted(value)}."
            )
        if set("{}") & set(value.replace(self.placeholder, "")):
            return self._fail(context, f"Other braces in {quoted(value)}; remove them.")
        return []

    def describe(self) -> str:
        return f"contains {self.placeholder} exactly once; no other braces"


class AtLeast(Rule):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if isinstance(value, int) and not isinstance(value, bool) and value >= self.minimum:
            return []
        return self._fail(context, f"Found {quoted(value)}.")

    def describe(self) -> str:
        return f"a whole number ≥ {self.minimum}"


class UniqueAcrossLanguages(Rule):
    """No other catalogued language uses the value (or, for a list of tables, an item's key)."""

    def __init__(self, item_key: str | None = None) -> None:
        self.item_key = item_key

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        return [
            self._finding(context, f"{quoted(taken)} is already used by {other.code}.")
            for other in context.others
            for taken in sorted(self._values(value) & self._values(other.get(context.path)))
        ]

    def describe(self) -> str:
        return (
            f"each {self.item_key} unique across languages"
            if self.item_key
            else "unique across languages"
        )

    def _values(self, value: Any) -> set[str]:
        if self.item_key is None:
            return (
                {str(value)}
                if isinstance(value, str | int) and not isinstance(value, bool)
                else set()
            )
        items = value if isinstance(value, list) else []
        return {
            str(item[self.item_key])
            for item in items
            if isinstance(item, dict) and self.item_key in item
        }


class DistinctLetters(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if isinstance(value, str) and _distinct_letters(value):
            return []
        return self._fail(context, f"Found {quoted(value)}.")

    def describe(self) -> str:
        return "letters only, no duplicates"


class EachWordCount(Rule):
    def __init__(self, minimum: int, maximum: int) -> None:
        self.minimum = minimum
        self.maximum = maximum

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        strings = _strings(value)
        if strings is None:
            return self._fail(context, "Expected a list of sentences.")
        return [
            self._finding(context, f"{quoted(text)} has {_count(len(text.split()), 'word')}.")
            for text in strings
            if not self.minimum <= len(text.split()) <= self.maximum
        ]

    def describe(self) -> str:
        return f"each has {self.minimum}–{self.maximum} words"


class LowercaseWords(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        strings = _strings(value)
        if strings is None:
            return self._fail(context, "Expected a list of words.")
        return [
            self._finding(context, f"{quoted(word)} is not one lowercase word.")
            for word in strings
            if not (_SINGLE_WORD.fullmatch(word) and word == word.lower())
        ]

    def describe(self) -> str:
        return "lowercase single words"


# ── Rules about the language and its voices ──────────────────────────────────────────


class NotCatalogued(Rule):
    onboarding_only = True

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if value not in context.catalogued_codes:
            return []
        detail = f"{quoted(value)} is already catalogued; use kit.sh check {value} / kit.sh backfill {value}."
        return self._fail(context, detail)

    def describe(self) -> str:
        return "not already a practice language"


class NotExplanationLanguage(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if value not in context.explanation_codes:
            return []
        return self._fail(context, f"{quoted(value)} is the language explanations are written in.")

    def describe(self) -> str:
        return "not the explanation language"


class SupportedScript(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if value in RIGHT_TO_LEFT:
            return self._fail(
                context,
                f"{quoted(value)} is written right to left; the app lays out left to right.",
            )
        if value in UNSPACED:
            reason = "is written without spaces between words; word tools and benchmarks need them"
            return self._fail(context, f"{quoted(value)} {reason}.")
        return []

    def describe(self) -> str:
        return "written left to right with spaces between words"


class WhisperSupports(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if value in context.whisper_codes:
            return []
        return self._fail(context, f"The speech recogniser (Whisper) has no {quoted(value)}.")

    def describe(self) -> str:
        return "supported by the speech recogniser"


class VoicesInCatalogue(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if context.voice_catalogue is None or not isinstance(value, list):
            return []
        offered = {voice.key for voice in context.voice_catalogue.candidates(context.code)}
        return [
            self._finding(context, f"{quoted(key)} is not a single-speaker {context.code} voice.")
            for key in _voice_keys(value)
            if key not in offered
        ]

    def describe(self) -> str:
        return "single-speaker voices of the language, from the Piper catalogue"


class DefaultVoiceAmongVoices(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        keys = _voice_keys(context.language.get("voices"))
        if not keys or value in keys:
            return []
        return self._fail(context, f"Found {quoted(value)}; use one of {_choices(tuple(keys))}.")

    def describe(self) -> str:
        return "one of the language's voices"


# ── Rules about content ──────────────────────────────────────────────────────────────


class NamesForEveryVoiceGender(Rule):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        names = _name_lists(value)
        if names is None:
            return self._fail(context, "Expected a table of name lists, one per voice gender.")
        return [
            *self._coverage(names, _voice_genders(context.language), context),
            *(
                finding
                for gender in names
                for finding in self._names(gender, names[gender], context)
            ),
            *self._repeats(names, context),
        ]

    def describe(self) -> str:
        return f"a list for every voice gender, at least {self.minimum} unique names each"

    def table_keys(self, context: RuleContext) -> tuple[str, ...]:
        genders = _voice_genders(context.language)
        return tuple(sorted(genders)) if genders else VOICE_GENDERS

    def _coverage(
        self, names: dict[str, list[str]], genders: frozenset[str] | None, context: RuleContext
    ) -> list[Finding]:
        if genders is None:
            return []
        missing = [
            self._finding(context, f"No names for {g} voices; add {self.minimum}.", f".{g}")
            for g in sorted(genders - names.keys())
        ]
        extra = [
            self._finding(context, f"No voice is {g}; remove these names.", f".{g}")
            for g in sorted(names.keys() - genders)
        ]
        return missing + extra

    def _names(self, gender: str, names: list[str], context: RuleContext) -> list[Finding]:
        findings = [
            self._finding(
                context,
                f"{quoted(name)} needs 1–{MAX_NAME_LENGTH} characters, no digits.",
                f".{gender}",
            )
            for name in names
            if not 0 < len(name.strip()) <= MAX_NAME_LENGTH or _DIGIT.search(name)
        ]
        if len(names) < self.minimum:
            detail = f"Found {len(names)}. Add {self.minimum - len(names)} more {gender} names."
            findings.append(self._finding(context, detail, f".{gender}"))
        return findings

    def _repeats(self, names: dict[str, list[str]], context: RuleContext) -> list[Finding]:
        every_name = [name for gender_names in names.values() for name in gender_names]
        return [
            self._finding(context, f"Repeated: {quoted(name)}.") for name in _repeats(every_name)
        ]


class CoversEveryScenario(Rule):
    def __init__(self, turns: int) -> None:
        self.turns = turns

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if not isinstance(value, dict):
            return self._fail(context, "Expected a table with one list of turns per scenario.")
        scenarios = set(context.scenario_ids)
        missing = [
            self._finding(context, f"No turns; add {self.turns}.", f".{scenario}")
            for scenario in context.scenario_ids
            if scenario not in value
        ]
        extra = [
            self._finding(context, "Not a scenario; remove it.", f".{scenario}")
            for scenario in sorted(value.keys() - scenarios)
        ]
        present = [s for s in context.scenario_ids if s in value]
        return missing + extra + [f for s in present for f in self._turns(s, value[s], context)]

    def describe(self) -> str:
        return f"{self.turns} turns for every scenario"

    def table_keys(self, context: RuleContext) -> tuple[str, ...]:
        return context.scenario_ids

    def _turns(self, scenario: str, turns: Any, context: RuleContext) -> list[Finding]:
        suffix = f".{scenario}"
        strings = _strings(turns)
        if strings is None:
            return self._fail(context, "Expected a list of turns.", suffix)
        if len(strings) != self.turns:
            return self._fail(
                context, f"Found {len(strings)}; exactly {self.turns} needed.", suffix
            )
        if not all(turn.strip() for turn in strings):
            return self._fail(context, "A turn is empty; write it.", suffix)
        return []


class EachContainsSpecialLetter(Rule):
    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        letters = context.language.get(SPECIAL_LETTERS_PATH)
        strings = _strings(value)
        if not _usable_letters(letters) or strings is None:
            return []
        return [
            self._finding(context, f"{quoted(text)} has none of {letters}.")
            for text in strings
            if not set(letters) & set(text)
        ]

    def describe(self) -> str:
        return "each holds at least one of the special letters"


class PreferTwoVoices(Rule):
    severity = Severity.WARNING

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        if isinstance(value, list) and len(value) == 1:
            return self._fail(
                context, "Only one voice; a second gives a choice and podcasts two hosts."
            )
        return []

    def describe(self) -> str:
        return "two or more voices"


class PreferBothGenders(Rule):
    severity = Severity.WARNING

    def check(self, value: Any, context: RuleContext) -> list[Finding]:
        genders = (
            {item.get("gender") for item in value if isinstance(item, dict)}
            if isinstance(value, list)
            else set()
        )
        genders &= set(VOICE_GENDERS)
        if len(genders) != 1:
            return []
        (gender,) = genders
        return self._fail(
            context, f"Every voice is {gender}; podcasts will cast hosts of one gender only."
        )

    def describe(self) -> str:
        return "voices of both genders"


# ── Helpers ──────────────────────────────────────────────────────────────────────────


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.strip() == PLACEHOLDER_VALUE


def _has_content(value: str | list[Any] | dict[str, Any]) -> bool:
    return bool(value.strip()) if isinstance(value, str) else bool(value)


def _strings(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def _repeats(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    repeated = []
    for text in values:
        if text.casefold() in seen:
            repeated.append(text)
        seen.add(text.casefold())
    return repeated


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _choices(values: tuple[str, ...]) -> str:
    return ", ".join(quoted(value) for value in values)


def _distinct_letters(text: str) -> bool:
    return all(letter.isalpha() for letter in text) and len(set(text)) == len(text)


def _usable_letters(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and _distinct_letters(value)


def _voice_keys(voices: Any) -> list[str]:
    items = voices if isinstance(voices, list) else []
    return [
        item["key"] for item in items if isinstance(item, dict) and isinstance(item.get("key"), str)
    ]


def _voice_genders(language: Any) -> frozenset[str] | None:
    """The voices' genders, or None while voices are missing or a gender is invalid."""
    voices = language.get("voices")
    if not isinstance(voices, list) or not voices:
        return None
    genders = [voice.get("gender") if isinstance(voice, dict) else None for voice in voices]
    return frozenset(genders) if all(g in VOICE_GENDERS for g in genders) else None  # type: ignore[arg-type]


def _name_lists(value: Any) -> dict[str, list[str]] | None:
    if not isinstance(value, dict):
        return None
    if not all(
        isinstance(key, str) and _strings(names) is not None for key, names in value.items()
    ):
        return None
    return value
