# Research: Language Onboarding Kit

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-06

Each decision below settles one design question from the plan's Technical Context. The facts they
rest on were checked in this repository and against the upstream voice catalogue on 2026-10-06.

## What adding a language costs today

Adding German (006) changed 108 files, but almost all of that was one-time plumbing: conversations
carry a language, aids take it from the conversation, flashcards and voices are scoped, and a guard
test (`tests/unit/test_no_language_literals.py`) forbids hard-coded codes. A search of `app/` and
`frontend/src/` on 2026-10-06 found **no language-specific code paths left**. Prompts name languages
through the catalogue, the frontend reads `/api/settings/practice-languages`, and podcasts cast hosts
from catalogue data and voices.

What a new language still needs, and where it lives today:

| Item | Where today | Form |
|---|---|---|
| Code, English name, default voice | `app/practice_languages/catalog.py` | Python literal |
| Host names by voice gender, guest labels, voice-sample line (007) | same | Python literal |
| Voices: key, display name, gender, locale, quality, speaking rate | `app/services/tts/voices.py` | Python literal |
| Voice downloads | `run.sh` `PIPER_VOICES` | Bash array, "keys must match" comment |
| Scripted learner turns (10 scenarios × 5), dictation sentences, loanword allowlist | `tests/integration/practice_languages/german_evaluation_set.py` | Python literal, German only |
| Adherence benchmark | `test_german_benchmark.py` | German hard-coded (code, sheet path, header text) |
| Transcription benchmark | `test_transcription_benchmark.py` | German voice, hint and `[äöüß]` hard-coded |
| Foreign-word check | `text_purity.py` | `GERMAN = "de"`, `("en", "es")` hard-coded |

So adding a language means writing Python literals in four files and Bash in one, plus copying
two German-only benchmarks. Spanish has **no evaluation set at all**: it predates the benchmarks.

---

## R1. Language data moves from Python literals to one data file per language

**Decision**: each practice language's runtime data (catalogue entry and voices) lives in one
generated data file, `backend/app/language_data/languages/<code>.toml`. A new package,
`app/language_data/`, reads those files into plain typed records. `practice_languages/catalog.py`
builds `PRACTICE_LANGUAGES`, and `services/tts/voices.py` builds `AVAILABLE_VOICES`, from those
records. Their public names and types (`PracticeLanguage`, `PRACTICE_LANGUAGES`, `VoiceInfo`,
`AVAILABLE_VOICES`, `voices_for`) are unchanged, so no consumer and no existing test changes.

**Rationale**:
- Scripts can write data safely. Having a script edit Python source (insert a dataclass literal in
  the right place, keep `black` happy, never duplicate) is fragile, and it is exactly the kind of
  step that costs an agent tokens when it goes wrong.
- One file per language makes "applying" a language mostly a file write, makes "is anything
  missing?" a comparison of a file against the registry, and keeps a diff to one language per file.
- `app/language_data/` depends on nothing in the app. Today `practice_languages/voices.py` imports
  `services/tts/voices.py`. If the TTS module read data from `practice_languages`, the two would
  depend on each other. A neutral data package that both read keeps the arrows one-way.
- TOML is read by the standard library (`tomllib`, Python ≥ 3.11). It holds Unicode names and lists
  readably, and agents write it reliably.

**Alternatives considered**:
- *Generate Python source* (`catalog.py` from a template): it keeps the literals, but then every
  catalogue edit by hand is overwritten. Rejected.
- *JSON*: it allows no comments, so the pack could not carry its own guidance (R5). The canonical
  data files need no comments, but one format for packs and data is simpler. Rejected.
- *One data file shared by all languages*: every onboarding would rewrite a shared file, and
  backfill diffs would mix languages. Rejected.
- *Keep the voices in `services/tts/`* (a TOML file per voice): a language would then live in two
  places again. Rejected.

**Display order** comes from an `order` integer in each file, which the kit derives as
max + 1 (Spanish 1, German 2, Italian 3). `DEFAULT_PRACTICE_LANGUAGE` and `NATIVE_LANGUAGE_NAMES`
stay in `catalog.py`. They are app policy, not language data.

**Loading is strict**: an unknown key, a missing key or a wrong type raises `LanguageDataError` at
import time, naming the file and key. A malformed file cannot reach a running app, and data that the
records do not model cannot hide in a file (it also backs the guard in R4).

