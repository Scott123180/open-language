# Implementation Plan: Language Onboarding Kit

**Branch**: `008-language-onboarding-kit` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/008-language-onboarding-kit/spec.md`

---

## Summary

Make adding a practice language a mostly scripted, repeatable job, and prove it by adding
**Italian** with it (FR-024).

006 and 007 left no language-specific code paths. What a new language still needs is *data*, today
written as Python literals in four files and a Bash array in `run.sh`. There are also two benchmarks
hard-coded to German (research § "What adding a language costs today"). The design rests on four
decisions:

1. **Language data becomes generated data files** (R1, R2). Each language is one runtime file,
   `app/language_data/languages/<code>.toml`, holding the catalogue entry and voices. It also has one
   evaluation file under the backend tests: scripted turns, dictation and loanwords.
   `PRACTICE_LANGUAGES` and `AVAILABLE_VOICES` are built from the runtime files, and their public
   shape does not change. `run.sh` reads the voice list from the data, so it is never edited for a
   language again.
2. **One requirement registry drives everything** (R4). `language_kit/registry.py` lists each
   per-language item with its rules. The registry generates:
   - the pack template;
   - validation and the completeness check;
   - backfill;
   - the canonical file layout;
   - a guard test, which fails if the app's language records grow a field the registry does not
     list.
3. **Scripts do the work; the agent writes one file** (R3, R5, R10). `backend/language_kit/` is a
   tested Python CLI behind a short skill, `.claude/skills/language-kit/`. The agent fills one
   self-documenting `pack.toml`. Scripts check prerequisites, list real voices from the upstream
   catalogue, validate, download and verify voices, write files atomically, run the suites, run the
   benchmarks and write the report. Output is one summary line plus only what needs attention.
4. **Benchmarks become language-independent** (R8). They read the language from the environment and
   the evaluation data from its file. German's 006 data moves unchanged, Spanish gains an evaluation
   set through the kit's own backfill step, and Italian gets one from its pack.

What is new: `app/language_data/` (loader and three data files), `backend/language_kit/` (CLI,
registry, rules, pack, voices, apply, verify, bench, report), the `language-kit` skill, three
evaluation files, one dev dependency (`tomli-w`), and Italian. Nothing changes in the database or the
frontend.

---

## Technical Context

**Language/Version**: Python 3.12 (backend `.venv`; `requires-python >= 3.11`, needed for
`tomllib`), Bash (`kit.sh`, `run.sh`). TypeScript 5.4 / React 18.3 frontend, unchanged.

**Primary Dependencies**:
- Standard library: `tomllib` (read), `urllib.request` (voice catalogue and downloads), `hashlib`
  (MD5), `argparse`, `subprocess` (suites, benchmarks).
- Existing: `faster-whisper` (its language list), `wordfreq` (dev; coverage and purity),
  `piper-tts`, the `ollama` client (benchmarks only).
- **New dev dependency**: `tomli-w` (pinned), for writing canonical TOML (research R5). No new
  runtime dependency.
- **New data source**: the Piper voice catalogue (`voices.json` on huggingface.co, the host
  `run.sh` already downloads voices from), used only by the kit at onboarding time, never by the app.

**Storage**: **No database change**. No table, column or row, and the kit never opens the
database. New files:
- `app/language_data/languages/{es,de,it}.toml`, which the app reads;
- `tests/integration/practice_languages/evaluation/{es,de,it}.toml`;
- per-language working files under `specs/008-language-onboarding-kit/languages/<code>/` (pack, run
  log, report, benchmark results, review sheet).

**Testing**:
- pytest unit tests for the loader, registry, rules, pack, renderer, apply, voice catalogue, CLI
  output and report. Network, downloads and subprocesses are faked at their boundaries.
- A pinning test that freezes today's `PRACTICE_LANGUAGES` and `AVAILABLE_VOICES`. It is written
  first and must pass unchanged after the move.
- A seeded-omission test (SC-004) and the guard test (FR-010, SC-005).
- The existing hermetic suite; coverage ≥ 90% over `app` and `language_kit`.
- Benchmarks stay behind the `benchmark` marker, as hand runs.
- Frontend: no code change. `kit verify` runs Vitest and Playwright, and quickstart §6 is the manual
  check with three languages.

**Target Platform**: Linux desktop, local-first. The kit is a developer tool run from the repository
in the backend venv. Network is needed only for voice discovery and download.

**Project Type**: Web application (FastAPI backend + Vite/React frontend) plus developer tooling (a
CLI package and an agent skill).

**Performance Goals**:
- Each kit command except `verify`, `bench` and downloads returns in < 5 s (the voice catalogue is
  cached for 24 h).
- An onboarding run takes < 30 min of working time (SC-002).
- Loading the language files adds < 50 ms to app start (three ~2 KB files).

**Constraints**:
- FR-017 / SC-009: no learner data touched, and no runtime behaviour change for Spanish or German.
  The pinning test proves the data is identical.
- FR-003 / SC-003: the agent can onboard without reading app source.
- Principle VI: a language never gets another language's voice, the kit only offers single-speaker
  voices the app can drive, and the app itself makes no new network call.
- 006: no language-code literal outside the catalogues. The guard test stays, and its allow-list
  shrinks (`services/tts/voices.py` no longer holds data).

**Scale/Scope**:
- 3 languages after this feature, 6 voices, 14 registry requirements, about 18 rule classes and
  11 CLI commands;
- 1 new runtime package (`app/language_data`) and 1 tooling package (`language_kit`);
- 1 skill;
- existing files changed: `practice_languages/catalog.py`, `services/tts/voices.py`, `run.sh`,
  `pyproject.toml`, `test_no_language_literals.py`, `text_purity.py`, the two benchmarks (one
  renamed), `test_german_evaluation_set.py` (rewritten against `de.toml`), `CLAUDE.md`,
  `docs/architecture.md`, `README.md` and `.specify/templates/plan-template.md`.

*No NEEDS CLARIFICATION items remain. The one spec clarification (FR-024: ship Italian) is folded in.
Design questions are settled in [research.md](research.md) R1–R14.*

---

## Spec interpretations

1. **"Every other changed file is written by a kit script" (SC-001)**: this is measured on the
   Italian onboarding commit, not on the feature as a whole. The kit, the data move and the Spanish
   backfill are ordinary development. The Italian commit's repository changes must be exactly the
   two generated files, plus the pack and reports under `specs/`.
2. **"Applies to the setup script's voice downloads" (FR-015)**: this is met by making `run.sh`
   read the voice list from the data files (R6), so applying never edits `run.sh`. The spec asks
   for the outcome (new voices are downloaded on setup), and this gets it without a generated edit.
3. **"Spanish and German MUST pass … with their existing data unchanged" (FR-021)**: "data" means
   the catalogue and voice values the app uses, pinned by test. Spanish gains an evaluation set,
   which is new test data, not changed app data. It is needed because the registry requires one for
   every language (R2).
4. **"Applying MUST be all or nothing" (FR-016)**: this covers the repository change (two files,
   atomic replace with restore). Downloaded voices live outside the repository, are verified and
   idempotent, and are not rolled back (R9).
5. **"Runs the backend and frontend test suites" (FR-018)**: `finish` runs all of them. With
   `--backend-only`, the frontend suites are skipped and the report says so; it is never silent.
6. **"Within 30 minutes" (SC-002)**: this is working time, excluding voice downloads and benchmark
   runs, as the spec says. Downloads are timed in the run log so they can be subtracted.
7. **German benchmark parity (SC-007)**: same evaluation data and same output format, not the same
   figures. The model is not deterministic, and Italian joins the foreign-word list (R8).

---

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design; the result is at the
bottom of this section.*

| Principle | Status | How this design satisfies it |
|---|---|---|
| **I. Clean Code**: ≤ 20-line functions, intention-revealing names, no magic values | ✅ | Thresholds, counts and limits are named constants in the rule constructors: 10 names, 5 turns, 20 dictation sentences, ≥ 95%, ≥ 18/20, cache TTL and exit codes. Each CLI command is a small `Command` object, and each rule is one class with one `check`. No function in the design needs more than 20 lines, and no existing long function is touched (see the function-length plan). |
| **II. SOLID: SRP** | ✅ | The pieces are split by job: <br>• `registry`: what a language needs; <br>• rules: whether a value is acceptable; <br>• `pack`: parsing and merging; <br>• `render`: canonical bytes; <br>• `voices`: the catalogue and downloads; <br>• `apply`: the atomic write; <br>• `verify`: running suites; <br>• `bench`: running benchmarks; <br>• `run_log` and `report`: the record; <br>• `cli`: dispatch only. <br>In the app, the `language_data` loader only parses files; `catalog.py` and `voices.py` only adapt records to their existing types. |
| **II. SOLID: OCP** | ✅ | A new per-language item is a new `Requirement` plus a record field. The template, validator, checker, backfill and renderer pick it up with no edit (R4). A new language is a new data file, and no code changes. A new rule is a new `Rule` class. |
| **II. SOLID: LSP** | ✅ | Every `Rule` honours `check(value, context) -> list[Finding]` and never raises for bad input; bad input is a finding. Fake catalogue, downloader and command runner substitute for the real ones in tests. |
| **II. SOLID: ISP** | ✅ | The boundary interfaces are small: <br>• `VoiceCatalogue`: `candidates(code)` and `voice(key)`; <br>• `VoiceDownloader`: `ensure(voice)`; <br>• `CommandRunner`: `run(argv, log) -> SuiteResult`; <br>• `Clock`. |
| **II. SOLID: DIP** | ✅ | Commands receive their collaborators from one `build_kit()` composition function, and tests pass fakes. Rules read a `RuleContext`, never the app. |
| **III. TDD (non-negotiable)** | ✅ | The pinning test for today's catalogue and voices comes first, before the move. Each rule, the loader's strictness, the renderer's round-trip, apply's rollback and the CLI output are test-first. The Spanish backfill and the Italian onboarding are run *through* the kit, so they exercise it. |
| **≥ 90% coverage, zero skipped tests** | ✅ | `--cov=language_kit` is added to `addopts`. The network, downloads, subprocesses and the clock are faked. Benchmarks are deselected by marker, not skipped. |
| **IV. Simple UI** | ✅ (n/a) | No UI change. Italian appears through the existing catalogue-driven Settings radio group, and quickstart §6 is the manual three-card keyboard and contrast check. |
| **V. Compartmentalization** | ✅ | `app.language_data` is a leaf with no app imports and one public root. `practice_languages` and `services/tts` both depend on it, which removes the reason they would otherwise depend on each other. The kit imports app package roots only, plus the scenario provider through `services/factory.py`. The app never imports the kit. |
| **V. Abstractions before implementations** | ✅ | `Rule`, `VoiceCatalogue`, `VoiceDownloader` and `CommandRunner` are declared and tested with fakes before the HTTP and subprocess implementations. |
| **V. No feature-flag / if-debug guards** | ✅ | Language behaviour is data. The literal guard stays in force. |
| **VI. Provider independence** | ✅ | No provider changes. The app's TTS still never uses another language's voice, and the loader rejects a voice whose locale is not its language's. The voice-catalogue fetch is a developer-time action of the kit, like `run.sh`'s downloads, and sends no learner data. The app gains no network call. |
| **Playwright E2E for frontend changes** | ✅ (n/a) | No frontend change. `kit verify` runs the full Playwright suite anyway (FR-018). |
| **Linting (ruff, black, mypy, ESLint, Prettier)** | ✅ | `language_kit` is under the same `ruff`, `black` and `mypy --strict` settings. `kit verify` runs them. |

**Initial gate: PASS.** There is one Complexity Tracking item: a new dev dependency.

### Function-length plan (Boy Scout, quality gate)

This feature touches no existing function over 20 lines. The functions it modifies:

| Function | Today | Change |
|---|---|---|
| `voices_for` ([voices.py](../../backend/app/services/tts/voices.py)) | 1 | Unchanged. `AVAILABLE_VOICES` becomes a call to the loader adapter |
| `foreign_words`, `_checked_words`, `_is_foreign` ([text_purity.py](../../backend/tests/integration/practice_languages/text_purity.py)) | 7, 3, 3 | Take the target and other languages as parameters |
| `test_german_replies_meet_sc_002` and helpers ([test_german_benchmark.py](../../backend/tests/integration/practice_languages/test_german_benchmark.py)) | ≤ 15 each | Renamed to `test_adherence_benchmark.py`, parameterised by language |
| `Dictation`, transcription test and helpers ([test_transcription_benchmark.py](../../backend/tests/integration/practice_languages/test_transcription_benchmark.py)) | ≤ 15 each | Special letters, voices and output path come from the evaluation set and environment |
| `setup_piper_voices` ([run.sh](../../run.sh)) | 8 | Reads `PIPER_VOICES` from `python -m app.language_data voice-keys` |

### Post-design re-check

The Phase 1 artifacts confirm the initial check:
- [data-model.md](data-model.md): records, the registry and rules.
- [contracts/cli.md](contracts/cli.md): commands, output and exit codes.
- [contracts/pack-format.md](contracts/pack-format.md).
- [contracts/data-files.md](contracts/data-files.md): loaders and invariants.
- [quickstart.md](quickstart.md).

Interfaces exist before implementations. The app gains one leaf package and no new coupling. All
behaviour stays testable without the network. **Post-design gate: PASS.**

---

## Project Structure

### Documentation (this feature)

```text
specs/008-language-onboarding-kit/
├── spec.md
├── plan.md                 # this file
├── research.md             # R1–R14
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md              # kit commands, output, exit codes, skill contract
│   ├── pack-format.md      # the hand-written language pack
│   └── data-files.md       # canonical data files and their loaders
├── checklists/requirements.md
├── languages/              # written by the kit while implementing
│   ├── es/                 # backfill-pack.toml, run-log.jsonl, report.md, benchmark results
│   ├── de/                 # benchmark results from the generalised benchmarks
│   └── it/                 # pack.toml, run-log.jsonl, report.md, benchmark-results.md, review-sheet.md
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
.claude/skills/language-kit/
├── SKILL.md                         # procedure only; ≤ 150 lines (contracts/cli.md § Skill)
└── kit.sh                           # cd backend && .venv/bin/python -m language_kit "$@"

