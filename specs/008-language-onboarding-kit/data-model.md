# Data Model: Language Onboarding Kit

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md)

There are **no database changes**: no table, column or row is added, and the kit never opens the
database (research R9). The entities below are files and in-memory value objects. Field formats are
in [contracts/pack-format.md](contracts/pack-format.md) and
[contracts/data-files.md](contracts/data-files.md).

```text
                    ┌──────────────────────────┐
                    │ Requirement registry     │  language_kit/registry.py
                    │  REQUIREMENTS: (Req, …)  │
                    └────────────┬─────────────┘
          generates ┌────────────┼───────────────┬───────────────┐ guards (both directions)
                    ▼            ▼               ▼               ▼
            Pack template   Validation /    Backfill pack   Record fields in
            (pack.toml)     completeness    (missing items) app/language_data
                    │ filled by agent                            ▲
                    ▼                                            │ loaded by
            Language pack ──apply──► runtime file  <code>.toml ──┘ (app)
                                 └─► evaluation file <code>.toml ──► benchmarks (tests)
                    every step ──► run-log.jsonl ──report──► report.md
```

---

## Runtime language data (app)

### LanguageRecord

One practice language, as loaded from `app/language_data/languages/<code>.toml`.

| Field | Type | Rules |
|---|---|---|
| `code` | str | ISO 639-1, two lowercase letters; equals the file stem |
| `name` | str | English name; non-empty; unique across languages |
| `order` | int | ≥ 1; unique; display order (derived: max + 1) |
| `default_voice` | str | the key of one of `voices` |
| `voices` | tuple[VoiceRecord, ...] | ≥ 1; keys unique across all languages |
| `podcast` | PodcastRecord | |

### VoiceRecord

| Field | Type | Producer | Rules |
|---|---|---|---|
| `key` | str | chosen | in the voice catalogue, `language.family == code`, single speaker |
| `gender` | `"female"` \| `"male"` | agent | as the voice's name / model card indicates |
| `speaking_rate` | `"natural"` \| `"fast"` \| `"slow"` | agent (default `natural`) | |
| `display_name` | str | derived, or agent override | `"<Name> (<country_english>)"`, e.g. "Paola (Italy)"; a pack may set it (1–40 characters) |
| `locale` | str | derived | `language.code`, e.g. `it_IT`; prefix equals `code` |
| `quality` | str | derived | catalogue `quality` (`x_low`, `low`, `medium`, `high`) |

These fields are exactly today's `VoiceInfo` fields. `VoiceInfo.language` remains the computed
locale prefix.

### PodcastRecord (007)

| Field | Type | Rules |
|---|---|---|
| `host_names` | mapping gender → tuple[str, ...] | a key for every gender among `voices`, no other key; ≥ 10 names per gender; unique (case-insensitive) across genders; each 1–20 characters, no digits |
| `guest_labels` | tuple[str, ...] | ≥ 1; unique (case-insensitive); each non-empty |
| `sample_line` | str | contains `{name}` exactly once and no other `{` or `}` |

### Mapping to today's public types (unchanged)

| Public name | Built from |
|---|---|
| `PracticeLanguage(code, name, default_voice, host_names, guest_labels, sample_line)` | `LanguageRecord` + its `PodcastRecord` |
| `PRACTICE_LANGUAGES` | all records, sorted by `order`, wrapped in `MappingProxyType` |
| `VoiceInfo(key, display_name, gender, locale, quality, speaking_rate)` | `VoiceRecord` |
| `AVAILABLE_VOICES` | every language's voices, in language order, then file order |

`DEFAULT_PRACTICE_LANGUAGE = "es"` and `NATIVE_LANGUAGE_NAMES` stay as code in `catalog.py`.

---

## Evaluation data (tests)

### EvaluationSet

One language's benchmark inputs, from `tests/integration/practice_languages/evaluation/<code>.toml`.

| Field | Type | Rules |
|---|---|---|
| `code` | str | equals the file stem and a catalogued language |
| `special_letters` | str | letters only, no duplicates; may be empty (a language without diacritics) |
| `turns` | mapping scenario id → tuple[str, ...] | a key for **every current scenario** and no other; exactly 5 turns each; each non-empty |
| `dictation` | tuple[str, ...] | exactly 20; unique; each has 3–15 words; when `special_letters` is non-empty, each contains at least one of them |
| `loanwords` | frozenset[str] | lowercase single words; may be empty |

German's existing data moves in unchanged, with `special_letters = "äöüß"`. Spanish gets a new set
through backfill (research R2).

---

## Kit entities (`backend/language_kit/`)

### Requirement

| Field | Type | Meaning |
|---|---|---|
| `path` | str | dotted path in the pack: `name`, `voices`, `podcast.host_names`, `evaluation.turns`, … |
| `destination` | `RUNTIME` \| `EVALUATION` | the data file the value is written to |
| `producer` | `AGENT` \| `CHOSEN` \| `DERIVED` | who supplies the value |
| `needed_by` | str | the feature that needs it: `006`, `007`, `008` |
| `description` | str | one or two sentences, shown in the pack and in `kit requirements` |
| `rules` | tuple[Rule, ...] | checked in order |
| `onboarding_only` | bool | true for `code`'s "not yet catalogued" style checks; skipped by `check` |

The initial registry has 14 requirements:

