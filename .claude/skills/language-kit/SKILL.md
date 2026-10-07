---
name: language-kit
description: "Add a language to Open-Language, or keep every language's data complete. Use when asked to add a language, support Italian (or any language), set up a new practice language, change per-language data, or backfill languages after a feature adds a per-language requirement."
user-invocable: true
disable-model-invocation: false
---

# Language kit

Scripts do the work; you write one file. Every command prints one summary line, then only what
needs attention, then `→ next:` with the command to run next. Run them from the repository root:

```bash
.claude/skills/language-kit/kit.sh <command> [args]     # kit.sh --help lists the commands
```

Exit codes: `0` done or nothing to do, `1` findings to fix, `2` usage or unmet prerequisite
(nothing changed), `3` something outside the kit failed (network, download, a test suite).
Every command takes `--json`; every command that writes takes `--dry-run`.

## When to use

- A practice language is to be added (Italian, French, …).
- `kit.sh check --all` fails, or a feature author has just added a per-language requirement.
- You are writing a feature that needs new data from every language (see *Adding a per-language
  requirement*).

Do not use it to remove a language or to translate interface text; neither is in its scope.

## Onboard a language

1. `kit.sh prereq <code>`: checks the code can be onboarded (ISO 639-1, not already a practice
   language, left to right with spaces, Whisper supports it, a single-speaker Piper voice exists).
   If it fails, stop and report the reason to the maintainer. On success it lists the candidate
   voices with country, quality and download size.
2. Choose voices from that list: prefer one female and one male voice, at medium quality or better
   where there is a choice, so podcast panels get two distinct hosts.
3. `kit.sh scaffold <code> --name <English name>`: writes
   `specs/<feature>/languages/<code>/pack.toml`. It is never overwritten.
4. Fill the pack. Read the guidance comment above each key: it says who supplies the value, the
   rules it must meet, and an example from an existing language. Replace every `TODO` and fill
   every empty list. Add one `[[voices]]` table per chosen voice (key and gender).
5. `kit.sh validate <code>`: repeat, fixing each `FAIL` line, until it reports `0 errors`.
   `WARN` lines do not block; mention them to the maintainer.
6. `kit.sh finish <code>`: applies the pack (downloads and checks the voices, writes the two data
   files), runs every test suite and linter, checks completeness and writes `report.md`. Add
   `--backend-only` only if the maintainer asks; the report then says the frontend was skipped.
   If a suite fails, read only the failing test ids and the log it names.
7. `kit.sh bench <code>`: runs the adherence and transcription benchmarks (needs Ollama and the
   voices; slow). A missed threshold is recorded, not fatal: the maintainer decides.
8. `kit.sh report <code>`: regenerates the report with the benchmark figures. Tell the maintainer
   where it is, and list its *Open items* and *Not checked* sections.

## Backfill after a new requirement

1. `kit.sh check --all`: lists, per language, every item that fails.
2. `kit.sh backfill --all` (or `backfill <code>`): writes
   `specs/<feature>/languages/<code>/backfill-pack.toml` holding only the failing items, with
   guidance and an example from a language that passes. A pack still being filled is kept; one
   already applied is replaced.
3. Fill each backfill pack as in *Onboard a language*, step 4.
4. `kit.sh validate <code> --pack <path>` until it reports `0 errors`, for each pack.
5. With several packs, `kit.sh apply <code> --pack <path>` for each first: the test suite checks
   that every language is complete, so it fails until the last pack is in.
6. `kit.sh finish <code> --pack <path>` for each pack, so every backfill is tested and reported
   like an onboarding.
7. `kit.sh check --all`: every language passes.

## Adding a per-language requirement

For a feature author whose feature needs a new value from every language. Do it in the same
change as the feature:

1. Add the field to its record and to the strict loader in `backend/app/language_data/`, test
   first. The loader now refuses every data file that lacks it, and the guard test
   (`tests/unit/language_kit/test_registry_covers_language_data.py`) fails, naming the field.
2. Add a `Requirement` for it in `backend/language_kit/registry.py`: its path, destination,
   producer, the feature that needs it, a one-sentence description and its rules (reuse a rule
   from `rules.py` or add one class, test first). The guard passes again. Add the new path to the
   expected table in `tests/unit/language_kit/test_registry.py` and one invalid value for it to
   `BROKEN_VALUES` in `tests/unit/language_kit/test_seeded_omissions.py`; both tests say so if you
   forget.
3. `kit.sh requirements` shows the new item; `kit.sh backfill --all` writes a pack asking for it.
4. Fill each pack, then `kit.sh finish <code> --pack <path>` for each language.
5. `kit.sh check --all` passes.

Nothing else changes: the pack template, validation, check, backfill and the data file layout all
come from the registry. This skill never lists requirements, so it needs no edit.

## Rules

- While onboarding or backfilling, never read app source (`backend/app`, `frontend/src`,
  `backend/tests`). Everything you need is in the pack's guidance and the kit's output.
- Never edit the generated data files by hand (`backend/app/language_data/languages/*.toml`,
  `backend/tests/integration/practice_languages/evaluation/*.toml`). Change them with a pack.
- Set each voice's gender from the voice's name or its model card; the catalogue has no gender
  field, and the report says the genders were asserted, not checked by listening.
- The Spanish and German examples in a pack are guidance, not text to translate word for word.
  Write natural, everyday sentences a learner would say in the new language.
- Host names are common first names of the language; guest labels are the language's own words
  for a guest, caller or presenter.
- Run commands one at a time and read their summary; do not pipe kit output through other tools.
- If `finish` fails in a suite and the failing tests are not about your pack's values, stop and
  report the `FAIL` lines and log paths to the maintainer. Do not change code to make it pass.