backend/
├── pyproject.toml                   # + tomli-w (dev); packages.find include app*; package-data; --cov=language_kit
├── app/
│   ├── language_data/               # NEW leaf package: no app imports
│   │   ├── __init__.py              # public root: records, load_language_records, voice_keys, LanguageDataError
│   │   ├── __main__.py              # `voice-keys` for run.sh
│   │   ├── records.py               # LanguageRecord, VoiceRecord, PodcastRecord
│   │   ├── loader.py                # strict TOML → records; cross-file invariants
│   │   └── languages/
│   │       ├── es.toml              # moved from catalog.py + tts/voices.py, values unchanged
│   │       ├── de.toml              # likewise
│   │       └── it.toml              # generated by `kit apply it`
│   ├── practice_languages/catalog.py  # PRACTICE_LANGUAGES built from records; DEFAULT + NATIVE stay
│   └── services/tts/voices.py         # AVAILABLE_VOICES built from records; VoiceInfo unchanged
├── language_kit/                    # NEW dev tooling package (not shipped with the app)
│   ├── __main__.py                  # python -m language_kit
│   ├── cli.py                       # argparse → Command objects; output and exit codes
│   ├── composition.py               # build_kit(): wires real or fake collaborators
│   ├── registry.py                  # REQUIREMENTS
│   ├── rules.py                     # Rule ABC + rule classes
│   ├── context.py                   # RuleContext from app facts
│   ├── findings.py                  # Finding, severities, text/json formatting
│   ├── pack.py                      # parse, partial packs, merge onto existing data
│   ├── template.py                  # pack and backfill-pack text with guidance comments
│   ├── render.py                    # canonical runtime and evaluation files (tomli-w)
│   ├── voices.py                    # VoiceCatalogue (Piper, cached), VoiceDownloader (MD5)
│   ├── prerequisites.py             # research R7
│   ├── apply.py                     # atomic two-file write with restore
│   ├── verify.py                    # CommandRunner, suite summaries, logs
│   ├── bench.py                     # benchmark runs with OPEN_LANGUAGE_BENCH_*
│   ├── workspace.py                 # repo root, data dirs, feature dir from .specify/feature.json
│   ├── run_log.py                   # run-log.jsonl
│   └── report.py                    # report.md
└── tests/
    ├── unit/language_data/          # loader strictness, invariants, pinning of today's values
    ├── unit/language_kit/           # rules, registry guard, pack, render round-trip, apply, cli, report, seeded omissions
    ├── unit/test_no_language_literals.py   # allow-list updated
    └── integration/practice_languages/
        ├── evaluation/{es,de,it}.toml      # NEW; de = 006's set unchanged + special_letters
        ├── evaluation_set.py               # NEW loader (replaces german_evaluation_set.py)
        ├── text_purity.py                  # language-parameterised
        ├── test_adherence_benchmark.py     # was test_german_benchmark.py
        ├── test_transcription_benchmark.py # every voice of the language
        └── test_evaluation_sets.py         # was test_german_evaluation_set.py; every language

