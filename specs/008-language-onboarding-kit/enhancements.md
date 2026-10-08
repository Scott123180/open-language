# Potential enhancements after 008: Language Onboarding Kit

What 008 missed, left unchecked or found awkward, kept as candidates for later work. Each item says
what was seen, where the evidence is, and what could be done. None of these blocked 008. The figures
and runs behind them are in [validation.md](validation.md).

Priority is a suggestion: **High** affects learners now, **Medium** affects the next language or
feature author, **Low** is polish.

---

## Learner-facing quality

### 1. Italian transcription misses badly on Whisper `base` (High)

- **Seen**: 6/20 sentences pass with Paola and 5/20 with Riccardo (`x_low`), against ≥ 18/20.
  The errors are genuine mishearings of Piper speech, for example "al mare" → "ad ammare",
  "carta" → "catta" and "Lunedì" → "L'une di".
- **Evidence**: `languages/it/benchmark-results.md`, `languages/it/report.md`.
- **Could do**:
  - Re-run `kit.sh bench it --transcription` on Whisper `small` and `medium`, as 006 did for
    German, and record which size Italian needs.
  - Recommend a Whisper size per language in Settings. This would be a new per-language requirement
    (for example `recommended_whisper_model`), added through the kit's own "Adding a per-language
    requirement" procedure.
  - Consider replacing `it_IT-riccardo-x_low` as the male voice when a better single-speaker male
    Italian voice appears in the Piper catalogue (`kit.sh prereq it` lists what exists).

### 2. German transcription still misses on `base` (High, known since 006)

- **Seen**: 17/20 with Thorsten and 12/20 with Kerstin (low quality), against ≥ 18/20. This
  matches the 006 open item.
- **Evidence**: `languages/de/benchmark-results.md`, and docs/architecture.md § "Open items".
- **Could do**: the same per-language Whisper recommendation as item 1. Kerstin's low quality is
  part of the gap, so a better female German voice would help both the learner and the benchmark.

### 3. Italian partner adherence is just under target (Medium)

- **Seen**: 46/50 replies with no flagged word, against ≥ 95% (47.5/50).
- **Evidence**: `languages/it/review-sheet.md` has 4 rows with no verdict yet. At least one flag is
  false: "out" comes from "check-out", which Italian uses. One looks real: "bagaglio hand".
- **Could do**:
  - Judge the review sheet; the true figure may meet the target.
  - Treat hyphenated compounds ("check-out") as one token in `text_purity.py`, or add them to
    Italian's loanwords through a backfill pack.
  - If English words really do leak in, look at the roleplay prompt for Italian, or wait for a
    larger model (the same limit as 003 and 005).

### 4. Learner-facing checks done through the API, not in the browser (Medium)

- **Seen**: Italian was checked end to end through the real API: conversation, podcast hosts,
  voices, transcription. The browser walk-through of quickstart §6 was not done: three
  practice-language cards with arrow keys, learning tools, Beginner level, Strict corrections,
  flashcards, Panel playback, Summary, Past Chats. Neither was the keyboard and contrast check of
  the three cards (Constitution IV).
- **Could do**:
  - Walk §6 once by hand with Italian selected.
  - Add a Playwright spec whose mocked `/api/settings/practice-languages` returns three languages,
    so arrow-key movement across three cards is covered automatically from now on.

---

## Benchmarks

### 5. Number words count as transcription errors (Medium)

- **Seen**: Whisper writes "cento", "dieci" and "novantatré" as "100", "10" and "93". The sentence
  then fails on word error rate, although the meaning was heard correctly.
- **Could do**: either normalise numbers before comparing (digits ↔ words, per language), or keep
  number words out of dictation sets. The second option could be a new dictation rule in the kit,
  so the pack guidance says it.

### 6. Spanish and the 007 benchmarks have not been run for every language (Medium)

- **Seen**: Spanish gained its first evaluation set in 008, but `kit.sh bench es` was never run.
  The 007 benchmarks (host language, summary) are now parametrised over every practice language,
  but have not been run for German or Italian, nor for Spanish since 007.
- **Could do**: `kit.sh bench es`, then the 007 benchmarks by hand
  (`pytest -m benchmark tests/integration/podcasts tests/integration/conversation_summary`), and
  record the figures.

### 7. Benchmarks hear Piper, not people (Low)

- **Seen**: dictation audio is synthesised by the language's own voices, so the transcription
  figures measure Whisper on Piper speech. A real learner's accent is not measured.
  `report.md` lists "a human speaking into the microphone" under *Not checked*.
- **Could do**: an optional set of recorded learner sentences per language, run by the same
  benchmark when present.

### 8. "Ollama stopped" path not run by hand (Low)