**Packaging**: `pyproject.toml` gains `[tool.setuptools.packages.find] include = ["app*"]` and
`package-data` for `app.language_data/languages/*.toml`. The `include` is needed anyway: a second
top-level package (`language_kit`, R3) would otherwise break setuptools' flat-layout
auto-discovery ("multiple top-level packages") on the next `pip install -e`.

## R2. Evaluation data moves to one data file per language under the tests

**Decision**: each language's evaluation set lives in
`backend/tests/integration/practice_languages/evaluation/<code>.toml`, loaded by `evaluation_set.py`.
The set holds the scripted learner turns per scenario, the dictation sentences, the loanword
allowlist and the language's special letters. `german_evaluation_set.py` is replaced, and its
content moves unchanged into `de.toml`, with `special_letters = "äöüß"` added. That string was the
`[äöüß]` regex in the transcription benchmark.

**Rationale**: evaluation data is test data. Shipping it inside `app/` would put benchmark sentences
into the runtime package. Keeping it beside the benchmarks keeps the split clean. The kit still
writes both files from one pack (R5).

**Spanish needs an evaluation set**. The registry (R4) requires one for every language, and FR-021
requires Spanish to pass the completeness check. Writing it is done **through the kit's backfill
step**: the first real use of User Story 4, before any new requirement exists.

**Alternatives considered**: an `[evaluation]` table inside the runtime data file, ignored by the
app. It is simpler (one file per language), but it ships test data in the app package. Rejected.

## R3. The kit is a Python package in the backend, with a thin skill on top

**Decision**:
- The scripts are one Python package, `backend/language_kit/`, run as
  `backend/.venv/bin/python -m language_kit <command>` from `backend/`.
- The skill is `.claude/skills/language-kit/`: a `SKILL.md` with the procedure, and `kit.sh`, a
  ten-line wrapper that changes to `backend/` and calls the venv's Python with its arguments.

**Rationale**:
- The kit needs the backend's own facts: the scenario list, the catalogue, the Whisper language
  list, `wordfreq` and the venv. Running in the venv gives it all of them without duplicating any.
- A backend package is covered by the existing gates: pytest with coverage, `ruff`, `black` and
  `mypy`. TDD and the 90% floor apply to the kit like any other code. `addopts` gains
  `--cov=language_kit`.
