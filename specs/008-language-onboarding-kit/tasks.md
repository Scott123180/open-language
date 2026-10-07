---

description: "Task list for the Language Onboarding Kit (008)"
---

# Tasks: Language Onboarding Kit

**Input**: Design documents from `specs/008-language-onboarding-kit/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) (R1–R14),
[data-model.md](data-model.md), [contracts/](contracts/) (`cli.md`, `pack-format.md`, `data-files.md`),
[quickstart.md](quickstart.md)

**Tests**: MANDATORY (Constitution III, TDD). Every test task comes before the implementation it
specifies and must be seen to FAIL first, except the pinning test (T006), which must PASS against
today's code before anything moves. Network, downloads, subprocesses and the clock are faked at their
boundaries. Benchmarks stay behind the `benchmark` marker and are run by hand.

**Organization**: Tasks are grouped by user story. The phase order follows the plan's delivery order
(plan.md § "Delivery order"), not the spec's priority order, because the stories build on each other:
US1 (onboard a language) uses US2's registry and rules and US4's pack, render and apply.

| Phase | Story | Priority | Delivers |
|---|---|---|---|
| 3 | US2: the kit tells exactly what a language is missing | P1 | registry, rules, `check`, guard test |
| 4 | US4: the kit stays current | P2 | pack, template, render, apply, `validate`, `backfill`, `requirements` |
| 5 | US1: add a new practice language with the kit | P1 | `prereq`, voices, `scaffold`, `verify`, `finish`, run log, report, the skill; Spanish evaluation set (US4, through `finish --pack`); **Italian** |
| 6 | US3: benchmarks for any language | P2 | language-independent benchmarks, `bench`; German and Italian runs |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4, from spec.md
- Paths are from the repository root. `kit` means `.claude/skills/language-kit/kit.sh` once T074 exists;
  before that, `cd backend && .venv/bin/python -m language_kit`.

## Conventions every task follows

- Functions ≤ 20 lines; thresholds, counts, limits, exit codes and URLs are named constants
  (Constitution I). `tests/unit/test_function_length.py` checks `app/language_data` and
  `language_kit` as whole files (T004).
- Every rule honours `check(value, context) -> list[Finding]` and never raises for bad input; bad input
  is a finding (LSP).
- Kit text output follows contracts/cli.md § "Output shape": one summary line, then only `FAIL` / `WARN`
  lines, then `→ next:`. Lines ≤ 120 characters; long values cut to 60 characters with `…`. Passing
  items are counted, never listed. Exit codes: `0` done or nothing to do, `1` findings, `2` usage or
  unmet prerequisite, `3` external failure.
- Every writing command (`scaffold`, `apply`, `backfill`, `verify`, `bench`, `finish`, `report`)
  accepts `--dry-run`; every command accepts `--json` and `--out DIR` (contracts/cli.md § "Common
  options").
- Type checking: `mypy` runs on the packages this feature adds, `language_kit` and
  `app/language_data`, never on `app` as a whole. `mypy app` already reports 232 errors in 53 files
  this feature does not touch (checked 2026-10-06); they are an out-of-scope open item (plan.md §
  "Spec interpretations" 11). Likewise, ESLint is the frontend lint gate: `prettier --check src`
  already flags 132 files.
- The kit imports app package roots only (`app.language_data`, `app.practice_languages`,
  `app.services.factory`); the app never imports `language_kit` (T005).
- Run Python through `backend/.venv` only.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: packaging, the new dev dependency and empty packages.

- [X] T001 Update `backend/pyproject.toml`: add `"tomli-w==1.2.0"` (pinned; the latest release on 2026-10-06) to `[project.optional-dependencies] dev`; add `[tool.setuptools.packages.find] include = ["app*"]`; add `[tool.setuptools.package-data] "app.language_data" = ["languages/*.toml"]`; add `--cov=language_kit` to `addopts` next to `--cov=app`. Then reinstall with `backend/.venv/bin/pip install -e "backend[dev]"` and confirm `backend/.venv/bin/python -c "import tomli_w"` works
- [X] T002 [P] Create empty packages: `backend/app/language_data/__init__.py`, the directory `backend/app/language_data/languages/`, `backend/language_kit/__init__.py`, `backend/tests/unit/language_data/__init__.py`, `backend/tests/unit/language_kit/__init__.py`, and the directory `backend/tests/integration/practice_languages/evaluation/`
- [X] T003 [P] Confirm `ruff`, `black` and `mypy --strict` reach the new packages: run `cd backend && .venv/bin/ruff check language_kit && .venv/bin/black --check language_kit && .venv/bin/mypy language_kit app/language_data`; if `[tool.mypy]` / `[tool.ruff]` in `backend/pyproject.toml` restrict paths, add `language_kit`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: move Spanish and German from Python literals into data files with **no** behaviour
change, and move German's evaluation set into its data file. Every later phase reads these files.

**⚠️ CRITICAL**: no user-story work starts until this phase's checkpoint passes.

### Guards and the pinning test (write first)

- [X] T004 [P] Extend `backend/tests/unit/test_function_length.py`: add `"language_data"` to `WHOLE_FILES`, and check every function in `backend/language_kit/**/*.py` (resolve it from the backend root beside `APP`) against `MAX_FUNCTION_LINES`; update the module docstring to say 008's packages are checked whole
- [X] T005 [P] Extend `backend/tests/unit/test_module_boundaries.py` with two tests: `test_language_data_imports_nothing_from_the_app` (no module under `app/language_data/` imports `app.*` other than `app.language_data`) and `test_the_app_never_imports_the_language_kit` (no module under `app/` imports `language_kit`)
- [X] T006 Write the pinning test `backend/tests/unit/language_data/test_pinned_language_values.py`, which freezes today's values literally: for `es` and `de`, every `PracticeLanguage` field (`code`, `name`, `default_voice`, `host_names` female and male tuples in order, `guest_labels`, `sample_line`); `list(PRACTICE_LANGUAGES)[:2] == ["es", "de"]`; all six `VoiceInfo` fields of the four voices `es_ES-davefx-medium`, `es_AR-daniela-high`, `de_DE-thorsten-medium`, `de_DE-kerstin-low` in that order; `voices_for("es")` and `voices_for("de")`. It must **not** assert that only Spanish and German exist, so Italian can be added by data alone. **It must PASS against today's `backend/app/practice_languages/catalog.py` and `backend/app/services/tts/voices.py` before T011–T014**

### `app.language_data` (leaf package)

- [X] T007 [P] Write failing loader tests in `backend/tests/unit/language_data/test_loader.py` (use `tmp_path` files): records load sorted by `order`; an unknown key, a missing key and a wrong type each raise `LanguageDataError` naming the file and the key; and each cross-file invariant raises `LanguageDataError`: duplicate `code`, `code` not equal to the file stem, duplicate `order`, a voice key used by two languages, `default_voice` not among the language's voices, and a voice whose locale prefix is not the language's `code`. Records are frozen
- [X] T008 [P] Write failing tests in `backend/tests/unit/language_data/test_voice_keys.py`: `voice_keys()` returns every voice key of every language in language order, then file order; `python -m app.language_data voice-keys` (run with `subprocess` from `backend/`) prints them one per line and exits 0; an unknown subcommand exits 2
- [X] T009 Implement `backend/app/language_data/records.py`: `@dataclass(frozen=True, slots=True)` `VoiceRecord(key, display_name, gender, locale, quality, speaking_rate)`, `PodcastRecord(host_names: Mapping[str, tuple[str, ...]], guest_labels: tuple[str, ...], sample_line: str)` and `LanguageRecord(code, name, order: int, default_voice, voices: tuple[VoiceRecord, ...], podcast: PodcastRecord)` per contracts/data-files.md
- [X] T010 Implement `backend/app/language_data/loader.py`: `LanguageDataError(ValueError)`, `LANGUAGES_DIR`, and `load_language_records(directory: Path = LANGUAGES_DIR) -> tuple[LanguageRecord, ...]` reading every `*.toml` with `tomllib`, strict on keys and types, enforcing the invariants listed in T007; then `backend/app/language_data/__init__.py` (public root: the three records, `load_language_records`, `voice_keys`, `LanguageDataError`) and `backend/app/language_data/__main__.py` (`voice-keys`). T007 and T008 pass
- [X] T011 Generate `backend/app/language_data/languages/es.toml` (`order = 1`) and `backend/app/language_data/languages/de.toml` (`order = 2`) with a one-off script in the session scratchpad (not committed) that serialises today's `PRACTICE_LANGUAGES` and `AVAILABLE_VOICES` with `tomli_w`. Each file starts with the two-line header from contracts/data-files.md § Files (`Language: Spanish (es).` / `German (de)`). Key order: `code`, `name`, `order`, `default_voice`, `[[voices]]` (`key`, `display_name`, `gender`, `locale`, `quality`, `speaking_rate`), `[podcast]` (`guest_labels`, `sample_line`), `[podcast.host_names]` (`female`, `male`). Values byte-for-byte as today
- [X] T012 Switch `backend/app/practice_languages/catalog.py` to build `PRACTICE_LANGUAGES` from `load_language_records()` (a `MappingProxyType` keyed by code in `order` order, `host_names` wrapped in `MappingProxyType`). `PracticeLanguage`, `DEFAULT_PRACTICE_LANGUAGE` and `NATIVE_LANGUAGE_NAMES` are unchanged. T006 passes unchanged
- [X] T013 Switch `backend/app/services/tts/voices.py`: `AVAILABLE_VOICES` is built from `load_language_records()` (every language's voices, language order then file order) as `VoiceInfo` values; `VoiceInfo` and `voices_for` are unchanged; replace the "Keys must match run.sh" docstring with one saying the voices come from `app/language_data/languages/`. T006 passes unchanged
- [X] T014 Update `backend/tests/unit/test_no_language_literals.py`: remove `backend/app/services/tts/voices.py` from `BACKEND_ALLOWED` (it no longer holds data) and update the docstring; the test passes
- [X] T015 Update `run.sh`: delete the hard-coded `PIPER_VOICES=(…)` array and its "keys must match" comment; in `setup_piper_voices`, read the list with `mapfile -t PIPER_VOICES < <("$VENV/bin/python" -m app.language_data voice-keys)` run from `backend/` (it already runs after `setup_backend`), and fail with a clear message if the command fails. Check by hand: `backend/.venv/bin/python -m app.language_data voice-keys` lists the four keys

### German evaluation set → data file

- [X] T016 Write the failing test `backend/tests/integration/practice_languages/test_evaluation_sets.py`, replacing `test_german_evaluation_set.py`: keep every assertion it makes today, now against `evaluation_set("de")` (`.turns`, `.dictation`, `.loanwords`), and add: `evaluation_set("de").special_letters == "äöüß"`; `evaluated_languages()` returns the codes that have an evaluation file, in catalogue order; `evaluation_set("xx")` raises naming the missing file; an unknown or missing key in a `tmp_path` file raises
- [X] T017 Implement `backend/tests/integration/practice_languages/evaluation_set.py`: `@dataclass(frozen=True, slots=True) EvaluationSet(code, special_letters: str, turns: Mapping[str, tuple[str, ...]], dictation: tuple[str, ...], loanwords: frozenset[str])`, `evaluation_set(code) -> EvaluationSet` (strict `tomllib` read of `evaluation/<code>.toml`) and `evaluated_languages() -> tuple[str, ...]`, per contracts/data-files.md
- [X] T018 Generate `backend/tests/integration/practice_languages/evaluation/de.toml` with a one-off scratchpad script (not committed) from today's `german_evaluation_set.py`, values unchanged: header as in T011, then `code = "de"`, `special_letters = "äöüß"` (the `[äöüß]` regex in `test_transcription_benchmark.py`), `loanwords` (sorted), `dictation` (original order), `[turns]` (one key per scenario id, original order). T016 passes
- [X] T019 Switch `backend/tests/integration/practice_languages/test_german_benchmark.py`, `test_transcription_benchmark.py` and `text_purity.py` from `german_evaluation_set` to `evaluation_set("de")` (no other change yet; US3 generalises them); delete `backend/tests/integration/practice_languages/german_evaluation_set.py` and `test_german_evaluation_set.py`. Confirm with `backend/.venv/bin/pytest -m benchmark --collect-only backend/tests/integration/practice_languages` that the benchmarks still collect

**Checkpoint**: `cd backend && .venv/bin/pytest` passes with coverage ≥ 90%, the pinning test passes
unchanged, `ruff`/`black`/`mypy language_kit app/language_data` pass, and `git diff` shows no change to any
`PRACTICE_LANGUAGES` or `AVAILABLE_VOICES` value (FR-021, SC-009).

---

## Phase 3: User Story 2 - The kit tells exactly what a language is missing (Priority: P1)

**Goal**: one registry of per-language requirements, rules behind one interface, and a read-only
`check` that reports pass or fail per language and item; plus the guard test that keeps the registry
and the app's language records in step.

**Independent Test**: `kit check de` passes. Deleting two names from `podcast.host_names.female` in a
copy of `de.toml` makes `check` fail naming `de`, `podcast.host_names.female` and the rule, and pass
every other item (quickstart §3). Spanish fails only on `evaluation.*` until T078 backfills it
(Phase 5, once the run log and `finish` exist), which is expected.

### Tests for User Story 2 (write first; they must fail)

- [X] T020 [P] [US2] Write `backend/tests/unit/language_kit/test_findings.py`: `Finding(language, path, severity, rule, detail)` with `Severity.ERROR` / `Severity.WARNING`; text form `FAIL <code> <path>: <rule>. <detail>` / `WARN …`; lines cut to ≤ 120 characters and quoted values to 60 characters with `…`; `--json` form is a list of dicts with the five fields
- [X] T021 [P] [US2] Write `backend/tests/unit/language_kit/test_rules_generic.py`, one behaviour per test, for `Required`, `MinCount(n)`, `ExactCount(n)`, `UniqueCasefold`, `MatchesPattern(regex, hint)`, `OneOf(values)` and `ExactlyOnePlaceholder("{name}")` (passes on one `{name}`; fails on zero, two, or any other `{` or `}`); `"TODO"` and empty arrays fail `Required`; each rule returns findings (never raises) for `None`, a wrong type or a wrong shape; each `describe()` is a short rule sentence
- [X] T022 [P] [US2] Write `backend/tests/unit/language_kit/test_rules_language.py` for `NotCatalogued` (onboarding only; the detail points to `kit check` / `kit backfill`), `NotExplanationLanguage` (refuses `en`), `SupportedScript` (refuses RTL `ar he fa ur yi ps sd ug dv` and unspaced `zh ja th lo km my bo`, with the reason), `WhisperSupports`, `VoicesInCatalogue` (voice keys exist in the catalogue with `language.family == code` and `num_speakers == 1`; reports nothing when the context has no catalogue) and `DefaultVoiceAmongVoices`
- [X] T023 [P] [US2] Write `backend/tests/unit/language_kit/test_rules_content.py` for `NamesForEveryVoiceGender(min=10)` (a key for every gender among `voices`, no other key; ≥ 10 names per gender; unique case-insensitive across genders; each 1–20 characters, no digits; detail like "at least 10 names (found 8). Add 2 more female names."), `CoversEveryScenario(turns=5)` (a key for every current scenario id and no other; exactly 5 non-empty turns each), `EachContainsSpecialLetter` (each dictation sentence holds ≥ 1 of `special_letters` when it is non-empty; passes everything when it is empty), and the warnings `PreferTwoVoices` and `PreferBothGenders` (the latter says podcasts will cast hosts of one gender only)
- [X] T024 [P] [US2] Write `backend/tests/unit/language_kit/test_registry.py`: `REQUIREMENTS` holds exactly the 14 requirements of data-model.md § Requirement, in this order, with these `destination` / `producer` / `needed_by`: `code` runtime derived 006; `name` runtime agent 006; `order` runtime derived 008; `voices` runtime chosen 006; `voices[].gender` runtime agent 007; `voices[].speaking_rate` runtime agent 006; `default_voice` runtime chosen 006; `podcast.host_names` runtime agent 007; `podcast.guest_labels` runtime agent 007; `podcast.sample_line` runtime agent 007; `evaluation.special_letters` evaluation agent 006; `evaluation.turns` evaluation agent 006; `evaluation.dictation` evaluation agent 006; `evaluation.loanwords` evaluation agent 006. Each has a description and at least one rule; and the data-model constraints are attached: `code` "ISO 639-1, two lowercase letters"; `name` "non-empty; unique across languages"; `order` "≥ 1; unique"; `voices` "≥ 1; keys unique across all languages"; `voices[].gender` `OneOf("female", "male")`; `voices[].speaking_rate` `OneOf("natural", "fast", "slow")`; `podcast.host_names` `NamesForEveryVoiceGender(min=10)`; `podcast.guest_labels` "≥ 1; unique (case-insensitive); each non-empty"; `podcast.sample_line` "contains `{name}` exactly once and no other `{` or `}`"; `evaluation.special_letters` "letters only, no duplicates; may be empty"; `evaluation.turns` `CoversEveryScenario(turns=5)`; `evaluation.dictation` "exactly 20; unique; each has 3–15 words; when `special_letters` is non-empty, each contains at least one of them"; `evaluation.loanwords` "lowercase single words; may be empty"
- [X] T025 [P] [US2] Write the guard test `backend/tests/unit/language_kit/test_registry_covers_language_data.py` (FR-010, SC-005): every field of `LanguageRecord`, `VoiceRecord`, `PodcastRecord` and `EvaluationSet` maps to a registry path (with `voices[].display_name`, `locale`, `quality` and `key` mapped to `voices`, and `voices` / `podcast` containers excluded), and every registry path maps to a field. A failure message reads exactly: "`<record>.<field>` is per-language data with no entry in `language_kit/registry.py`. Add a Requirement for it (see the language-kit skill, 'Adding a per-language requirement')". Include a seeded test that runs the guard's comparison function against a fake record with an extra `greeting` field and asserts the message names `PodcastRecord.greeting`-style text, plus the reverse direction (a requirement with no field)
- [X] T026 [P] [US2] Write `backend/tests/unit/language_kit/test_context.py`: `RuleContext` holds `scenario_ids` (from the scenario provider via `app.services.factory.get_scenario_provider()`), `catalogued_codes`, `explanation_codes` (from `NATIVE_LANGUAGE_NAMES`), `whisper_codes`, `wordfreq_codes`, and an optional `voice_catalogue`; a pinning test that `faster_whisper.tokenizer._LANGUAGE_CODES` imports and contains `es`, `de` and `it` (plan Complexity Tracking); `wordfreq.available_languages()` contains `es`, `de`, `it`
- [X] T027 [P] [US2] Write `backend/tests/unit/language_kit/test_language_files.py`: reading a catalogued language's runtime file and evaluation file into `LanguageData` values addressed by registry path; a language with no evaluation file yields `None` for every `evaluation.*` path (so `check` fails on them rather than crashing); directories come from a `Workspace` so tests use `tmp_path` copies
- [X] T028 [P] [US2] Write `backend/tests/unit/language_kit/test_workspace.py`: repository root discovery; the runtime and evaluation data directories; `feature_directory` from `.specify/feature.json` and the default output root `<feature_directory>/languages`; `--out DIR` overrides it
- [X] T029 [P] [US2] Write `backend/tests/unit/language_kit/test_check_command.py`: `check <code>` and `check --all` run every requirement that is not `onboarding_only`; summary `check: 2 languages, 14 requirements, 0 failing (es ✓, de ✓)` on a passing fixture and exit 0; a failing item prints its `FAIL` line, the summary marks the language `✗`, and exit is 1; the summary also reports, as information, how many of each language's voices are installed in the voice directory; `--json`; the command changes no file (snapshot the `tmp_path` tree before and after; US2 scenario 4); an uncatalogued code exits 2; and a real-repository test that `check de` passes
- [X] T030 [P] [US2] Write the seeded-omission test `backend/tests/unit/language_kit/test_seeded_omissions.py` (SC-004): parametrised over every requirement that is not `onboarding_only` × every language in `evaluated_languages()`, on a `tmp_path` copy of that language's two files, remove the item and, separately, break it (one invalid value per requirement, defined in a table in the test), then assert `check` fails naming exactly that language and path and passes every other item

### Implementation for User Story 2

- [X] T031 [P] [US2] Implement `backend/language_kit/findings.py` (`Severity`, `Finding`, text and JSON formatting with the 120/60 limits as named constants). T020 passes
- [X] T032 [US2] Implement `backend/language_kit/rules.py`: the `Rule` ABC (`check(value, context) -> list[Finding]`, `describe() -> str`, `severity`) and every rule class named in T021–T023, one class per rule, thresholds as constructor arguments. T021–T023 pass
- [X] T033 [US2] Implement `backend/language_kit/context.py`: `RuleContext` (frozen) and `gather_rule_context()` reading the app facts listed in T026 (scenario ids through `app.services.factory`, `NATIVE_LANGUAGE_NAMES` via `app.practice_languages`, `faster_whisper.tokenizer._LANGUAGE_CODES`, `wordfreq.available_languages()`). T026 passes
- [X] T034 [US2] Implement `backend/language_kit/registry.py`: `Destination` (`RUNTIME`, `EVALUATION`), `Producer` (`AGENT`, `CHOSEN`, `DERIVED`), frozen `Requirement(path, destination, producer, needed_by, description, rules, onboarding_only=False)` and `REQUIREMENTS` as specified in T024 (`NotCatalogued`, `NotExplanationLanguage`, `SupportedScript` and `WhisperSupports` sit on `code` with `onboarding_only=True` where they only make sense before cataloguing). T024 passes; then add the comparison function the guard uses and make T025 pass
- [X] T035 [P] [US2] Implement `backend/language_kit/workspace.py` (`Workspace`: repository root, runtime directory, evaluation directory, voice directory from `OPEN_LANGUAGE_VOICE_DIR` else `~/.local/share/piper-voices`, output root). T028 passes
- [X] T036 [US2] Implement `backend/language_kit/language_files.py`: `LanguageData` (complete or partial values of one language, addressed by registry path) and `read_language(code, workspace) -> LanguageData`. T027 passes
- [X] T037 [US2] Write `backend/tests/unit/language_kit/test_cli.py` (usage error → exit 2 with a one-line message; `--help` lists the commands; unknown command exits 2; `python -m language_kit` with no command prints usage and exits 2). It must fail: `backend/language_kit/cli.py` does not exist yet
- [X] T038 [US2] Implement the command layer: `backend/language_kit/cli.py` (argparse with the common options `--dry-run`, `--json`, `--out`; each command a small `Command` object; exit-code constants `EXIT_OK = 0`, `EXIT_FINDINGS = 1`, `EXIT_USAGE = 2`, `EXIT_EXTERNAL = 3`), `backend/language_kit/composition.py` (`build_kit()` wiring the real collaborators that exist so far — `Workspace`, the system clock and `gather_rule_context()`; tests pass fakes. The voice catalogue, voice downloader and command runner are added to `build_kit()` by T073, once T065, T066 and T069 build them; until then no command calls them: `check` never does, and T043 requires that `apply` touches neither for a pack that changes no voice), `backend/language_kit/__main__.py`, and the `check` command. T029, T030 and T037 pass

**Checkpoint**: `kit check de` exits 0; `kit check es` fails only on `evaluation.special_letters`,
`evaluation.turns`, `evaluation.dictation` and `evaluation.loanwords`; the guard and seeded tests pass;
`check` writes nothing.

---

## Phase 4: User Story 4 - The kit stays current as features add per-language needs (Priority: P2)

**Goal**: packs (full and partial) generated from the registry, validation, canonical rendering, an
atomic apply, `backfill` and `requirements`. Spanish's evaluation set is written **through the kit's
backfill** in T078 (Phase 5), once the run log, `verify`, `report` and `finish --pack` exist, so that
the backfill run gets its run log and report (FR-018, FR-027).

**Independent Test**: quickstart §8 on a scratch branch: register a sample requirement → `check --all`
fails on it only for every language → `backfill --all` writes packs with only that item → fill and
apply → only that line changes in each file → `check --all` passes, and `SKILL.md` is untouched.

### Tests for User Story 4 (write first; they must fail)

- [ ] T039 [P] [US4] Write `backend/tests/unit/language_kit/test_pack.py`: parse a pack with `tomllib`; a TOML syntax error becomes one finding `FAIL <code> pack: line N: <message>`; a key not in the registry is an error naming it (e.g. `guest_label`); `order`, `locale` or `quality` in a pack is an error "derived by the kit; remove it"; a voice's `display_name` is optional in a pack (an override of the derived name; a non-empty string of 1–40 characters, else an error); `"TODO"` and `[]` fail their rules; `missing(registry)` lists absent paths; `merged_onto(existing)` replaces only the items present in the pack (`code` always present) and keeps every other item; `findings(registry, context)` runs every rule on the merged data and a pack is valid when no `ERROR` remains (warnings allowed)
- [ ] T040 [P] [US4] Write `backend/tests/unit/language_kit/test_template.py`: the full pack holds every registry item in registry order (except `order` and voice `display_name`/`locale`/`quality`; the `[[voices]]` guidance says `display_name` may be added to override the derived name), each preceded by the guidance block of contracts/pack-format.md § "Guidance comments" (`# ── <path> ─── <producer> · needed by <feature>`, description, `# Rules: …` from each rule's `describe()`, `# Example (<Language>): …`); `code` and `name` filled, `default_voice` and `sample_line` and `special_letters` `"TODO"`, arrays `[]`, `[evaluation.turns]` with `[]` for **every current scenario**; the example comes from the first catalogued language that passes that item, preferring German; voice candidates (key, region, quality, size) listed in a comment above `[[voices]]`; a partial pack holds `code` plus only the given paths; and a fake extra `Requirement` passed in appears in the template with no other change (FR-009)
- [ ] T041 [P] [US4] Write `backend/tests/unit/language_kit/test_render.py`: rendering `LanguageData` gives exactly two texts (runtime and evaluation) with the header of contracts/data-files.md, registry key order and `tomli-w` formatting; `render(load(f)) == f` for every committed file under `backend/app/language_data/languages/` and `backend/tests/integration/practice_languages/evaluation/`; derived values on apply: `order` = max existing + 1, and for a newly added voice `display_name = "<Name> (<country_english>)"` (e.g. "Paola (Italy)") unless the pack gives one, in which case the pack's value is written (e.g. "David (Spain)" for a catalogue name `davefx`), `locale = language.code` (e.g. `it_IT`), `quality` from the catalogue; existing voices keep their stored derived values without consulting the catalogue
- [ ] T042 [P] [US4] Write `backend/tests/unit/language_kit/test_voice_interfaces.py` for the abstractions only: `VoiceCandidate(key, name, region, country, quality, size_bytes, files)` with `files` holding `relative_path` and `md5`; a `FakeVoiceCatalogue` (`candidates(code)`, `voice(key)`) and `FakeVoiceDownloader` (`ensure(voice)`) in `backend/tests/unit/language_kit/fakes.py` substitute for the ABCs (LSP)
- [ ] T043 [P] [US4] Write `backend/tests/unit/language_kit/test_apply.py`: validation errors → exit 1 and no file changes; voices are ensured **before** any file is written, and only voices that the merged data adds or that are missing from the voice directory (a pack that changes no voice touches neither the catalogue nor the network, so apply works offline); a download failure → exit 3 and the repository untouched; both files are written to temporaries beside their targets and `os.replace`d; if the second replace fails, the first target is restored from its backup; rendered files equal to the current ones with all voices present → `nothing-to-do`, exit 0, no write; `--dry-run` prints `would write <path> (+A −R lines)` and `would download <key> (<size>)` and changes nothing; a partial pack changes only its items byte-for-byte (contracts/pack-format.md § "Partial packs"); no other language's files change (FR-017)
- [ ] T044 [P] [US4] Write `backend/tests/unit/language_kit/test_validate_command.py`: `validate <code> [--pack PATH]` (default `<out>/<code>/pack.toml`) parses, merges onto the language's existing data if catalogued, prints every finding; exit 0 with warnings only, 1 with errors; read-only; a missing pack exits 2 with `→ next: kit.sh scaffold <code> --name <Name>`
- [ ] T045 [P] [US4] Write `backend/tests/unit/language_kit/test_backfill_command.py`: `backfill <code>` / `--all` lists, per language, the failing items and writes `<out>/<code>/backfill-pack.toml` holding only those (plus `code`) with guidance and an example from a passing language; a language with nothing missing is `nothing-to-do`; an existing `backfill-pack.toml` is never overwritten (reported, `nothing-to-do`); `--dry-run` writes nothing; summary ends `→ next: kit.sh finish <code> --pack <path>`
- [ ] T046 [P] [US4] Write `backend/tests/unit/language_kit/test_requirements_command.py`: `requirements` prints the registry as a table (path, producer, needed by, rules), read-only, exit 0; `--json` lists the same
- [ ] T047 [P] [US4] Write `backend/tests/unit/language_kit/test_backfill_flow.py` (US4 scenarios 1–3, quickstart §8 automated): with a fake extra `Requirement("podcast.greeting", …)` injected into a `build_kit()` built over `tmp_path` copies of the data and a matching record field, `check --all` fails on that path only for every language; `backfill --all` writes packs holding only `code` and `greeting`; after filling and `apply --pack`, the diff of each runtime file is the added `greeting` line only and `check --all` passes

