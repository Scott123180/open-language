# Contract: `language_kit` command line and the `language-kit` skill

**Feature**: [../spec.md](../spec.md) | **Research**: R3, R9–R12

## Invocation

```bash
.claude/skills/language-kit/kit.sh <command> [args]
# is exactly
cd backend && .venv/bin/python -m language_kit <command> [args]
```

`kit.sh` fails with exit 2 and the message "backend/.venv is missing: run ./run.sh --setup" when the
venv is absent. It does nothing else.

## Common options

| Option | Meaning |
|---|---|
| `--dry-run` | Report what would change; change nothing. Accepted by every command that writes (`scaffold`, `apply`, `backfill`, `bench`, `finish`, `report`). |
| `--json` | One JSON document on stdout instead of text. |
| `--out DIR` | The per-language output root. Default: `<feature_directory>/languages` from `.specify/feature.json`. |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done, or nothing to do |
| 1 | Findings: validation errors, a failing check, a missed benchmark threshold |
| 2 | Usage error or unmet prerequisite (nothing was changed) |
| 3 | External failure: network, download checksum, a test suite or linter failing |

## Output shape (text)

```text
<command> <code>: <one-line summary>
FAIL <code> <path>: <rule>. <detail>
WARN <code> <path>: <rule>. <detail>
→ next: <the next command to run, when there is an obvious one>
```

Passing items are counted in the summary, never listed. Lines are ≤ 120 characters. Long values are
cut to 60 characters with `…`.

---

## Commands

### `prereq <code>`

Read-only, apart from the voice-catalogue cache. It checks research R7 in order and stops at the
first failure (exit 2). On success it lists the candidate voices:

```text
prereq it: Italian can be onboarded (5/5 checks, 1 warning)
voice it_IT-paola-medium     Italy  medium  64 MB
voice it_IT-riccardo-x_low   Italy  x_low   28 MB
voice it_IT-serena-medium    Italy  medium  64 MB
voice it_IT-serena-high      Italy  high    114 MB
WARN it wordfreq: ...   (only if not covered)
→ next: kit.sh scaffold it --name Italian
```

### `scaffold <code> --name <English name>`

Runs `prereq` first, then writes `<out>/<code>/pack.toml` (see [pack-format.md](pack-format.md)).
If the pack already exists, it reports `nothing-to-do` and never overwrites it.

### `validate <code> [--pack PATH]`

Read-only. It parses the pack (default `<out>/<code>/pack.toml`), merges it onto the language's
existing data, if any, and prints every finding. Exit 0 if there are no errors (warnings allowed),
else 1. A TOML syntax error is reported as `FAIL <code> pack: line N: <message>`.

### `apply <code> [--pack PATH]`

1. Runs `validate`; stops with exit 1 on errors.
2. Downloads and MD5-verifies missing voices; exit 3 on failure (repository untouched).
3. Writes the runtime and evaluation data files atomically (research R9).

If the rendered files equal the current ones and all voices are present, it reports `nothing-to-do`.
With `--dry-run`, it prints `would write <path> (+A −R lines)` and `would download <key> (<size>)`.

### `verify [--backend-only]`

Runs, from the repository root:
- `backend/.venv/bin/pytest`;
- `ruff check`;
- `black --check`;
- `mypy app language_kit`;
- `npm run lint`, `npm test -- --run` and `npm run test:e2e`, in `frontend/` (skipped with
  `--backend-only`, and the report says so).

It prints one line per suite. Full output goes to `<out>/<code>/logs/<suite>.log` when a language
is given with `--language <code>`, else `<out>/_logs/`.

### `check [<code> | --all]`

Read-only. It checks catalogued languages' data files against every requirement that is not
onboarding-only. It also reports, as information, how many of each language's voices are installed.

```text
check: 3 languages, 14 requirements, 0 failing (es ✓, de ✓, it ✓)
```

### `backfill [<code> | --all]`

For each language with failing items, it writes `<out>/<code>/backfill-pack.toml` holding only
those items, each with its guidance and an example from a passing language. A language with nothing
missing is listed as `nothing-to-do`. Apply the result with `apply <code> --pack <path>`.

### `bench <code> [--adherence | --transcription]`

Both kinds run by default. It sets `OPEN_LANGUAGE_BENCH_LANGUAGE=<code>` and
`OPEN_LANGUAGE_BENCH_OUT=<out>/<code>/`, then runs
`pytest -m benchmark -s <benchmark files>`. It prints each figure against its threshold and the
paths of `benchmark-results.md` and `review-sheet.md`. Exit 1 on a missed threshold (the files are
still written), and exit 3 when Ollama, the model or a voice is unavailable (nothing is written).

### `report <code>`

Renders `<out>/<code>/report.md` from `run-log.jsonl` (data-model § OnboardingReport). It always
regenerates the whole file.

### `finish <code> [--backend-only]`

`apply`, then `verify`, then `check <code>`, then `report <code>`. It stops at the first step
with exit ≥ 2 and still writes the report. This is the one command an agent runs after the pack
validates.

### `requirements`

Read-only. It prints the registry as a table: path, producer, needed by and rules. It is for
feature authors and for the skill's "Adding a per-language requirement" section.

---

## Skill contract (`.claude/skills/language-kit/SKILL.md`)

- **Frontmatter**: `name: language-kit`, and a description that triggers on "add a language",
  "support Italian", "new practice language", "per-language data", "backfill languages".
- **Sections**, in this order:
  1. *When to use*.
  2. *Onboard a language*: `prereq` → choose voices → `scaffold` → fill the pack → `validate` until
     clean → `finish` → `bench` → `report`.
  3. *Backfill after a new requirement*.
  4. *Adding a per-language requirement* (research R12).
  5. *Rules*: no app source reading while onboarding, no hand edits to generated files, genders
     from the voice's name or model card, and Spanish and German examples in the pack are guidance,
     not text to translate word for word.
- **No requirement list** in the skill. The pack and `requirements` are the source.
- **Length**: ≤ 150 lines.