- `.claude/skills/` is tracked in git (the speckit skills are), so the skill ships with the repo.
- It sits outside `app/` because it is development tooling. The app never imports it, and it is not
  packaged (R1's `include = ["app*"]`). Tests import it because pytest puts `backend/` on `sys.path`
  (`tests/` is a package).

**Alternatives considered**:
- *Bash scripts*: validation of nested Unicode data, HTTP, MD5 and TOML in Bash is fragile and hard
  to test. Rejected.
- *Scripts inside the skill directory*: they would be outside pytest's coverage and outside the
  linters. Rejected.
- *A `make`-style task file*: it adds a tool without adding anything. Rejected.

**Import boundary**: the kit imports app package roots only (`app.language_data`,
`app.practice_languages`), plus the scenario list through `app.services.factory`'s provider seam,
like any consumer (Principle V).

## R4. One requirement registry drives the pack, validation, check, backfill and guard

**Decision**: `language_kit/registry.py` holds `REQUIREMENTS`, a tuple of `Requirement` value
objects. Each one carries:
- `path`: the item's place in the pack, such as `podcast.sample_line`;
- `destination`: the runtime or the evaluation file;
- `producer`: written by the agent, chosen from listed options, or derived by a script;
- `needed_by`: the feature that needs it, such as `007`;
- a description, an example source language, and its `rules`.

Rules are small strategy objects behind one `Rule` interface (`check(value, context) -> list[Finding]`),
such as `MinCount`, `UniqueCasefold`, `ExactlyOnePlaceholder` or `CoversEveryScenario`. A rule is
an *error* or a *warning*. Only errors block applying.

Everything else is generated from the registry:
- **Pack template**: each item, with its description, rules and an example taken from an existing
  language's data.
- **Validation and the completeness check**: every rule of every item.
- **Backfill**: the items whose rules fail.
- **The canonical data files**: values are written at their `path`, in their `destination`, so a
  new item needs no renderer change (OCP).
- **`kit requirements`**: the registry as a table, for feature authors.

**The guard (FR-010)**: `tests/unit/language_kit/test_registry_covers_language_data.py` compares,
in both directions, the fields of the language-data records (`LanguageRecord`, `VoiceRecord`,
`PodcastRecord`, `EvaluationSet`) with the registry's paths. A field with no requirement fails with:
"`<record>.<field>` is per-language data with no entry in `language_kit/registry.py`. Add a
Requirement for it (see the language-kit skill, 'Adding a per-language requirement')". The reverse
check catches a requirement for data that no longer exists. With R1's strict loader, data cannot
reach the app without a record field, so the guard covers everything a language can supply.

**Rule context**: some rules apply only when onboarding (the language must not already be
catalogued), and some depend on the app (every scenario has turns). A `RuleContext` carries the
scenario ids, catalogued codes, explanation-language codes and the voice catalogue (when it has been
fetched). Rules read it and never import the app themselves.

**Scenario coverage is dynamic**: `CoversEveryScenario` reads the current scenario ids. If a later
feature adds a scenario, every language fails the check on `evaluation.turns`, and backfill asks for
turns for just that scenario. That is FR-007's "keep the kit current" without anyone editing it.

**Alternatives considered**:
- *A JSON Schema file*: it cannot express "covers every scenario" or "exactly one `{name}`"
  without custom keywords, and it is a second language for feature authors. Rejected.
- *Validation code per field, without a registry*: nothing could then generate the pack, backfill
  or the guard. Rejected.

## R5. The pack is one hand-written TOML file with its guidance inside

**Decision**: `kit scaffold <code>` writes `specs/<feature>/languages/<code>/pack.toml`. For every
registry item it holds:
- a comment block: the description, who produces it, the rules, and an example from an existing
  language (German by default, or any language that passes the item);
- the key with a `TODO` placeholder, or with its value already filled when the item is derived.

The candidate voices from the prerequisite step are listed in a comment, with key, region, quality
and download size. The agent copies the keys it wants and sets each one's gender.

`kit apply` reads the pack with `tomllib`, derives the rest and writes the two canonical data files
with `tomli-w`. A voice's display name ("Paola (Italy)"), locale and quality come from the voice
catalogue, and `order` is the next free number. The pack stays in the feature folder as the record
of what was written by hand.

**Rationale**: the agent reads one file and edits one file (SC-001, SC-003). The guidance sits next
to each item, so the skill's instructions stay short and never go stale (FR-009).

**Canonical files are generated**: they start with a "generated by the language kit; change through
a pack" header and have fixed key order and formatting. Rendering the same data twice gives the same
bytes, which is how every step proves idempotency (FR-006).

**New dev dependency**: `tomli-w` (pinned), for writing TOML correctly (escaping, Unicode, arrays of
tables). The standard library reads TOML but cannot write it. Hand-rolling a writer is ~60 lines of
escaping edge cases. It is dev-only: the app only reads.

## R6. Voices come from the upstream voice catalogue, never from memory

**Decision**: the prerequisite step fetches the Piper voice catalogue
(`https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json`, the same host `run.sh`
already downloads from) and caches it in `~/.cache/open-language/piper-voices.json` for 24 hours.
It lists the voices whose `language.family` is the code and whose `num_speakers` is 1.

**Facts checked on 2026-10-06** (177 voices in the catalogue):
- Each entry has `key`, `name`, `language.{code, family, region, name_english, country_english}`,
  `quality`, `num_speakers`, and `files` with each file's `size_bytes` and `md5_digest`.
- **Gender is not in the catalogue.** It is an agent-written item, and the report always lists "voice
  genders asserted, not checked by listening" under *not checked*.
- Italian has four single-speaker voices: `it_IT-paola-medium`, `it_IT-riccardo-x_low`,
  `it_IT-serena-medium` and `it_IT-serena-high`.
- `PiperTTSProvider` has no speaker selection, so multi-speaker voices (`de_DE-mls-medium`,
  236 speakers) cannot be used and are not offered.

**Download**: `kit apply` downloads each chosen voice's `.onnx` and `.onnx.json` into the voice
directory (`OPEN_LANGUAGE_VOICE_DIR`, else `~/.local/share/piper-voices`, as in `run.sh` and
`config.py`) and checks each file against `md5_digest`. A file already present with the right digest
is skipped. A mismatch deletes the partial file and fails the step.

**`run.sh` reads the data instead of keeping a list**: `PIPER_VOICES` becomes the output of
`"$VENV/bin/python" -m app.language_data voice-keys`, which runs after `setup_backend`. That order is
already the case. The "keys must match run.sh" duplication disappears, and applying a language never
edits `run.sh`, which still downloads every catalogued voice on `--setup` (FR-015). The command lives
in `app.language_data` (runtime), not the kit (dev tooling), so `run.sh` needs no dev extras.

## R7. Prerequisite checks use the libraries' own lists

| Check | Source | Failure |
|---|---|---|
| Code is two lowercase letters (ISO 639-1) | regex | stop |
| Not already catalogued | `app.language_data` | stop: "use `kit check` / `kit backfill`" |
| Not the explanation language | `NATIVE_LANGUAGE_NAMES` | stop |
| Left-to-right, spaced words | kit constant: RTL `ar he fa ur yi ps sd ug dv`, unspaced `zh ja th lo km my bo` | stop, with the reason |
| Speech recogniser supports it | `faster_whisper.tokenizer._LANGUAGE_CODES` (100 codes; `it` present) | stop |
| At least one single-speaker local voice | voice catalogue (R6) | stop |
| Adherence word list covers it | `wordfreq.available_languages()` (`it` present) | **warn**: the adherence benchmark will be "not run" |

`_LANGUAGE_CODES` is private to `faster-whisper`. It has been stable since 0.x. A unit test pins that
the import works and contains `es`, `de` and `it`, so an upgrade that moves it fails loudly instead of
silently passing every language. The alternative, `WhisperModel(...).supported_languages`, loads a
model (seconds, and GB of memory) just to read a list.

## R8. Benchmarks become language-independent, selected by environment variables

**Decision**:
- `test_german_benchmark.py` becomes `test_adherence_benchmark.py`, and
  `test_transcription_benchmark.py` is generalised in place.
- Both read the language from `OPEN_LANGUAGE_BENCH_LANGUAGE` (default: every catalogued language
  that has an evaluation set) and the output folder from `OPEN_LANGUAGE_BENCH_OUT`. Both keep the
  `benchmark` marker, so CI stays hermetic.
- `kit bench <code>` sets the two variables and runs pytest.
- The tests write `benchmark-results.md` and `review-sheet.md` themselves before asserting, as 006's
  did, so a missed threshold still leaves the full evidence (FR-022, US3 scenario 3).

**Generalised details**:
- *Foreign-word check* (`text_purity.py`): the target is the benchmarked language. The "other"
  languages are English plus every other catalogued practice language that `wordfreq` covers.
  006's German run used English and Spanish; with Italian catalogued, German is also checked for
  Italian words. The thresholds (Zipf ≥ 3.0, margin ≥ 1.5) and the rule that skips capitalised
  tokens after the first are unchanged. The capitalisation rule exists for German nouns, and in other
  languages it skips proper nouns, which is still right.
- *Transcription*: each dictation sentence is synthesised by **every** voice of the language, not
  just one. 006 specified one German voice (Kerstin), so each voice gets its own table. "Keeps the
  special letters" reads `special_letters` from the evaluation set instead of `[äöüß]`.
- *Thresholds*: 006's are unchanged. The adherence benchmark needs at least 95% clean replies. The
  transcription benchmark needs at least 18 of 20 sentences passing, where a sentence passes with a
  word error rate ≤ 20% and its special-letter words kept.
- *Review-sheet header*: it names the language and the other languages from the catalogue, not
  "German" and "English or Spanish".

**SC-007** asks that the German run use 006's data unchanged and write 006's format. It does not ask
for identical figures: the model is not deterministic, and Italian now joins the foreign-word list.

**Alternatives considered**: pytest command-line options (`--language`). `pytest_addoption` only
works in the root conftest, and these tests are run by path. Environment variables need no plumbing.
Rejected.

## R9. Applying is all or nothing; voices download first

**Decision**: `kit apply` runs, in order:
1. Validate the merged pack. Any error stops the step with no change.
2. Download and verify the voices into the voice directory. This is outside the repository,
   idempotent and harmless if later steps fail.
3. Render both data files to temporary files beside their targets, then `os.replace` each one. If
   the second replace fails, the first target is restored from its backup. Two files are the whole
   repository change.

Verification (tests and linters) is a separate step (`kit verify`), and `kit finish` chains apply →
verify → check → report. A failing test after applying is reported, not rolled back. It means the
app or the kit has a defect, and the files show exactly what was applied.

`--dry-run` on apply prints the files it would write, as a unified diff summary (lines added and
removed per file), and the voices it would download with their sizes. It touches nothing.

**Learner data**: nothing in the kit opens the database. A new language adds no table, no column and
no row. `voice_choices` and `app_settings` are untouched, so the learner's practice language stays
selected (FR-017, SC-009). Existing upgrade tests (`test_upgrade_preserves_data.py`) still pass.

## R10. Output is built for an agent's context window

**Decision**:
- Each command prints one summary line (`check: 3 languages, 37 items, 1 failing`), then only the
  lines that need attention, one per finding: `FAIL it podcast.host_names.male: at least 10 names
  (found 6). Add 4 more male names.` Passing items are counted, not listed.
- `--json` prints the same as one JSON document for scripts.
- Exit codes: `0` ok, `1` findings, `2` usage or unmet prerequisite, `3` external failure (network,
  download or a test suite).
- `kit verify` captures each suite's output to `languages/<code>/logs/` and prints only pass/fail
  and counts per suite, plus, for failures, the test ids (at most 20) and the log path.

**Rationale**: the spec's cost goal (FR-004, SC-003) is about tokens read. A passing pytest run is
~2,000 lines; the summary is one.

## R11. Run log and report

**Decision**: every command that acts on a language appends one JSON line to
`specs/<feature>/languages/<code>/run-log.jsonl`. Each line has the command, a timestamp, the
outcome, findings counts, files written, voices downloaded, suite results and benchmark figures.
`kit report <code>` renders `report.md` from the log, so the report is written by a script
(FR-027). It has these sections:
- **Applied**: data files and voices.
- **Checks**: suites and the completeness check.
- **Benchmarks**: figures against thresholds, or "not run" with the reason.
- **Open items**: misses, warnings, and review-sheet rows still to judge.
- **Not checked**: a fixed list: listening to the voices, voice genders by ear, a screen-reader
  pass, offline use, and a human speaking into the microphone.

The feature folder comes from `.specify/feature.json` (`feature_directory`), else `--out`. This is
how speckit's own scripts find it.

## R12. The skill stays short and static

**Decision**: `.claude/skills/language-kit/SKILL.md` (target ≤ 150 lines) has five parts:
- when to use the kit;
- the onboarding procedure, as numbered commands with what to do between them;
- the backfill procedure;
- "Adding a per-language requirement", for feature authors;
- the rules: never read app source during onboarding, never edit generated data files by hand,
  never pick a voice gender without checking the voice's name or model card.

It holds no list of requirements, which come from the pack and `kit requirements`, so adding a
requirement never means editing the skill (FR-009, US4 scenario 5).

**Adding a per-language requirement**, the procedure for a future feature's author, in the same
change:
1. Add the field to the record and loader in `app/language_data/`, test first. The strict loader
   now fails on every data file that lacks it.
2. Add a `Requirement` to the registry. The guard test passes again.
3. Run `kit backfill --all`, fill each language's partial pack, then `kit apply` each.
4. Run `kit check --all`. It passes.

Steps 1 and 2 are enforced by the guard and the loader.

**FR-026**: `CLAUDE.md` (a short "Per-language data" note) and the plan template's Constitution
Check section both gain one line: "Does this feature add per-language data? Then it registers a
requirement in the language kit (`.claude/skills/language-kit`)". The check runs through every
future `/speckit-plan`.

## R13. Italian content choices (FR-024)

- **Voices**: `it_IT-paola-medium` (female, the default, the same medium tier as `davefx` and
  `thorsten`) and `it_IT-riccardo-x_low` (male, the only male Italian voice). Two genders give
  Panel episodes two distinct hosts. `serena-medium` is a third, female option. The agent decides at
  onboarding, and the prerequisite output shows all four. `riccardo` is x_low quality, so the
  transcription benchmark may miss with it, as it did with Kerstin. That is recorded, not blocking.
- **Special letters**: `àèéìòù`. Dictation sentences each carry at least one, as in "Perché",
  "città", "più", "caffè".
- **Expected weak spots**: `llama3.1:8b`'s Italian is generally stronger than its German, but the
  Beginner length gap (005 SC-001) and correction restraint (003) apply to every language and stay
  open items.

## R14. What the kit does not do

- **Remove a language**: out of scope (spec).
- **Translate interface text**: scenarios, show premises and personalities are English interface
  text by design (006, 007).
- **Edit the frontend**: nothing to edit (R1, catalogue-driven). `kit verify` still runs Vitest and
  Playwright. `PracticeLanguageFieldset` renders one radio card per catalogued language. A third card
  (Italian) is checked by eye and keyboard in the quickstart walkthrough (§6), since no automated
  test covers three real languages.
- **Choose for the maintainer whether a missed benchmark ships**: the report lists it, and the
  maintainer decides (spec Assumptions).
