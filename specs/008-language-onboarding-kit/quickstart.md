# Quickstart: validating the Language Onboarding Kit

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **CLI**: [contracts/cli.md](contracts/cli.md)

Runnable checks that prove the feature end to end. `kit` below means
`.claude/skills/language-kit/kit.sh`, run from the repository root.

## 0. Prerequisites

- `backend/.venv` set up with dev extras (`backend/.venv/bin/pip install -e "backend[dev]"`). This
  pulls in the new `tomli-w`.
- For §5–§7: network access (voice catalogue and download), Ollama with `llama3.1:8b`, and a GPU or
  patience for Whisper.
- Work on the feature branch. §3 and §8 change files on purpose and are reverted with
  `git checkout -- <files>`.

## 1. The default suite stays green and hermetic

```bash
cd backend && .venv/bin/pytest && .venv/bin/ruff check . && .venv/bin/black --check . && .venv/bin/mypy language_kit app/language_data
cd ../frontend && npm run lint && npm test -- --run && npm run test:e2e
```

**Expect**:
- everything passes, with coverage ≥ 90% across `app` and `language_kit`;
- no test touches the network, Ollama or Whisper (the benchmark and `claude_live` markers stay
  deselected);
- the pinning test for today's `PRACTICE_LANGUAGES` and `AVAILABLE_VOICES` values passes, so
  Spanish and German data are unchanged after the move to data files (FR-021).

## 2. Spanish and German pass the completeness check (US2, FR-021)

```bash
kit check --all
```

**Expect** `check: 2 languages, 14 requirements, 0 failing (es ✓, de ✓)` before Italian is
onboarded (3 languages after), exit 0. Spanish passes because its evaluation set was written
through backfill and `finish --pack` (research R2). Its `backfill-pack.toml`, `run-log.jsonl` and
`report.md` are in `languages/es/`.

## 3. Seeded omissions are caught (SC-004) and the guard fires (SC-005)

```bash
backend/.venv/bin/pytest backend/tests/unit/language_kit -k "seeded"
```

The test removes or breaks each requirement in turn, for each language, on a temporary copy of the
data, and asserts that `check` fails naming exactly that language and path.

By hand, once:
1. Delete two names from `podcast.host_names.female` in a copy of `de.toml`. Run
   `kit check de`. **Expect** `FAIL de podcast.host_names.female: at least 10 names (found 8)…`,
   exit 1. Revert.
2. Add a field `greeting: str` to `PodcastRecord` without a registry entry. Run
   `pytest backend/tests/unit/language_kit/test_registry_covers_language_data.py`. **Expect** a
   failure naming `PodcastRecord.greeting` and `language_kit/registry.py`. Revert.

## 4. Read-only and dry-run commands change nothing (FR-005)

```bash
git status --short > /tmp/before
kit check --all; kit requirements; kit prereq it
kit validate es --pack specs/008-language-onboarding-kit/languages/es/backfill-pack.toml
kit apply es --pack specs/008-language-onboarding-kit/languages/es/backfill-pack.toml --dry-run
kit scaffold fr --name French --dry-run
git status --short | diff /tmp/before -
```

**Expect** no diff.

## 5. Onboard Italian with the kit (US1, FR-024; SC-001, SC-002, SC-003)

Do this in a fresh Claude Code session with only the `language-kit` skill invoked, so the session
record can be checked for SC-003. Start a timer.

```bash
kit prereq it                        # 6/6 checks; lists paola, riccardo, serena-medium, serena-high
kit scaffold it --name Italian       # writes languages/it/pack.toml
# agent fills pack.toml (voices, genders, names, labels, sample line, evaluation set)
kit validate it                      # repeat until "0 errors"
kit finish it                        # apply → verify → check → report
```

**Expect**:
- `finish` writes exactly two repository files: `backend/app/language_data/languages/it.toml` and
  `backend/tests/integration/practice_languages/evaluation/it.toml`;
- the chosen voices are in the voice directory with matching MD5;
- every suite passes, and `check --all` reports `3 languages … 0 failing`;
- `report.md` exists.

**SC-001**: `git diff --name-only master...HEAD -- backend run.sh frontend` for the Italian
commit lists only the two generated files. The only hand-edited file is `pack.toml`.