| Path | Destination | Producer | Needed by |
|---|---|---|---|
| `code` | runtime | derived | 006 |
| `name` | runtime | agent | 006 |
| `order` | runtime | derived | 008 |
| `voices` | runtime | chosen | 006 |
| `voices[].gender` | runtime | agent | 007 |
| `voices[].speaking_rate` | runtime | agent | 006 |
| `default_voice` | runtime | chosen | 006 |
| `podcast.host_names` | runtime | agent | 007 |
| `podcast.guest_labels` | runtime | agent | 007 |
| `podcast.sample_line` | runtime | agent | 007 |
| `evaluation.special_letters` | evaluation | agent | 006 |
| `evaluation.turns` | evaluation | agent | 006 |
| `evaluation.dictation` | evaluation | agent | 006 |
| `evaluation.loanwords` | evaluation | agent | 006 |

`voices[].display_name`, `locale` and `quality` are covered by the `voices` requirement. They are
derived when it is applied (a pack may override `display_name`), and the guard maps them to it.

### Rule

An interface: `check(value, context: RuleContext) -> list[Finding]`, plus `describe() -> str` for
the pack and `severity` (`ERROR` | `WARNING`). Initial rules:
- `Required`, `MinCount(n)`, `ExactCount(n)` and `UniqueCasefold`;
- `MatchesPattern(regex, hint)`, `OneOf(values)` and `ExactlyOnePlaceholder("{name}")`;
- `NotCatalogued` (onboarding only) and `NotExplanationLanguage`;
- `SupportedScript`, `WhisperSupports`, `VoicesInCatalogue` and `DefaultVoiceAmongVoices`;
- `NamesForEveryVoiceGender(min=10)`, `CoversEveryScenario(turns=5)` and `EachContainsSpecialLetter`;
- warnings: `PreferTwoVoices` and `PreferBothGenders`.

### RuleContext

The app facts that rules read, gathered once per command:
- `scenario_ids`;
- `catalogued_codes`;
- `explanation_codes`;
- `whisper_codes`;
- `wordfreq_codes`;
- `voice_catalogue`, optional, present when fetched or cached.

Rules never import the app.

### Finding

| Field | Type |
|---|---|
| `language` | str |
| `path` | str |
| `severity` | `ERROR` \| `WARNING` |
| `rule` | str (the rule's `describe()`) |
| `detail` | str: what was found and what to change |

### LanguagePack

A parsed pack. It may be partial (backfill). Methods:
- `missing(registry) -> tuple[str, ...]`;
- `merged_onto(existing: LanguageData | None) -> LanguageData`;
- `findings(registry, context) -> list[Finding]`.

A pack is valid when it has no `ERROR` findings after merging.

### LanguageData

The complete, merged data of one language, held in memory between validation and rendering. It
renders to exactly two files, runtime and evaluation, in canonical form: a fixed header, registry key
order and `tomli-w` formatting. `render(load(file)) == file` for every canonical file.

### VoiceCandidate

A catalogue voice offered for a language:
- `key` and `name`;
- `region` and `country`;
- `quality`;
- no gender: the catalogue has none, so the agent sets it in the pack (plan.md § "Spec
  interpretations" 9);
- `size_bytes`, the total of `.onnx` and `.onnx.json`;
- `files`, each with its `relative_path` and `md5`.

### RunLogEntry

One JSON line in `specs/<feature>/languages/<code>/run-log.jsonl`:

| Field | Type |
|---|---|
| `at` | ISO 8601 timestamp |
| `command` | `prereq` \| `scaffold` \| `validate` \| `apply` \| `verify` \| `check` \| `backfill` \| `bench` |
| `outcome` | `ok` \| `findings` \| `failed` \| `nothing-to-do` \| `dry-run` |
| `findings` | list of Finding (errors and warnings) |
| `files_written` | list of repository-relative paths |
| `voices_downloaded` | list of keys |
| `suites` | list of {name, passed, failed, skipped, log} |
| `benchmarks` | list of BenchmarkResult |

### OnboardingReport

`report.md`, rendered from the run log: header (language, dates, kit commands run), Applied,
Checks, Benchmarks, Open items, Not checked (research R11). It is regenerated in full each time.
Nothing is appended by hand.

### BenchmarkResult

| Field | Type |
|---|---|
| `kind` | `adherence` \| `transcription` |
| `language` | str |
| `voice` | str \| None (transcription only) |
| `model` | str (Ollama model or Whisper size) |
| `passed`, `total`, `threshold` | int, int, str (`"≥ 95%"`, `"≥ 18/20"`) |
| `met` | bool \| None (None when not run) |
| `not_run_reason` | str \| None |
| `results_file`, `review_sheet` | paths |

---

## State transitions: one language through the kit

```text
(absent) ──prereq ok──► (prerequisites met) ──scaffold──► (pack drafted)
   ▲  prereq fail: stop, nothing written                         │ agent fills pack
   │                                                             ▼
   │                               validate: findings ◄──── (pack filled)
   │                                                             │ validate: no errors
   │                                                             ▼
   │                         apply fails: no repo change ◄─ (pack valid)
   │                                                             │ apply
   │                                                             ▼
   │                                  (catalogued) ──verify/check/bench/report──► (onboarded)
   │                                                             │
   └──────── a new requirement is registered ───► (incomplete) ──backfill → fill → finish --pack──┘
```

`check` is read-only in every state. Every transition is idempotent: repeating it in its target
state reports `nothing-to-do`.