- **Seen**: `kit.sh bench it --adherence` with Ollama stopped was not run, because Ollama served
  other work on the machine. A unit test covers the path (exit 3, names Ollama, writes nothing).
- **Could do**: run it once by hand the next time Ollama can be stopped.

---

## The kit, for the next language and the next feature author

### 9. Adding a requirement still means editing two test tables (Medium)

- **Seen**: a feature author must add the new path to `test_registry.py` and an invalid value to
  `BROKEN_VALUES` in `test_seeded_omissions.py`. Both tests fail with a clear message, and the skill
  names them, but they are hand edits.
- **Could do**: let each rule supply a "broken example" value, so the seeded-omission test needs no
  table. Keep `test_registry.py` as the deliberate, reviewed list.

### 10. Other fixtures with fixed fields (Medium)

- **Seen**: the Italian test pack now comes from the committed data (fixed in 008).
  `write_valid_evaluation()` and the backfill body in `test_finish_command.py` still build
  evaluation data by hand, so a new `evaluation.*` requirement would break them the same way.
- **Could do**: build them from a passing language's data, as the Italian pack is.

### 11. The full new-requirement exercise was not repeated after the last fix (Low)

- **Seen**: quickstart §8 ran twice. The second run's only failure was a template test with a
  hard-coded list. That test now checks the ordering rule, and passes with an extra requirement
  registered, but the three-language run was not repeated after the change.
- **Could do**: repeat §8 on a scratch branch before the next feature that adds a requirement, or
  as part of that feature.

### 12. Pack guidance is long in places (Low)

- **Seen**: the onboarding agent found that examples cut with "…" hid the shape of a value, and
  some "Rules:" lines run past 120 characters (the `code` item has six rules). Guest-label
  conventions needed a judgement call; the description has since been clarified.
- **Could do**: wrap rule lines; add a `kit.sh requirements --example <path>` that prints a
  passing language's full value for one item.

### 13. Run reports point at log files that are not committed (Low)

- **Seen**: `report.md` and `run-log.jsonl` name the logs under `languages/<code>/logs/`, but
  `*.log` is git-ignored, so in a fresh clone those paths do not exist.
- **Could do**: either commit the suite logs for onboarding runs (they are large), or have the
  report say the logs are local to the machine that ran the kit.

### 14. Voice genders are asserted, not checked (Low)

- **Seen**: the Piper catalogue has no gender field, so the pack states each voice's gender from
  its name or model card. Every report lists this under *Not checked*.
- **Could do**: read the voice's `MODEL_CARD` during `prereq` and show any gender it states next to
  the candidate.

### 15. The kit relies on a private faster-whisper name (Low)

- **Seen**: `faster_whisper.tokenizer._LANGUAGE_CODES` tells the kit which languages Whisper
  supports. A pinning test fails loudly if an upgrade moves it.
- **Could do**: switch to a public API if faster-whisper adds one.

### 16. Removing a language is out of scope (Low)

- **Seen**: the kit adds and backfills languages, but cannot remove one (spec, research R14).
- **Could do**: a `kit.sh retire <code>` that removes the two data files and reports learner data
  still in that language (conversations, saved words, decks), which would stay in the database.

---

## Repository health found along the way

### 17. Lint backlogs outside the 008 gates (Medium)

- **Seen**: `mypy app` reports 232 errors in 53 files and `prettier --check src` flags 132 files
  (checked 2026-10-06). None are in files 008 touched. `kit verify` therefore type-checks only
  `language_kit` and `app/language_data`, and uses ESLint as the frontend gate.
- **Could do**: clear them as their own piece of work, then widen `kit verify` to `mypy app` and
  Prettier.

### 18. The integration suite opens the learner's real database (Medium, known since 006)

- **Seen**: the app lifespan's `init_db()` runs against `~/.open-language/app.db` during
  integration tests. In 008 the file was not written (its modified time predates the feature), but
  a test run should never touch learner data.
- **Could do**: point the integration suite at a temporary database path for the whole session.

---

## Found by later features

### 19. The skill's order for a new runtime requirement stops the kit (Medium, found in 009)

- **Seen**: "Adding a per-language requirement" step 1 adds the field to the strict loader first.
  For a runtime field this stops the kit itself: `kit.sh` imports `app.practice_languages` (cli →
  composition → context), and that import loads every data file with the strict loader, so a
  required field that no file has yet raises before `backfill` can write it. Evaluation fields are
  not affected. 009's `flag` works around it (tasks T049–T053): the loader accepts the field as
  optional, the packs are applied, then the loader requires it.
- **Could do**: write that order into the skill for runtime fields, or have `context.py` read the
  catalogue codes it needs without importing the app catalogue.