**SC-002**: time from `prereq` to `finish` exiting 0, minus the download time logged in
`run-log.jsonl`, is under 30 minutes.

**SC-003**: the session record shows `Read` and `Edit` calls only on `SKILL.md`, `pack.toml` and
files under `languages/it/`, and none under `backend/app`, `frontend/src` or `backend/tests`.

## 6. Italian works end to end for a learner (US1 scenario 5; SC-008)

Restart the app (`./run.sh`). In the browser:
1. **Settings**: three practice-language cards. Arrow keys move Spanish → German → Italian. Choose
   Italian. The voice list shows only Italian voices, with the default selected. Save.
2. **Home → Order at a Restaurant**: the greeting is Italian and is spoken in Paola's voice. Speak a
   sentence with "perché" or "città". It is transcribed with its accent.
3. Use translation, alternative phrasing, word lookup, suggestions and the expression helper once
   each. The Italian side is Italian, and explanations are English. Set the level to Beginner, then
   corrections to Strict, and send one wrong sentence.
4. Save two words. **Flashcards** (with Italian selected) shows only those words. Generate a deck
   and play a word's audio (Italian voice).
5. **Podcasts → Panel → any ready-made show**: two hosts with Italian names, each in their own
   voice. Preview a voice: the sample line is Italian with the host's name. Open the Summary in
   Italian and in English.
6. **Past Chats**: the Italian conversation is labelled Italian. Continue an older Spanish one: it
   stays Spanish.

**SC-008**: `git diff master...HEAD -- backend/app frontend/src` contains no Italian-specific code,
only the data file.

## 7. Benchmarks for any language (US3; FR-022, FR-023; SC-007)

```bash
kit bench de     # German, from the generalised benchmarks
kit bench it
kit report it
```

**Expect**:
- `languages/de/benchmark-results.md` has 006's sections (adherence figure, one transcription table
  per voice) computed from `evaluation/de.toml`, whose content equals 006's
  `german_evaluation_set.py`;
- the same files for Italian, with no Italian-specific benchmark code;
- a missed threshold still writes both files, exits 1, and appears under *Open items* in
  `report.md`;
- stopping Ollama and running `kit bench it --adherence` gives exit 3, writes nothing, and names
  Ollama.

## 8. A new per-language requirement is backfilled (US4; FR-025, SC-005)

On a scratch branch (not merged):
1. Add `PodcastRecord.greeting` (test first) and a `Requirement("podcast.greeting", …)`. The guard
   passes, and the strict loader now fails. Mark the field optional in the loader for this
   exercise.
2. `kit check --all`: **expect** each language to fail on `podcast.greeting` only.
3. `kit backfill --all`: **expect** three `backfill-pack.toml` files, each with only `code` and
   `[podcast] greeting`.
4. Fill them, then `kit finish <code> --pack … --backend-only` for each. **Expect** the diff of each runtime file to
   be the added `greeting` line only (FR-025 scenario 3).
5. `kit check --all` passes. The `SKILL.md` diff on this branch is empty (US4 scenario 5).

Discard the branch.

## 9. Idempotency (FR-006; SC-006)

```bash
kit scaffold it --name Italian; kit apply it; kit backfill --all; kit finish it --backend-only
git status --short
```

**Expect**:
- each command reports `nothing-to-do` (`finish` still runs the suites and rewrites `report.md`);
- `git status` shows only `languages/it/report.md`, `run-log.jsonl` and logs, and no change under
  `backend/` or `run.sh`. Those three are the kit's own run records, which SC-006 does not cover
  (plan.md § "Spec interpretations" 8).

## 10. Learner data is untouched (FR-017; SC-009)

Before §5, copy the learner database:
`cp ~/.local/share/open-language/app.db /tmp/pre-008.db`, or the `db_path` from settings. After
§6 step 1, but **before** saving Settings, compare every table except `app_settings` and
`voice_choices` row by row (the existing `test_upgrade_preserves_data.py` helper does this).
**Expect** no difference, and the practice language is still the one selected before.

## 11. Setup downloads the catalogued voices

```bash
OPEN_LANGUAGE_VOICE_DIR=$(mktemp -d) ./run.sh --setup
```

**Expect** six voice downloads (es ×2, de ×2, it ×2) with no edit to `run.sh` for Italian, and
`backend/.venv/bin/python -m app.language_data voice-keys` lists the same six keys.