run.sh                               # PIPER_VOICES from `python -m app.language_data voice-keys`
CLAUDE.md, docs/architecture.md, README.md, .specify/templates/plan-template.md   # FR-026
```

**Structure Decision**: this is the existing web-application layout. Runtime language data joins the
backend app as a leaf package. The kit is a sibling package of `app` in `backend/`, so it shares the
venv, test runner, coverage and linters, but is not packaged or imported by the app. The skill lives
with the other project skills in `.claude/skills/`.

### Delivery order (for /speckit-tasks)

1. **Foundation**: write the pinning test, then move Spanish and German into
   `app/language_data/` and switch `catalog.py` and `voices.py` to the loader. Switch `run.sh` to
   `voice-keys`. The suite passes unchanged.
2. **US2 (check)**: the registry, rules, `RuleContext`, `check`, the guard test and the
   seeded-omission test. German passes, and Spanish fails only on `evaluation.*`, which is expected.
3. **US4 core**: the pack, template, render, apply and backfill. Backfill Spanish's evaluation set
   through the kit, and move German's set into `de.toml`. `check --all` passes (FR-021).
4. **US1**: prereq, voice catalogue and downloader, scaffold, verify, finish, run log, report and
   the skill. Then **onboard Italian through the skill** (FR-024, SC-001–SC-003).
5. **US3**: generalised benchmarks and `bench`. Run them for German and Italian, and record the
   results.
6. **Polish**: FR-026 docs, `architecture.md` and README, quickstart §4, §8, §9 and §10, and the
   validation record.

---

## Complexity Tracking

| Violation / addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| New dev dependency `tomli-w` | The kit must write canonical TOML that round-trips byte-for-byte, which is what idempotency (FR-006) rests on. The standard library reads TOML but cannot write it. | A hand-written writer means ~60 lines of escaping rules (Unicode, quotes, multiline, arrays of tables) to test and maintain. JSON data files cannot carry the pack's guidance comments, and two formats (TOML packs, JSON data) double the mental load (R1, R5). |
| A second top-level backend package (`language_kit`) next to `app` | The kit needs the backend venv, scenario list, catalogue, Whisper and `wordfreq`, and it must sit under the project's TDD, coverage and lint gates. | Scripts in `.claude/skills/` would be untested and unlinted. Putting the kit inside `app/` would ship developer tooling in the runtime package (R3). The packaging cost is one `packages.find` line. |
| `faster_whisper.tokenizer._LANGUAGE_CODES` (a private name) | It is the only way to know Whisper's languages without loading a model (seconds, GBs). | `WhisperModel(...).supported_languages` loads a model to read a constant. A pinning test fails loudly if an upgrade moves the name (R7). |
