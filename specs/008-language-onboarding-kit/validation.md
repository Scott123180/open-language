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

**Browser walk-through of §6 (T100, 2026-10-07).** Done in headless Chromium, driven step by step
by an agent session, against the real stack (Claude Sonnet as the learner's selected partner, Piper,
faster-whisper `medium` from the learner's settings). The app ran as a second instance on its own
ports, against a copy of the learner database and with its own audio cache, so the learner's running
app and data were not touched. Chromium's fake microphone played a Paola recording of "Perché la
città è così bella?".

| Step (quickstart §6) | Result |
|---|---|
| 1. Settings | Spanish, German, Italian cards. Arrow keys move Spanish → German → Italian. The voice list shows only Paola (Italy) and Riccardo (Italy), with Paola selected. Saved |
| 2. Order at a Restaurant | The greeting is Italian ("Buongiorno! Benvenuto al nostro ristorante…") and is spoken in Paola's voice (22 kHz, median pitch 210 Hz; Paola 188 Hz, davefx 134 Hz). The spoken sentence is transcribed with its accents, "Perché la città è così bella?", and the partner answers in Italian |
| 3. Learning tools | Translate, Grammar, Phrasing (three Italian alternatives), word lookup ("tavolo (noun, masculine). Definition: table…"), Suggestions (Italian) and the expression helper ("English → Italian", answering "Posso avere il conto, per favore?") all work; explanations are English. With Beginner level and Strict corrections, "Io volere un tavolo per due persona." gets two corrections, "voglio" (conjugation) and "persone" (agreement) |
| 4. Flashcards | With Italian selected, *My Words* lists only the two saved words, "tavolo" and "ristorante". A Listen deck is generated (`?language=it`), and the word's audio plays in Paola's voice (200 Hz) |
| 5. Podcasts | Every ready-made show casts Italian hosts. Weekend Food Talk, Panel, Short: Silvia (Paola) and Lorenzo (Riccardo). The voice previews say "Ciao, sono Silvia. Benvenuti alla trasmissione!" and the same with Lorenzo (checked by transcription). Each line is spoken in its host's own voice: Lorenzo's at 16 kHz, which only Riccardo x_low produces, and Silvia's at 22 kHz and female pitch. The learner's line gets an Italian reply. The Summary works in English and in Italian |
| 6. Past Chats | The Italian chat and episode are labelled Italian. An older Spanish chat opened while Italian is selected stays Spanish, and so does its expression helper ("English → Spanish") |

Past Chats has no *Continue* control for roleplay chats (only for episodes), so the older Spanish
chat was opened from its URL.

**Keyboard and contrast of the three cards (T101; Constitution IV).** In the running app, arrow keys
move focus and selection across all three cards. Screenshots in light and dark mode show a visible
teal focus ring and the selected card's highlight. A new Playwright group, *Practice language — a
third language added by data alone* in `frontend/e2e/practice-language.spec.ts`, now covers this
on every run:
- three cards in catalogue order;
- arrow-key movement to Italian;
- only Italian voices, with Paola selected;
- a WCAG text contrast of at least 4.5:1 on every card label, in light and in dark mode.

This was an agent's check, not a person's. A screen-reader pass remains under *Not checked* in
every report.

**The kept Italian report records every suite (T103).** The committed `languages/it/report.md`
came from the §9 `--backend-only` re-run, so it listed the frontend suites as skipped. `kit.sh finish
it` was re-run without the flag: `apply nothing-to-do, verify ok, check ok, report written`. The
report now lists pytest 2847, ESLint, Vitest 754 and Playwright 290, all passing, and the
completeness check.

**SC-008**: `git diff master...HEAD -- backend/app frontend/src`, outside `language_data/languages/`,
contains no Italian-specific code (no `Italian`, `it_IT`, or `"it"` line added).

**SC-009 / quickstart §10, learner data untouched**: the copy of the learner database made for the
first row-by-row comparison was lost when that session's scratch directory was cleared. At the time,
the file's timestamps stood in for it: `~/.open-language/app.db` was last written before the first
008 commit.

**Redone on 2026-10-07 (T102).** Steps:
1. A consistent read-only snapshot was taken of `app.db` (SQLite backup API): practice language
   `es`, 42 conversations.
2. A copy of it served the second app instance.
3. That app started with Italian catalogued. Settings was opened and Italian chosen, by arrow keys,
   but not saved (§6 step 1).
4. The copy was then compared with the snapshot, row by row and every column, over every table
   except `app_settings` and `voice_choices`.

**Result: 19 tables and 591 rows, no difference.** The practice language and voice were unchanged
(`es`, `es_ES-davefx-medium`). The comparison covered every table and every column, which is stricter
than the `test_upgrade_preserves_data.py` helper (its fixed table list and pre-006 columns).

The redo had one side effect on the learner's machine, now undone. Until its restart with a
separate home directory, the second instance wrote three audio files into the learner's
`~/.open-language/tts_cache/`. The cache is keyed by message and word id, and those ids (messages
366 and 368, word 30) were not yet used by the learner's database, which ends at message 365 and word
28. The files were moved out, so no later message can pick them up. The voice-samples directory was
not touched.

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

## Read-only, idempotency and setup (T097; FR-005, FR-006, FR-015, SC-006)

- **§4: read-only and dry-run commands.** `check --all`, `requirements`, `prereq it`,
  `validate es --pack …`, `apply es --pack … --dry-run` and `scaffold fr --name French --dry-run` left
  `git status` unchanged.
- **§9: idempotency.** On the onboarded Italian, `scaffold it --name Italian`, `apply it` and
  `backfill --all` each reported `nothing-to-do`. `finish it --backend-only` reported
  `apply nothing-to-do, verify ok, check ok, report written`. Afterwards `git status` showed only
  the kit's own run records, `languages/it/report.md` and `run-log.jsonl` (logs are git-ignored).
  Nothing changed under `backend/` or in `run.sh`.
  - The first attempt found a defect: `scaffold` checked prerequisites before looking for an existing
    pack, so on a catalogued language it refused instead of reporting `nothing-to-do`. Fixed in
    `218f385`.
- **§11: setup downloads every catalogued voice.** `OPEN_LANGUAGE_VOICE_DIR=$(mktemp -d) ./run.sh
  --setup` downloaded all six voices (es ×2, de ×2, it ×2) and completed. `run.sh` has no edit for
  Italian, and `python -m app.language_data voice-keys` lists the same six keys.

## A new per-language requirement is backfilled (T098; quickstart §8, FR-025, SC-005)

The exercise ran on a scratch branch, which was discarded. It added `PodcastRecord.greeting`
(optional in the loader, as §8 says) and a `Requirement("podcast.greeting", …)`.

| Step | Result |
|---|---|
| Record field alone | the guard test fails: "`PodcastRecord.greeting` is per-language data with no entry in `language_kit/registry.py`. Add a Requirement for it (see the language-kit skill, 'Adding a per-language requirement')" |
| `kit.sh check --all` | `3 languages, 15 requirements, 3 failing`: only `podcast.greeting`, for es, de and it |
| `kit.sh backfill --all` | three packs, each holding only `code` and `[podcast] greeting = "TODO"` |
| fill, `validate`, `apply`, `finish --pack … --backend-only` each | each runtime file's diff is one added `greeting = "…"` line |
| `kit.sh check --all` | `0 failing (es ✓, de ✓, it ✓)` |
| `SKILL.md` diff | empty |

**Findings, now fixed on the feature branch:**
1. **An applied backfill pack blocked every later backfill.** Spanish's committed, applied pack from
   T078 meant `backfill es` reported `nothing-to-do` and wrote nothing. A pack that would no longer
   change the language is now replaced; one still being filled is kept (`3ead801`).
2. **The kit's own tests failed after a backfill.** Their Italian test pack was written out by hand,
   so it lacked the new item, and two tests used `greeting` as an imaginary example. The test pack
   now comes from the committed Italian data, and examples use a name no real field will take
   (`8570382`).
3. **Finishing the first of several backfills failed verify.** The real-repository `check --all` test
   is red until every language has the item. The skill now says to `apply` every pack first, then
   `finish` each (`7cc158c`).
4. **One template test hard-coded the list of pack items.** It now checks the ordering rule instead.

On the second run, after findings 1–3 were fixed, the only failure left was finding 4. Its test has
since been rewritten, and it passes with an extra requirement registered.

**Third run, in full, on 2026-10-07 (T104).** It ran in a separate worktree on a scratch branch,
which was then discarded, so the learner's running app (`uvicorn --reload`) never saw the change.

| Step | Result |
|---|---|
| Loader test first | `PodcastRecord.greeting` (optional) fails its two new loader tests, then passes |
| Record field alone | the guard fails with the message above, naming `PodcastRecord.greeting` |
| `Requirement("podcast.greeting", …)` + the two test-table rows | `kit.sh requirements` lists it; `check --all`: `3 languages, 15 requirements, 3 failing`, only `podcast.greeting`, for es, de and it |
| `backfill --all` | three packs, each only `code` and `[podcast] greeting = "TODO"`; Spanish's applied pack from T078 is replaced, as finding 1's fix intends |
| fill, `validate` (0 errors each), `apply` each | each runtime file's diff is the one `greeting` line |
| `finish <code> --pack … --backend-only` each | `apply nothing-to-do, verify ok, check ok, report written`, for es, de and it (pytest 2856 passed each) |
| `check --all` | `3 languages, 15 requirements, 0 failing (es ✓, de ✓, it ✓)` |
| `SKILL.md` diff | empty |

The first attempt at the `finish` step failed three `test_template.py` tests in every language. The
cause was the exercise, not the kit: it gave the requirement `needed_by="scratch"`. The template
prints any value, but the tests' guidance-header pattern (`needed by (\d+)`) accepts only a numeric
feature id, as every real requirement has. With `"009"`, as the next feature would give, every suite
passed. A feature author who gives a non-numeric id gets the same three failures; the registry
does not reject such an id itself. A feature author still extends two test tables by hand:
the expected rows in `test_registry.py` and `BROKEN_VALUES` in `test_seeded_omissions.py`. Both fail
with a clear message, and the skill names them.