### Implementation for User Story 4

- [ ] T048 [US4] Implement `backend/language_kit/pack.py`: `LanguagePack` (`parse`, `missing`, `merged_onto`, `findings`). T039 passes
- [ ] T049 [US4] Implement `backend/language_kit/template.py`: full-pack and partial-pack text from the registry, examples from passing languages, candidate-voice comment. T040 passes
- [ ] T050 [US4] Implement `backend/language_kit/render.py`: canonical runtime and evaluation text with `tomli_w`, header, registry key order, derived values. T041 passes
- [ ] T051 [P] [US4] Declare the boundary interfaces in `backend/language_kit/voices.py`: `VoiceCandidate`, `VoiceCatalogue` ABC (`candidates(code)`, `voice(key)`), `VoiceDownloader` ABC (`ensure(voice)`); add the fakes in `backend/tests/unit/language_kit/fakes.py`. T042 passes (the HTTP implementations come in Phase 5)
- [ ] T052 [US4] Implement `backend/language_kit/apply.py` (validate → ensure voices → atomic two-file write with restore) and the `apply` command in `backend/language_kit/cli.py`. T043 passes
- [ ] T053 [US4] Implement the `validate`, `backfill` and `requirements` commands in `backend/language_kit/cli.py` (wired in `composition.py`). T044, T045, T046 and T047 pass

