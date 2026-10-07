# Validation record: Language Onboarding Kit (008)

The plan's validation record: what was checked by hand, how, and what it showed.

## Italian onboarded through the skill (T080, T081; SC-001, SC-002, SC-003)

**How**: a separate agent session, started with only the `language-kit` skill and the maintainer's
content choices (research R13), was told not to read or edit anything but `SKILL.md` and files under
`languages/it/`. It ran `prereq` → `scaffold` → filled `pack.toml` → `validate` → `finish`.

| Criterion | Target | Result |
|---|---|---|
| SC-001: files written | only the two generated data files, plus `languages/it/` | **Met.** Commit `8cf4d1f` holds `backend/app/language_data/languages/it.toml`, `backend/tests/integration/practice_languages/evaluation/it.toml`, and `languages/it/` (`pack.toml`, `run-log.jsonl`, `report.md`; logs are git-ignored). The only hand-edited file is `pack.toml`. |
| SC-002: working time | < 30 min, excluding downloads | **Met: about 5 minutes.** `prereq` at 22:43:27Z, first `finish` exit at 22:48:20Z (4 min 53 s). Downloading both voices took 3.8 s (`run-log.jsonl`). |
| SC-003: no app source read | `Read`/`Edit` only on `SKILL.md`, `pack.toml`, `languages/it/` | **Met.** The session's only file reads and edits were `languages/it/pack.toml`. Its shell commands were `kit.sh` commands, a script that filled `pack.toml`, `date`, `git status`, and reads of the `languages/it/logs/` files. Nothing under `backend/app`, `backend/tests`, `backend/language_kit` or `frontend/`. |

**The first `finish` failed, correctly.** Its verify step found 17 failing tests and one black
failure. None were about the Italian data. The kit's own unit tests copied every real language into
their temporary repository and assumed exactly Spanish and German; one settings test counted four
voices; one test file was unformatted. The agent stopped and reported, as instructed. The fix
(commit `a91970c`) made those tests use a fixed
Spanish and German pair (FR-019). `kit.sh finish it` was then re-run on the agent's pack unchanged:
`apply nothing-to-do, verify ok, check ok, report written`. Both voices were downloaded and
MD5-verified by `apply` (`voices_downloaded` in the run log).

The agent's feedback on the pack also changed the guidance:
- an item with a default now reads as optional;
- the voice example says the `[[voices]]` tables go before `[podcast]` and shows only pack keys;
- guest labels are described;
- the header no longer contains the word TODO;
- the skill says to stop and report a failure that is not about the pack.

## Italian works for a learner (T082; SC-008, SC-009)

Checked through the real API on the real stack (Piper, faster-whisper `base`, Ollama `llama3.1:8b`),
with a throwaway database:

| Check (quickstart §6) | Result |
|---|---|
| Practice languages | `es` Spanish, `de` German, `it` Italian, in that order |
| Italian voices | `it_IT-paola-medium`, `it_IT-riccardo-x_low`, both installed |
| Settings → Italian; Order at a Restaurant | conversation `target_language` `it`; the partner opens "Ciao! Benvenuto nel nostro ristorante." |
| Podcast catalogue in Italian | a show casts Silvia (Paola's voice) and Lorenzo (Riccardo's voice) |
| Speech in, accents kept | Paola saying "Perché la città è così bella?" transcribes as `perché la città è così bella` |

**Not done here, for a person:** the browser walk-through of §6 (three cards with arrow-key movement,
the learning tools, Beginner level and Strict corrections, flashcards, Panel playback, Summary, Past
Chats) and the keyboard and contrast check of the three cards (Constitution IV). The frontend did not
change, and its Vitest and Playwright suites passed in every `finish`.

**SC-008**: `git diff master...HEAD -- backend/app frontend/src`, outside `language_data/languages/`,
contains no Italian-specific code (no `Italian`, `it_IT`, or `"it"` line added).

**SC-009 / quickstart §10, learner data untouched**: the copy of the learner database made for the
row-by-row comparison was lost when the session's scratch directory was cleared. A stronger check
replaces it: `~/.open-language/app.db` was last written at 2026-10-06 20:46:39 (−04:00), before the
first 008 commit (20:53:54), and has no WAL file, so nothing has written to it since. The practice
language is still `es` and all 41 conversations are there.

## Spanish backfilled through the kit (T078)

`kit.sh backfill es` wrote a pack of the four missing evaluation items. It was filled, validated
(0 errors) and applied with `kit.sh finish es --pack …`, which wrote only
`evaluation/es.toml`. The first run's verify failed on kit tests that assumed Spanish had no
evaluation set; after the fix, the second run passed every suite (pytest 2791, Vitest 754,
Playwright 285, linters). Report: `languages/es/report.md`.

## Benchmarks (T091, T092; SC-007)

German, through `kit.sh bench de`, from `evaluation/de.toml`, whose values equal 006's
`german_evaluation_set.py` (pinned by `test_evaluation_sets.py`), written in 006's format with one
transcription table per voice:

| Figure | Target | 006 | 008 |
|---|---|---|---|
| Adherence (`llama3.1:8b`) | ≥ 95% | 50/50 | **50/50** |
| Transcription, Whisper `base`, Kerstin | ≥ 18/20 | 13/20 | **12/20** |
| Transcription, Whisper `base`, Thorsten | ≥ 18/20 | not run | **17/20** |

The figures are not expected to be identical (plan interpretation 7). The 008 run also counts Italian
words as foreign. Transcription still misses on `base`, as recorded in 006.

Italian, through `kit.sh bench it` (T092), with no Italian-specific benchmark code:

| Figure | Target | 008 |
|---|---|---|
| Adherence (`llama3.1:8b`) | ≥ 95% | **46/50, missed** |
| Transcription, Whisper `base`, Paola | ≥ 18/20 | **6/20, missed** |
| Transcription, Whisper `base`, Riccardo (x_low) | ≥ 18/20 | **5/20, missed** |

- **Adherence**: the 4 flagged replies wait in `languages/it/review-sheet.md` for a verdict. At least
  one flag is false ("out", from "check-out", which Italian uses as a loanword). One looks real
  ("bagaglio hand").
- **Transcription**: the misses are real Whisper `base` errors on Piper speech ("al mare" → "ad
  ammare", "carta" → "catta", "Lunedì" → "L'une di"). Some sentences also fail only because number
  words come back as digits ("cento" → "100", "dieci" → "10"). A later Italian dictation set should
  avoid number words.
- Both misses appear under *Open items* in `languages/it/report.md`. The plan leaves the shipping
  decision to the maintainer (spec Assumptions).

**`kit bench it --adherence` with Ollama stopped**: not run here, because Ollama serves other work on
this machine. The same path is covered by
`test_bench_command.py::test_without_ollama_adherence_exits_three_names_it_and_writes_nothing`.
`OllamaProbe` checks `/api/tags` and names Ollama when it is unreachable.
