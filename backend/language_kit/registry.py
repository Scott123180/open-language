"""What every practice language needs: one registry drives the pack, validation, check and backfill.

Adding a per-language item is a `Requirement` here plus a field on its record (see the
language-kit skill, "Adding a per-language requirement"). The guard test compares the two.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

from language_kit.context import RuleContext
from language_kit.findings import Finding
from language_kit.rules import (
    SPEAKING_RATES,
    VOICE_GENDERS,
    AtLeast,
    CoversEveryScenario,
    DefaultVoiceAmongVoices,
    DistinctLetters,
    EachContainsSpecialLetter,
    EachWordCount,
    ExactCount,
    ExactlyOnePlaceholder,
    LowercaseWords,
    MatchesPattern,
    MinCount,
    NamesForEveryVoiceGender,
    NotCatalogued,
    NotExplanationLanguage,
    OneOf,
    PreferBothGenders,
    PreferTwoVoices,
    Present,
    Required,
    Rule,
    SupportedScript,
    UniqueAcrossLanguages,
    UniqueCasefold,
    VoicesInCatalogue,
    WhisperSupports,
)

MIN_HOST_NAMES = 10
TURNS_PER_SCENARIO = 5
DICTATION_SENTENCES = 20
MIN_DICTATION_WORDS = 3
MAX_DICTATION_WORDS = 15
NAME_PLACEHOLDER = "{name}"


class Destination(Enum):
    RUNTIME = "runtime"
    EVALUATION = "evaluation"


class Producer(Enum):
    AGENT = "agent"
    CHOSEN = "chosen"
    DERIVED = "derived"


@dataclass(frozen=True, slots=True)
class Requirement:
    path: str
    destination: Destination
    producer: Producer
    needed_by: str
    description: str
    rules: tuple[Rule, ...]
    onboarding_only: bool = False

    def findings(self, context: RuleContext, *, onboarding: bool = False) -> list[Finding]:
        """Every finding for this item of `context.language`; onboarding-only rules on request."""
        rules = [rule for rule in self.rules if onboarding or not rule.onboarding_only]
        return [
            finding
            for concrete_path, value in context.language.items(self.path)
            for finding in _first_error_and_warnings(rules, value, context.at(concrete_path))
        ]


def _first_error_and_warnings(
    rules: list[Rule], value: object, context: RuleContext
) -> list[Finding]:
    """Rules run in order; after the first error the rest would only repeat it, so they stop."""
    findings: list[Finding] = []
    for rule in rules:
        found = rule.check(value, context)
        findings += found
        if any(finding.is_error for finding in found):
            break
    return findings


_R, _E = Destination.RUNTIME, Destination.EVALUATION
_AGENT, _CHOSEN, _DERIVED = Producer.AGENT, Producer.CHOSEN, Producer.DERIVED

REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        "code",
        _R,
        _DERIVED,
        "006",
        "The language's ISO 639-1 code; also the data files' names.",
        (
            Required(),
            MatchesPattern(r"^[a-z]{2}$", "ISO 639-1, two lowercase letters"),
            NotCatalogued(),
            NotExplanationLanguage(),
            SupportedScript(),
            WhisperSupports(),
        ),
    ),
    Requirement(
        "name",
        _R,
        _AGENT,
        "006",
        "The language's English name, as prompts and the Settings screen show it.",
        (Required(), UniqueAcrossLanguages()),
    ),
    Requirement(
        "order",
        _R,
        _DERIVED,
        "008",
        "Where the language sits in lists; the kit gives a new language the next number.",
        (Required(), AtLeast(1), UniqueAcrossLanguages()),
    ),
    Requirement(
        "voices",
        _R,
        _CHOSEN,
        "006",
        "The Piper voices that speak the language. Choose keys from the candidates listed above.",
        (
            Required(),
            MinCount(1),
            UniqueAcrossLanguages("key"),
            VoicesInCatalogue(),
            PreferTwoVoices(),
            PreferBothGenders(),
        ),
    ),
    Requirement(
        "voices[].gender",
        _R,
        _AGENT,
        "007",
        "Each voice's gender, from its name or model card; podcasts cast hosts by it.",
        (Required(), OneOf(VOICE_GENDERS)),
    ),
    Requirement(
        "voices[].speaking_rate",
        _R,
        _AGENT,
        "006",
        "How fast the voice speaks; leave it out for natural.",
        (Required(), OneOf(SPEAKING_RATES)),
    ),
    Requirement(
        "default_voice",
        _R,
        _CHOSEN,
        "006",
        "The voice a learner hears until they choose another.",
        (Required(), DefaultVoiceAmongVoices()),
    ),
    Requirement(
        "podcast.host_names",
        _R,
        _AGENT,
        "007",
        "First names podcast hosts are given, one list per voice gender. Common, everyday names.",
        (Required(), NamesForEveryVoiceGender(MIN_HOST_NAMES)),
    ),
    Requirement(
        "podcast.guest_labels",
        _R,
        _AGENT,
        "007",
        "The language's own words for a show's guest or caller, cut from host lines like labels.",
        (Required(), MinCount(1), UniqueCasefold(), MatchesPattern(r"\S", "each non-empty")),
    ),
    Requirement(
        "podcast.sample_line",
        _R,
        _AGENT,
        "007",
        "What a podcast host says when the learner previews their voice.",
        (Required(), ExactlyOnePlaceholder(NAME_PLACEHOLDER)),
    ),
    Requirement(
        "evaluation.special_letters",
        _E,
        _AGENT,
        "006",
        "Letters a transcript must keep (accents, umlauts). Empty for a language without them.",
        (Present(), DistinctLetters()),
    ),
    Requirement(
        "evaluation.turns",
        _E,
        _AGENT,
        "006",
        "Correct, simple learner turns for the adherence benchmark, one list per scenario.",
        (Required(), CoversEveryScenario(TURNS_PER_SCENARIO)),
    ),
    Requirement(
        "evaluation.dictation",
        _E,
        _AGENT,
        "006",
        "Everyday sentences for the transcription benchmark, read aloud by every voice.",
        (
            Required(),
            ExactCount(DICTATION_SENTENCES),
            UniqueCasefold(),
            EachWordCount(MIN_DICTATION_WORDS, MAX_DICTATION_WORDS),
            EachContainsSpecialLetter(),
        ),
    ),
    Requirement(
        "evaluation.loanwords",
        _E,
        _AGENT,
        "006",
        "Standard words of the language that are also common in English; never counted as foreign.",
        (Present(), LowercaseWords()),
    ),
)


def requirement(path: str) -> Requirement:
    for item in REQUIREMENTS:
        if item.path == path:
            return item
    raise KeyError(path)


# ── The guard: record fields ↔ registry paths (FR-010) ───────────────────────────────

_RECORD_PREFIXES = {
    "LanguageRecord": "",
    "VoiceRecord": "voices[].",
    "PodcastRecord": "podcast.",
    "EvaluationSet": "evaluation.",
}
_FIELD_PATHS: Mapping[str, str | None] = {
    "LanguageRecord.voices": None,
    "LanguageRecord.podcast": None,
    "VoiceRecord.key": "voices",
    "VoiceRecord.display_name": "voices",
    "VoiceRecord.locale": "voices",
    "VoiceRecord.quality": "voices",
    "EvaluationSet.code": "code",
}
"""Fields that map to another path; None marks a container whose fields are mapped instead."""
_ADD_REQUIREMENT = (
    "Add a Requirement for it (see the language-kit skill, 'Adding a per-language requirement')"
)


def uncovered_fields(records: Mapping[str, Iterable[str]], paths: Iterable[str]) -> list[str]:
    """A message for every record field no requirement covers."""
    known = set(paths)
    return [
        f"`{record}.{field}` is per-language data with no entry in `language_kit/registry.py`. "
        + _ADD_REQUIREMENT
        for record, fields in records.items()
        for field in fields
        if (path := _field_path(record, field)) is not None and path not in known
    ]


def orphan_requirements(records: Mapping[str, Iterable[str]], paths: Iterable[str]) -> list[str]:
    """A message for every requirement with no record field behind it."""
    covered = {_field_path(record, field) for record, fields in records.items() for field in fields}
    return [
        f"`{path}` is a requirement in `language_kit/registry.py` with no language-data field. "
        "Remove it, or add the field to its record and loader."
        for path in paths
        if path not in covered
    ]


def _field_path(record: str, field: str) -> str | None:
    qualified = f"{record}.{field}"
    if qualified in _FIELD_PATHS:
        return _FIELD_PATHS[qualified]
    return _RECORD_PREFIXES.get(record, f"{record}.") + field