**Checkpoint**: the full suite is green; T047 proves the backfill flow end to end on `tmp_path` copies;
`kit check de` still passes and `kit check es` still fails only on `evaluation.*` (backfilled in T078).

---

## Phase 5: User Story 1 - Maintainer adds a new practice language with the kit (Priority: P1) 🎯 MVP

**Goal**: the whole onboarding path, from `prereq` to `finish` and a report, behind a short skill; then
**Italian onboarded through the skill** as the acceptance test (FR-024).

**Independent Test**: quickstart §5 in a fresh session: the only hand-edited file is `pack.toml`, the
only repository files written are `it.toml` (runtime) and `evaluation/it.toml`, every suite passes,
`check --all` reports 3 languages and 0 failing; then quickstart §6: Italian works end to end.

### Tests for User Story 1 (write first; they must fail)

- [ ] T054 [P] [US1] Write `backend/tests/unit/language_kit/test_voice_catalogue.py` for `PiperVoiceCatalogue` (HTTP faked by injecting a fetch function; fixture: a trimmed `voices.json` with Italian, German multi-speaker `de_DE-mls-medium` and Spanish entries): fetches `https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json`; caches it in `~/.cache/open-language/piper-voices.json` (path injectable) for 24 hours using a fake `Clock`, refetching after expiry; `candidates("it")` returns only voices with `language.family == "it"` and `num_speakers == 1`, with region, country, quality, `size_bytes` (`.onnx` + `.onnx.json`) and per-file MD5; a network error raises a kit error whose message says voice discovery needs the network
- [ ] T055 [P] [US1] Write `backend/tests/unit/language_kit/test_voice_downloader.py` for `HttpVoiceDownloader` (HTTP faked): downloads the `.onnx` and `.onnx.json` of a voice into the voice directory; checks each against its `md5_digest`; skips a file already present with the right digest; on a mismatch deletes the partial file and raises; returns the keys it downloaded and the elapsed time (for the run log, SC-002)
- [ ] T056 [P] [US1] Write `backend/tests/unit/language_kit/test_prerequisites.py` (research R7, FR-011–FR-013): checks run in order — code is two lowercase letters; not catalogued (points to `kit check` / `kit backfill`); not the explanation language; left-to-right with spaced words; Whisper supports it; at least one single-speaker voice — and stop at the first failure with exit 2 and nothing written; a `wordfreq` gap is a `WARN` that does not stop (the adherence benchmark will be "not run"); voices of one gender only is a `WARN`; success prints `prereq it: Italian can be onboarded (6/6 checks, 1 warning)` style summary, one `voice <key> <country> <quality> <N> MB` line per candidate, and `→ next: kit.sh scaffold it --name <Name>`
- [ ] T057 [P] [US1] Write `backend/tests/unit/language_kit/test_scaffold_command.py`: `scaffold <code> --name <Name>` runs `prereq` first (failure → exit 2, nothing written); writes `<out>/<code>/pack.toml` from the template with the candidate voices; an existing pack is never overwritten (`nothing-to-do`); `--name` is required; `--dry-run` writes nothing; summary ends `→ next: kit.sh validate <code>`
- [ ] T058 [P] [US1] Write `backend/tests/unit/language_kit/test_verify.py` with a fake `CommandRunner` (`run(argv, log) -> SuiteResult`): runs `.venv/bin/pytest`, `.venv/bin/ruff check .`, `.venv/bin/black --check .` and `.venv/bin/mypy language_kit app/language_data` with `backend/` as the working directory (so `backend/pyproject.toml` supplies `testpaths`, the `benchmark` / `claude_live` deselection and the coverage floor), and `npm run lint`, `npm test -- --run`, `npm run test:e2e` with `frontend/` as the working directory; assert each suite's `argv` and working directory; prints one line per suite with pass/fail and counts; for a failure, at most 20 test ids and the log path; logs go to `<out>/<code>/logs/<suite>.log` with `--language <code>`, else `<out>/_logs/`; `--backend-only` skips the three frontend suites and records them as skipped (never silent); `--dry-run` prints `would run <suite> (in <directory>)` per suite, runs nothing and writes no log; any failing suite → exit 3
- [ ] T059 [P] [US1] Write `backend/tests/unit/language_kit/test_run_log.py`: each command that acts on a language appends one JSON line to `<out>/<code>/run-log.jsonl` with `at` (ISO 8601 from the `Clock`), `command` (`prereq` | `scaffold` | `validate` | `apply` | `verify` | `check` | `backfill` | `bench`), `outcome` (`ok` | `findings` | `failed` | `nothing-to-do` | `dry-run`), `findings`, `files_written` (repository-relative), `voices_downloaded`, `suites` (`{name, passed, failed, skipped, log}`), `benchmarks`; a `--dry-run` writes no line
- [ ] T060 [P] [US1] Write `backend/tests/unit/language_kit/test_report.py`: `report <code>` regenerates `<out>/<code>/report.md` in full from `run-log.jsonl` with a header (language, dates, kit commands run) and the sections **Applied** (data files, voices), **Checks** (suites, the completeness check; skipped frontend suites stated), **Benchmarks** (each figure against its threshold, or "not run" with the reason), **Open items** (misses, warnings, review-sheet rows still to judge) and **Not checked** (the fixed list: listening to the voices; voice genders asserted, not checked by listening; a screen-reader pass; offline use; a human speaking into the microphone); re-running gives the same bytes; `--dry-run` prints it without writing
- [ ] T061 [P] [US1] Write `backend/tests/unit/language_kit/test_finish_command.py`: `finish <code> [--pack PATH] [--backend-only]` runs `apply` (with the same `--pack`, default `<out>/<code>/pack.toml`) → `verify` → `check <code>` → `report <code>`; `finish es --pack <out>/es/backfill-pack.toml` applies a partial pack and writes the report, so a backfill run gets the same record as an onboarding run (FR-018, FR-027); stops at the first step with exit ≥ 2 and still writes the report; a validation error stops with exit 1 before anything is written; on a completed language every step reports `nothing-to-do` except `verify` (which runs) and `report` (which regenerates) (quickstart §9)
- [ ] T062 [P] [US1] Write `backend/tests/unit/language_kit/test_dry_run.py` (FR-005, quickstart §4): for `scaffold`, `apply`, `backfill`, `verify`, `finish` and `report` with `--dry-run`, and for `check`, `validate`, `requirements` and `prereq`, a snapshot of the `tmp_path` repository and output root is unchanged afterwards (the voice-catalogue cache excepted for `prereq`)
- [ ] T063 [P] [US1] Write `backend/tests/unit/language_kit/test_kit_script.py`: running `.claude/skills/language-kit/kit.sh` from a temporary copy without `backend/.venv` exits 2 with "backend/.venv is missing: run ./run.sh --setup"; with the venv it passes its arguments through (`kit.sh requirements` exits 0)
- [ ] T064 [P] [US1] Write `backend/tests/unit/language_kit/test_skill_contract.py` (contracts/cli.md § Skill; US4 scenario 5): `.claude/skills/language-kit/SKILL.md` is ≤ 150 lines; frontmatter `name: language-kit` and a description containing "add a language", "support Italian", "new practice language", "per-language data" and "backfill languages"; the five sections appear in order (*When to use*, *Onboard a language*, *Backfill after a new requirement*, *Adding a per-language requirement*, *Rules*); no registry path (e.g. `podcast.sample_line`) appears in it, so adding a requirement never needs a skill edit

### Implementation for User Story 1

- [ ] T065 [P] [US1] Implement `PiperVoiceCatalogue` (24 h cache, single-speaker filter, `Clock` injected) in `backend/language_kit/voices.py`, constants for the URL, cache path and TTL. T054 passes
- [ ] T066 [P] [US1] Implement `HttpVoiceDownloader` (`urllib.request`, `hashlib.md5`, partial-file cleanup) in `backend/language_kit/voices.py`, with the voice-file base URL that `run.sh` uses. T055 passes
- [ ] T067 [US1] Implement `backend/language_kit/prerequisites.py` (the R7 checks, the RTL and unspaced code sets as named constants) and the `prereq` command. T056 passes
- [ ] T068 [US1] Implement the `scaffold` command in `backend/language_kit/cli.py` on top of `prerequisites.py` and `template.py`. T057 passes
- [ ] T069 [P] [US1] Implement `backend/language_kit/verify.py`: `CommandRunner` ABC, `SubprocessCommandRunner`, `SuiteResult`, the suite list, pytest/Vitest/Playwright summary parsing; and the `verify` command. T058 passes
- [ ] T070 [P] [US1] Implement `backend/language_kit/run_log.py` and append an entry from every acting command (`prereq`, `scaffold`, `validate`, `apply`, `verify`, `check <code>`, `backfill`). T059 passes
- [ ] T071 [US1] Implement `backend/language_kit/report.py` and the `report` command. T060 passes
- [ ] T072 [US1] Implement the `finish` command (with `--pack PATH`, passed through to `apply`) in `backend/language_kit/cli.py`. T061 and T062 pass
- [ ] T073 [US1] Wire the real collaborators in `backend/language_kit/composition.py` (`PiperVoiceCatalogue`, `HttpVoiceDownloader`, `SubprocessCommandRunner`, system clock, `Workspace`); with the network, run `kit prereq it` by hand and confirm it lists `it_IT-paola-medium`, `it_IT-riccardo-x_low`, `it_IT-serena-medium`, `it_IT-serena-high`
- [ ] T074 [P] [US1] Create `.claude/skills/language-kit/kit.sh` (executable; ~10 lines: resolve the repository root from the script's location, exit 2 with "backend/.venv is missing: run ./run.sh --setup" if absent, else `cd backend && exec .venv/bin/python -m language_kit "$@"`). T063 passes
- [ ] T075 [US1] Write `.claude/skills/language-kit/SKILL.md` per contracts/cli.md § Skill and research R12: *When to use*; *Onboard a language* (`prereq` → choose voices from its list → `scaffold` → fill `pack.toml` → `validate` until clean → `finish` → `bench` → `report`, with what to do between commands); *Backfill after a new requirement* (`backfill` → fill each `backfill-pack.toml` → `validate --pack` until clean → `finish <code> --pack <path>` for each, so tests run and a report is written); *Adding a per-language requirement* (record field + loader, test first → `Requirement` in the registry → `backfill --all` → fill → `finish <code> --pack <path>` each → `check --all`); *Rules* (never read app source while onboarding; never edit generated data files by hand; set voice genders from the voice's name or model card; Spanish and German examples are guidance, not text to translate word for word). No requirement list. T064 passes
- [ ] T076 [US1] Make existing tests catalogue-driven so a language added by data alone keeps the suite green (FR-019): in `backend/tests/unit/practice_languages/test_catalog.py` replace the three exact-list assertions — line 42 `list(PRACTICE_LANGUAGES) == ["es", "de"]`, line 46 names `== ["Spanish", "German"]` and line 50 the default-voice list — with assertions that Spanish then German lead the catalogue in `order` (names and default voices checked for those two); parametrise both `["es", "de"]` parametrisations in `backend/tests/unit/podcasts/test_casting.py` (lines 26 and 42) over `list(PRACTICE_LANGUAGES)`; parametrise the two 007 benchmarks, `backend/tests/integration/podcasts/test_host_language_benchmark.py:25` and `backend/tests/integration/conversation_summary/test_summary_benchmark.py:53`, over `list(PRACTICE_LANGUAGES)` so Italian is benchmarked for host language and summary too (they stay behind the `benchmark` marker); search `backend/tests` and `frontend/src` / `frontend/e2e` for any other assertion that exactly two languages exist and fix it the same way. Commit this before T080 so the Italian commit holds only generated files (SC-001)
- [ ] T077 [US4] Extend `backend/tests/unit/language_kit/test_check_command.py` with a real-repository test: `check --all` passes for every catalogued language (FR-021). It fails until T078 writes `evaluation/es.toml`; do T077 and T078 together and commit them as one change, so the suite is never left red
- [ ] T078 [US4] Backfill Spanish **through the kit** (research R2): run `kit backfill es`; fill `specs/008-language-onboarding-kit/languages/es/backfill-pack.toml` with `special_letters = "áéíóúüñ"`, exactly 5 natural learner turns for every scenario id listed, exactly 20 unique dictation sentences of 3–15 words each containing at least one of `áéíóúüñ`, and lowercase single-word Spanish loanwords (e.g. `"hotel"`, `"taxi"`, `"ok"`); run `kit validate es --pack …` until it reports 0 errors; then `kit finish es --pack specs/008-language-onboarding-kit/languages/es/backfill-pack.toml` (apply → verify → check → report). The only repository file written is `backend/tests/integration/practice_languages/evaluation/es.toml`; `es.toml` (runtime) is unchanged and the pinning test still passes; T077 passes; `test_render.py`'s round-trip now covers `evaluation/es.toml`; `languages/es/` holds `backfill-pack.toml`, `run-log.jsonl` (from `backfill` on) and `report.md` (FR-027). `kit check --all` → `check: 2 languages, 14 requirements, 0 failing (es ✓, de ✓)`, exit 0 (quickstart §2)
- [ ] T079 [US1] Run `kit verify` and `kit check --all` on the branch; both pass. Copy the learner database for quickstart §10: `cp ~/.local/share/open-language/app.db` (or the `db_path` from settings) to the scratchpad as `pre-008.db`

### Acceptance: onboard Italian with the skill (FR-024; SC-001, SC-002, SC-003)

- [ ] T080 [US1] In a **fresh Claude Code session** with only the `language-kit` skill invoked (so the session record can be checked for SC-003), with a timer started, onboard Italian: `kit prereq it` → `kit scaffold it --name Italian` → fill `specs/008-language-onboarding-kit/languages/it/pack.toml` (voices per research R13: `it_IT-paola-medium` female and default, `it_IT-riccardo-x_low` male; ≥ 10 female and ≥ 10 male Italian host names; Italian guest labels; a sample line with exactly one `{name}`; `special_letters = "àèéìòù"`; 5 turns for every scenario; 20 dictation sentences of 3–15 words each with at least one of `àèéìòù`; loanwords) → `kit validate it` until 0 errors → `kit finish it`. Expect: exactly two repository files written, `backend/app/language_data/languages/it.toml` and `backend/tests/integration/practice_languages/evaluation/it.toml`; both voices in the voice directory with matching MD5; every suite passes; `check --all` → `3 languages, 14 requirements, 0 failing`; `report.md` written
- [ ] T081 [US1] Verify SC-001–SC-003 and commit Italian on its own: `git status` shows only the two generated files plus `specs/008-language-onboarding-kit/languages/it/` (`pack.toml`, `run-log.jsonl`, `report.md`, logs); the session record shows `Read`/`Edit` calls only on `SKILL.md`, `pack.toml` and files under `languages/it/`, none under `backend/app`, `frontend/src` or `backend/tests`; working time from `prereq` to `finish` exit 0, minus the download time in `run-log.jsonl`, is under 30 minutes. Record the three results in `specs/008-language-onboarding-kit/validation.md`
- [ ] T082 [US1] Walk quickstart §6 in the running app (`./run.sh`) and §10 (compare every table except `app_settings` and `voice_choices` against `pre-008.db` before saving Settings, using the helper in `backend/tests/integration/practice_languages/test_upgrade_preserves_data.py`): three practice-language cards with arrow-key movement, Italian voices only, an Italian conversation with accented transcription, every learning tool, Beginner level and Strict corrections, flashcards, a Panel podcast with two Italian hosts in their own voices and the sample line, Summary in Italian and English, Past Chats labels; a keyboard and contrast check of the three cards (Constitution IV). Record results (SC-008, SC-009) in `specs/008-language-onboarding-kit/validation.md`

**Checkpoint**: Italian is a supported practice language, added by data alone; `git diff master...HEAD
-- backend/app frontend/src` shows no Italian-specific code (SC-008).

---

## Phase 6: User Story 3 - Benchmarks run for any language with one command (Priority: P2)

**Goal**: the adherence and transcription benchmarks become language-independent (selected by
`OPEN_LANGUAGE_BENCH_LANGUAGE` / `OPEN_LANGUAGE_BENCH_OUT`) and `kit bench <code>` runs them, writing
`benchmark-results.md` and `review-sheet.md` in 006's form.

**Independent Test**: `kit bench de` writes German results from `evaluation/de.toml` (006's data
unchanged) in 006's format; `kit bench it` writes the same files with no Italian benchmark code;
stopping Ollama makes `kit bench it --adherence` exit 3 and write nothing (quickstart §7).

### Tests for User Story 3 (write first; they must fail)

- [ ] T083 [P] [US3] Update `backend/tests/integration/practice_languages/test_text_purity.py` first: `foreign_words(text, target, others)` (and its helpers) take the target and the other languages as parameters; `other_languages(target)` is English plus every other catalogued practice language that `wordfreq` covers (for German with Italian catalogued: `en`, `es`, `it`); the Zipf ≥ 3.0 and margin ≥ 1.5 thresholds and the "skip capitalised tokens after the first" rule are unchanged; loanwords come from `evaluation_set(target).loanwords`
- [ ] T084 [P] [US3] Write `backend/tests/integration/practice_languages/test_bench_environment.py` for a new helper module `bench_environment.py`: `bench_languages()` reads `OPEN_LANGUAGE_BENCH_LANGUAGE`, default every code in `evaluated_languages()`; `bench_output_dir(code)` reads `OPEN_LANGUAGE_BENCH_OUT`, default `specs/<feature>/languages/<code>/` from `.specify/feature.json`; the results writer produces 006's sections (the adherence figure; one transcription table per voice) plus a machine-readable `benchmark-results.json` holding `BenchmarkResult` fields (`kind`, `language`, `voice`, `model`, `passed`, `total`, `threshold` as `"≥ 95%"` / `"≥ 18/20"`, `met`, `not_run_reason`, `results_file`, `review_sheet`); the review-sheet header names the language and the other languages from the catalogue (not "German" / "English or Spanish") and has an empty Verdict column
- [ ] T085 [P] [US3] Write `backend/tests/unit/language_kit/test_bench_command.py` with a fake `CommandRunner` and fake availability probes: `bench <code>` sets `OPEN_LANGUAGE_BENCH_LANGUAGE=<code>` and `OPEN_LANGUAGE_BENCH_OUT=<out>/<code>/` and runs `pytest -m benchmark -s` on both benchmark files (`--adherence` / `--transcription` select one); prints each figure against its threshold and the paths of `benchmark-results.md` and `review-sheet.md`; a missed threshold → exit 1 with both files written; Ollama, the model or a voice unavailable → exit 3, a message naming what is missing and how to get it, and nothing written (US3 scenario 4); a language `wordfreq` does not cover → adherence "not run" with the reason; results are appended to the run log as `benchmarks`; `--dry-run` writes nothing

### Implementation for User Story 3

- [ ] T086 [US3] Generalise `backend/tests/integration/practice_languages/text_purity.py` (`foreign_words`, `_checked_words`, `_is_foreign` take the target and other languages; drop `GERMAN = "de"` and the hard-coded `("en", "es")`). T083 passes
- [ ] T087 [US3] Implement `backend/tests/integration/practice_languages/bench_environment.py` (environment resolution, results and review-sheet writers, JSON sidecar). T084 passes
- [ ] T088 [US3] `git mv backend/tests/integration/practice_languages/test_german_benchmark.py test_adherence_benchmark.py` and parameterise it by `bench_languages()`: scripted turns from `evaluation_set(code).turns` across every scenario, foreign-word check against `other_languages(code)`, threshold ≥ 95% clean replies (006), results and review sheet written via `bench_environment.py` **before** asserting; keep the `benchmark` marker; every function ≤ 20 lines
- [ ] T089 [US3] Generalise `backend/tests/integration/practice_languages/test_transcription_benchmark.py`: parameterise by `bench_languages()` and **every** voice in `voices_for(code)`; the special-letter check reads `evaluation_set(code).special_letters` instead of `[äöüß]` (no check when empty); the language hint is the code; threshold ≥ 18 of 20 sentences with word error rate ≤ 20% and special-letter words kept (006); one table per voice written before asserting; keep the `benchmark` marker
- [ ] T090 [US3] Implement `backend/language_kit/bench.py` (availability probes for Ollama, the model and the installed voices; the pytest run with the two environment variables; reading `benchmark-results.json`) and the `bench` command in `backend/language_kit/cli.py`; add `bench` to the dry-run test in `backend/tests/unit/language_kit/test_dry_run.py`. T085 passes
- [ ] T091 [US3] Run `kit bench de` (FR-023, SC-007): `specs/008-language-onboarding-kit/languages/de/benchmark-results.md` and `review-sheet.md` exist in 006's format, computed from `evaluation/de.toml`; note in `validation.md` that its content equals 006's `german_evaluation_set.py` (pinned by T016) and compare the figures with 006's recorded run (parity of data and format, not of figures; plan interpretation 7)
- [ ] T092 [US3] Run `kit bench it` then `kit report it` (FR-024): Italian results and review sheet in `specs/008-language-onboarding-kit/languages/it/`; a missed threshold appears under *Open items* in `report.md`; then stop Ollama and confirm `kit bench it --adherence` exits 3, names Ollama and writes nothing. Record in `validation.md`

**Checkpoint**: both benchmarks run for any evaluated language from data alone; German and Italian
results and review sheets are recorded.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: FR-026 documentation, the remaining quickstart checks, and the final gates.

- [ ] T093 [P] FR-026: add one line to the Constitution Check section of `.specify/templates/plan-template.md`: "Does this feature add per-language data? Then it registers a requirement in the language kit (`.claude/skills/language-kit`) in the same change"
- [ ] T094 [P] FR-026: update `CLAUDE.md`: a short "Per-language data" note (registry, `kit backfill`, the guard test); in Project Overview add 008 and Italian; in Active Technologies add `tomli-w` (dev) and the Piper voice catalogue as a kit-only data source; in Domain modules describe `app/language_data/` (leaf, the only place language data lives; `catalog.py` and `voices.py` adapt it) and `backend/language_kit/` (dev tooling, never imported by the app); add a 008 entry to Recent Changes; note `run.sh` reads voices from `python -m app.language_data voice-keys`
- [ ] T095 [P] Update `docs/architecture.md`: the language data files and loader, the kit and its registry, the evaluation files, the generalised benchmarks, and under § "Open items": Italian's benchmark results and misses, plus two out-of-scope lint backlogs found while planning 008 (`mypy app` reports 232 errors in 53 files and `prettier --check src` flags 132 files, both on 2026-10-06; `kit verify` therefore type-checks only `language_kit` and `app/language_data`, and ESLint is the frontend lint gate)
- [ ] T096 [P] Update `README.md`: Italian as a practice language (three languages), and how to add a language with the `language-kit` skill
- [ ] T097 Run quickstart §4 (read-only and dry-run commands leave `git status` unchanged), §9 (idempotency: `kit scaffold it --name Italian; kit apply it; kit backfill --all; kit finish it --backend-only` → `nothing-to-do`, and `git status` shows only `languages/it/report.md`, `run-log.jsonl` and logs, the kit's own run records, which plan.md § "Spec interpretations" 8 places outside SC-006) and §11 (`OPEN_LANGUAGE_VOICE_DIR=$(mktemp -d) ./run.sh --setup` downloads six voices with no edit to `run.sh`); record results in `specs/008-language-onboarding-kit/validation.md`
- [ ] T098 Run quickstart §8 on a scratch branch (register `podcast.greeting`, `check --all` fails on it only, `backfill --all` writes three packs with only `code` and `greeting`, fill and `finish <code> --pack … --backend-only` each, each runtime diff is the `greeting` line only, `check --all` passes, `SKILL.md` diff empty); discard the branch; record the result in `validation.md`
- [ ] T099 Final gates from the repository root: `cd backend && .venv/bin/pytest` (coverage ≥ 90% over `app` and `language_kit`, zero skipped), `.venv/bin/ruff check .`, `.venv/bin/black --check .`, `.venv/bin/mypy language_kit app/language_data`; `cd frontend && npm run lint && npm test -- --run && npm run test:e2e`. All pass

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup. **Blocks every story.** T006 (pinning) passes before
  T011–T013 change anything.
- **US2 (Phase 3)**: after Foundational.
- **US4 (Phase 4)**: after US2 (pack validation and backfill run the registry and rules; `apply` uses
  `check`'s data reading).
- **US1 (Phase 5)**: after US4 (`scaffold` uses the template; `finish` uses `apply` and `validate`).
  T077–T078 (Spanish backfill, a US4 deliverable) need `verify`, the run log, `report`, `finish --pack`
  and the real wiring (T069–T073). T080 (Italian) needs every other US1 task, and T076 committed first.
- **US3 (Phase 6)**: after Foundational for T083–T089 (benchmark generalisation); T090 needs the
  command layer (US2) and run log (T070); T092 needs Italian (T080).
- **Polish (Phase 7)**: after every story; T098 needs US4, T097 needs US1.

### Story dependency graph

```text
Setup ─► Foundational ─► US2 (check) ─► US4 (pack · apply · backfill · es) ─► US1 (prereq … finish · skill · Italian) ─► Polish
                   └──────────────► US3 tests + benchmark generalisation (T083–T089) ──► T090 (needs CLI, run log) ─► T091 · T092 (needs Italian)
```

### Within each story

- Tests first, seen to fail; then the smallest implementation that passes.
- Value objects (`findings`, `records`) → rules and registry → readers and renderers → commands → the
  real HTTP and subprocess collaborators → hand runs through the kit.

---

## Parallel Opportunities

- **Setup**: T002 and T003 after T001.
- **Foundational**: T004, T005, T007, T008 together (T006 first or alongside, it touches no new code);
  T016 alongside T009–T010.
- **US2**: all tests T020–T030 together (separate files); then T031 and T035 alongside T032.
- **US4**: tests T039–T047 together; T051 alongside T048–T050.
- **US1**: tests T054–T064 together; then T065, T066, T069, T070 and T074 together.
- **US3**: T083–T085 together, and T083–T089 can run alongside Phases 3–5 by a second developer.
- **Polish**: T093–T096 together.

### Parallel example: User Story 2

```bash
# All US2 tests at once (separate files):
Task: "Findings formatting tests in backend/tests/unit/language_kit/test_findings.py"
Task: "Generic rule tests in backend/tests/unit/language_kit/test_rules_generic.py"
Task: "Language rule tests in backend/tests/unit/language_kit/test_rules_language.py"
Task: "Content rule tests in backend/tests/unit/language_kit/test_rules_content.py"
Task: "Registry tests in backend/tests/unit/language_kit/test_registry.py"
Task: "Guard test in backend/tests/unit/language_kit/test_registry_covers_language_data.py"
Task: "Seeded omissions in backend/tests/unit/language_kit/test_seeded_omissions.py"
```

### Parallel example: User Story 1

```bash
# The boundary collaborators, once their tests exist:
Task: "PiperVoiceCatalogue in backend/language_kit/voices.py"        # T065 and T066 share a file: run one after the other
Task: "CommandRunner and verify in backend/language_kit/verify.py"
Task: "Run log in backend/language_kit/run_log.py"
Task: "kit.sh in .claude/skills/language-kit/kit.sh"
```

---

## Implementation Strategy

### MVP first

1. Phase 1 + Phase 2: data files in place, nothing changed for learners.
2. Phase 3 (US2): **stop and validate**: `kit check de` passes and seeded omissions are caught. This
   is the smallest useful slice: it tells the maintainer and agent exactly what a language lacks.
3. Phase 4 (US4) and Phase 5 (US1): the full onboarding path, proven by Italian. US1 is the story the
   feature exists for, so the feature is not shippable until T080–T082 pass.

### Incremental delivery

1. Foundation → the app reads language data from files (no visible change).
2. + US2 → `check` and the guard.
3. + US4 → packs, apply, backfill, proven on `tmp_path` copies.
4. + US1 → `prereq` to `finish`, the skill; Spanish's evaluation set through `finish --pack`
   (`check --all` passes); Italian ships.
5. + US3 → benchmarks for any language; German and Italian results recorded.
6. Polish → docs, quickstart record, final gates.

### Commits

- One commit per task or logical group, with the attribution line.
- T076 (catalogue-driven tests) is committed **before** T080. The Italian onboarding is its own commit
  holding only the two generated files and `specs/008-language-onboarding-kit/languages/it/`, so SC-001
  can be checked against it.

---

## Notes

- [P] = different files, no dependency on an incomplete task.
- New file not named in plan.md: `language_kit/language_files.py` (reading a catalogued language's two
  files into `LanguageData`, needed by `check`, `backfill` and `apply`), `bench_environment.py` (shared
  benchmark plumbing), `benchmark-results.json` (the figures `kit bench` reads back instead of parsing
  Markdown) and `validation.md` (the plan's "validation record").
- Spanish's backfill (T077–T078) is a US4 deliverable placed in Phase 5: it runs through
  `finish --pack` so the backfill run gets its run log, test run and report (FR-018, FR-027), and those
  arrive with US1. Phase 4 proves the backfill flow on `tmp_path` copies (T047).
- German's evaluation set moves in Phase 2 rather than with US4 (plan delivery step 3), so that German
  passes `check` in US2 as the plan's US2 step expects.
