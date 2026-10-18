# Implementation Plan: Recurring Podcast Shows

**Branch**: `010-recurring-podcast-shows` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/010-recurring-podcast-shows/spec.md`

---

## Summary

Podcast mode (007) treats every episode as a one-off. This feature makes a show a **series**:
- the same hosts return episode after episode, in each practice language;
- they remember the topics covered and what the learner shared, and refer back to it;
- they are only replaced when the learner recasts one on purpose.

The quick **one-off** episode stays one choice away. Around that, the feature adds:
- **favourites** and a **My shows** group;
- **Find a new show**, a set of fresh, personalised suggestions that leaves the ready-made list as
  it is;
- a themed **drop-down** for every select in the app.

The design rests on five decisions from [research.md](research.md):

1. **A series sits beside episodes, not inside them** (R2, R3). A series is a show in one language
   with its own two hosts. A link table, `podcast_series_episodes`, marks which episodes belong
   to it. Starting a series episode copies the series' hosts into the episode's `podcast_hosts`,
   exactly as 007 copies a draft's hosts, so the whole 007 episode pipeline runs unchanged:
   - one-off and pre-feature episodes have no link row, so FR-007 and FR-022 hold by
     construction;
   - reset deletes one row and the cascade does the rest.
2. **Memory reaches the model as a snapshot taken at the start** (R5). The engine fingerprints the
   standing prompt, and the cues are re-rendered from stored facts (007 R3). So a series episode
   stores, when it starts, the bounded list of what the hosts remember. Its standing prompt and
   its `open`/`greet` cues are rendered from that snapshot only. A one-off's prompt and cues stay
   byte-identical to 007's.
3. **Memory is written in the background, and Start waits for it with a message** (R6, R7). A
   `SeriesMemoryKeeper` makes one structured call per episode chunk, after a series sign-off and
   when the setup screen opens a series:
   - it writes at most 3 points about the learner per episode and keeps the newest 10 topics and
     8 learner points, within a 1,200-character text budget, so the stored list always fits the
     prompt section whole (FR-006, SC-006);
   - learner points are only taken from chunks that contain learner lines, so a Listen episode
     remembers topics only;
   - if the learner presses Start while memory is still catching up, the setup screen says so
     ("Hugo and Inés are catching up on episode 3…"), waits up to 30 s, and then starts on its
     own. A failure or timeout offers **Try again** or **Start without it**. Usually memory is
     already up to date and nothing waits.
4. **The series' hosts are checked, not trusted** (R2, R8). A series episode after the first must
   start with the series' hosts, or it is refused with a plain 409. There is no Shuffle once a
   series has started. **Recast…** is a confirmed server action that changes one slot for this and
   every later episode, so SC-001 is guaranteed by construction.
5. **Drop-downs become an in-app listbox** (R11). A native popup is drawn by the browser and the
   OS; 007's CSS fix did not hold, and Playwright cannot inspect a native popup. `ThemedSelect`
   (WAI-ARIA select-only combobox, design tokens only) replaces all five native selects, so
   FR-021 and SC-008 can be tested automatically in both themes.

What is new:
- five tables, all additive, in `app/podcasts/models.py`;
- seven endpoints (favourites, remove a kept show, discover, series detail, recast, reset, memory
  catch-up) and new fields on the catalogue and episode responses, all additive;
- two shared frontend components (`ThemedSelect`, `ConfirmDialog`) and one shared hook
  (`useListboxNavigation`), ten podcast components and four hooks.

No new dependency, voice or per-language data is needed.

The real risk is the local model's **recall** (SC-002, SC-003). It is measured with the hand-run
benchmark and review-sheet pattern of 003, 005 and 007 before any claim is made. If it misses,
series ship labelled experimental (spec Assumptions).

---

## Technical Context

**Language/Version**: Python ≥ 3.11 (`backend/.venv` runs 3.14.4); TypeScript 5.4 / React 18.3

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0, the `ollama` client and the `claude -p` adapter (004).
  `StructuredLLMProvider.chat_json` serves the memory keeper and Find a new show, as it serves
  007's generator and summary.
- **No new dependencies.** No new voices (R13).
- Frontend: React 18, react-router-dom v6, TanStack Query v5, Vitest + Testing Library,
  Playwright. **No new dependencies**: the listbox is in-app (R11).

**Storage**: SQLite (WAL, foreign keys on). Five new tables via `create_all()` (data-model §2):
- `podcast_shows`;
- `podcast_series`;
- `podcast_series_hosts`;
- `podcast_series_episodes`;
- `podcast_series_memories`.

No `_ADDITIVE_COLUMNS` entry, no existing column, and no existing row is updated.

**Testing**:
- pytest unit, contract and integration tests, ≥ 90% coverage;
- seeded property tests for memory bounding and discovery seeds;
- a golden test pinning one-off prompts to 007;
- a frozen `tests/fixtures/schema_007.sql` upgrade test (SC-009);
- the `benchmark` marker for the hand-run checks (quickstart §3);
- Vitest;
- Playwright E2E: four new specs, and five existing specs moved to the shared `chooseOption()`
  helper.

**Target Platform**: Linux desktop, local-first (Ollama, Piper, faster-whisper). Claude is opt-in
(004). Series must work fully offline on the local stack.

**Project Type**: Web application (FastAPI backend + Vite/React frontend).

**Performance Goals**:
- SC-006: episode 10's first host line within 20% of episode 1's. `POST /episodes` never calls
  the model (R6), and the series section is capped at 1,800 characters (R7).
- Catch-up wait before a series Start, when memory is not up to date: p90 ≤ 15 s on the local
  setup, capped at 30 s, and shown to the learner as a "catching up" message (R6).
- SC-007: Find a new show in ≤ 30 s on the local setup. One structured call for five shows, plus
  at most one top-up call (R10).
- The setup screen loads without waiting for memory. The catch-up is a 202, like 007's
  warm-session call.

**Constraints**:
- FR-007: one-off prompts and cues are byte-identical to 007's (golden test).
- FR-015: `SHOW_TEMPLATES` is untouched.
- FR-022 and SC-009: there is no data migration; pre-feature episodes have no link row.
- Principle VI:
  - the memory keeper and discovery use the selected provider through the factory. The
    process-wide `MemoryCatchUps` holds no keeper or provider: each `start` and `wait` is given a
    keeper built from the request's `get_structured_llm`, so a provider switch (004, no restart)
    applies to the next catch-up;
  - a failure is reported (discovery) or logged and retried at the next trigger (memory), never
    redirected to another provider;
  - memory goes to a cloud provider only inside the episode context the existing Claude notice
    already covers (spec Assumptions).
- 006/008: no language code literal outside the catalogues; no per-language data (R13).

**Scale/Scope**:
- one learner, 3 languages, 8 ready-made shows;
- per series, at most 10 topics and 8 learner points;
- 7 new endpoints, plus additive fields on 3 existing ones;
- about 10 new backend modules inside `app/podcasts/` (including `services/series_snapshot.py`),
  and 15 existing backend files touched (listed under *Function-length plan* and contracts §10);
- frontend: 2 shared components and 1 shared hook, 10 podcast components, 4 hooks (plus the pure
  `catchUpState.ts` reducer), 3 pages touched (Podcasts, PodcastSetup, PodcastEpisode header),
  and 4 non-podcast components moved to `ThemedSelect`.

*No NEEDS CLARIFICATION items remain. The design questions are settled in research R1–R13.*

---

## Spec interpretations

Points where the spec admits more than one reading. Each is resolved here so the choice can be
reviewed.

1. **"Episode" for counting** (spec edge case "abandoned"): any series episode that was started
   counts, even with no lines. It is offered as **Continue** until it finishes, so an empty one is
   reused rather than skipped.
2. **FR-002 with an unfinished episode**: the primary action is **Continue episode N**. Starting a
   new episode is a secondary action and does not close the unfinished one (R4).
3. **FR-008, "series episode after the first"**: the lock applies once the series has one episode.
   Episode 1 of a series keeps Shuffle and the personality choice. Its hosts at Start become the
   series' hosts.
4. **FR-009, choosing the new host**: Recast draws a new name and voice by 007's rules. The dialog
   lets the learner choose the personality ("Any" by default), so `HostCaster.recast` gains an
   optional `personality_id`; 007's Shuffle calls it without one. With two installed voices, the
   recast host usually keeps the slot's voice (007 interpretation 6), and the dialog says so.
5. **FR-010 and the learner's name**: an unstarted ready-made show's hosts are stable *for a given
   language and learner name*. 007's clash avoidance stays for shows with no series, since no
   relationship exists yet. **Series hosts never change name**: a clash is pointed out on the
   setup screen and refused at Start with "change the name the hosts call you" (spec edge case).
6. **FR-013, My shows contents**: the group holds the favourites, the shows with a series in the
   current language, and every *played* learner-made show (US4-3), which has nowhere else to
   appear (R9).
7. **FR-014 and one-off episodes**: playing a one-off of a generated, surprise or suggested show
   also keeps it. "An episode of it is played" covers both kinds.
8. **FR-019 and unfavouriting**: a learner-made show kept only by its favourite (never played, no
   series) is discarded when unfavourited (R9). A played learner-made show stays until the learner
   removes it (FR-024), which deletes the show row and, by cascade, its series in every language;
   the episodes stay in Past Chats.
9. **FR-004, what is remembered**:
   - one topic per episode (the episode's subject);
   - up to three things the learner said about themselves (likes, plans, experiences, opinions),
     each in the conversation's language and in English.

   The learner sees the English version; the hosts get the conversation-language version (R6).
   Nothing the hosts said about themselves is remembered.
10. **FR-005, "acknowledge the show is continuing"** is asked for in the series `open` cue, which
    also asks the host to bring up one remembered point. US1's example has the opener do it. The
    standing prompt permits further references (R5).
11. **FR-006, "bounded"**: newest wins, within fixed caps of 10 topics and 8 learner points and a
    1,200-character budget on the points' text (R7). The budget is enforced when points are
    written, so the stored list always fits the 1,800-character series section whole. What is
    stored is exactly what is remembered and shown: the learner never sees a list that differs
    from what the hosts get.
12. **"Episode deleted from Past Chats"**: the app has no delete today. Every new row cascades from
    `conversations`, so if a conversation is removed, its link and the memories drawn from it go
    with it, and the count follows (R3). No delete feature is added.
13. **FR-016, "at least three"**: the system asks for five and returns three to five after
    filtering (R10).
14. **FR-017, "favour the learner's saved interests"**: with interests, 3 of 5 seeds come from them
    (a deterministic quota, seeded-testable); without, 5 built-in everyday topics. The quota
    governs the seeds, not the response: filtering can leave a set where fewer than 3 relate to
    the interests. This is accepted (research R10).
15. **FR-021, "every drop-down"** means every `<select>` in `frontend/src`. There are five today,
    and `ThemedSelect` replaces them all (R11).
16. **Memory timing** (clarified 2026-10-17): memory is written after a series sign-off and when
    the setup screen opens a series. If the learner presses Start while memory is pending or
    being written, the setup screen waits for it (up to 30 s) with a "catching up" message, then
    starts. A failure or timeout offers Try again or Start without it (R6). SC-006 and FR-006
    concern the episode itself: the wait is a visible step before the episode exists, with its
    own measured budget.

---

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design; the result is at the
bottom of this section.*

| Principle | Status | How this design satisfies it |
|---|---|---|
| **I. Clean Code**: ≤ 20-line functions, intention-revealing names, no magic values | ✅ | Every cap and budget is a named catalogue constant (data-model §1). New code is written to the limit. The existing functions this feature touches, and their lengths, are listed under *Function-length plan*; none ends over 20. `WordFilterBar` (197 lines today) is split before its select is replaced (Boy Scout). The frontend's ESLint `max-lines-per-function: 20` override is extended to the new shared files and to the four non-podcast components this feature modifies. |
| **II. SOLID: SRP** | ✅ | Each piece answers one question: <br>• `ShowLibrary`: which shows are the learner's; <br>• `SeriesService`: which hosts and snapshot an episode starts with, and recast and reset; <br>• `SeriesMemoryKeeper`: what to remember from lines; <br>• `MemoryCatchUps`: whether a catch-up is running; <br>• `ShowDiscovery`: which new shows to suggest; <br>• `SuggestionSeeds`: which ideas to try. <br>The routers only sequence them. |
| **II. SOLID: OCP** | ✅ | The 007 episode pipeline is extended through an optional `series` brief and one injected listener. No existing branch changes behaviour for one-off episodes, and a golden test proves it. New caps and sources are catalogue entries. |
| **II. SOLID: LSP** | ✅ | No provider or storage subclass changes contract. `SQLitePodcastStorage.create_episode` keeps its all-or-nothing contract, now with one more row. |
| **II. SOLID: ISP** | ✅ | `ShowLibraryStorage` and `SeriesStorage` are separate small ABCs beside `PodcastStorage`, which gains no methods. `EpisodeEndings` has one method. |
| **II. SOLID: DIP** | ✅ | `EpisodeTurns` depends on `EpisodeEndings`, never on the memory keeper. The keeper takes a `StructuredLLMProvider` and a session factory, both wired in `services/factory.py`. Discovery takes an injected `random.Random`. |
| **III. TDD (non-negotiable)** | ✅ | The pure pieces get their tests first: snapshot round-trip, series prompt section and budget, the memory parser and grounding rule, cap pruning, seed quota, title normalisation. The golden one-off test and the frozen `schema_007.sql` upgrade test are written **before** any prompt or model change. `ThemedSelect`'s keyboard and ARIA tests come before the component. |
| **≥ 90% coverage, zero skipped tests** | ✅ | Benchmarks are deselected by marker, not skipped. The structured provider is a scripted fake from `tests/support`. The background keeper is tested synchronously through an injected executor. |
| **IV. One primary action per screen** | ✅ | Podcasts: choose a show (the favourite toggle and Find a new show are secondary). Setup: **Continue episode N** *or* **Start episode N / Start one-off episode**, never two at once (R4). Recast, Start over and One-off are secondary. |
| **IV. Immediate feedback** | ✅ | The favourite toggle updates at once (optimistic, rolled back with a message on failure). Find a new show shows progress in a live region. Recast shows the new host in place. The remembered list notes "Updating…" while a catch-up runs. A Start that waits on memory says who is catching up on which episode, then starts on its own. |
| **IV. Plain-language, what-to-do-next messages** | ✅ | Every new 404, 409, 422 and 503 says what to do (data-model §6, contracts §2–§8). The Recast and Start over dialogs say exactly what is lost and what is kept. |
| **IV. Accessibility** | ✅ | `ThemedSelect` follows the APG pattern. `ConfirmDialog` is an `alertdialog` with focus trap and return. The favourite toggle is a separate `aria-pressed` button, never nested inside the card's button. My shows is a labelled region, and suggestions use a live region. Manual check in quickstart §6. |
| **V. Compartmentalization** | ✅ | All new code is inside `app.podcasts`; its package root does not change. The factory, the composition root, is the only outside importer of the new storage, keeper and endings modules. `test_module_boundaries.py` is extended to enforce it. `conversation_summary` is not touched or imported (R6 rejects reusing it). |
| **V. Abstractions before implementations** | ✅ | `ShowLibraryStorage`, `SeriesStorage` and `EpisodeEndings` are declared and tested with fakes before the SQLite classes and the keeper. |
| **V. No feature-flag / if-debug guards** | ✅ | Series versus one-off is data: the presence of a link row and snapshot. It is not a flag checked through the code. If SC-002 forces an "experimental" label, it is UI copy, as in 003 and 005. |
| **VI. Provider independence** | ✅ | No provider class or registry change. Memory and discovery use the selected provider through the factory. Failures are surfaced (discovery, 503 with the provider's message) or logged and retried (memory), never redirected. On the local stack nothing new leaves the machine. With Claude, the remembered points travel inside the episode prompt the existing notice covers. |
| **Per-language data** (template gate) | ✅ N/A | This feature adds **no** per-language value: no `Requirement` in `backend/language_kit/registry.py`, no `kit.sh backfill` (R13). |
| **Playwright E2E for frontend changes** | ✅ | New `podcast-series`, `podcast-favourites`, `podcast-discovery` and `themed-select` specs. The `settings`, `conversation-level`, `practice-language`, `flashcards` and `podcasts` specs move to `chooseOption()`, and the Vitest tests of the five controls (and the `Settings`, `Chat` and `Flashcards` page tests that drive them) open the combobox instead of changing a native select. Fixtures are added (contracts §11). |
| **Linting (ruff, black, ESLint, Prettier)** | ✅ | No tooling change beyond extending the ESLint function-length override's file list. |

**Initial gate: PASS.** There are no Complexity Tracking items.

### Function-length plan (Boy Scout, quality gate)

Measured on `010-recurring-podcast-shows` @ `335baa8`. Every existing function this feature
modifies is ≤ 20 lines after the change. All are ≤ 20 today except `WordFilterBar`, which is
brought under the limit when it is touched (constitution Quality Gates).

| Function | Today | Change |
|---|---|---|
| `get_catalog` ([routes.py](../../backend/app/podcasts/routes.py)) | 11 | The listing build moves to `responses.catalog_listings(...)` → ≈ 10 |
| `start_episode` (routes.py) | 16 | Resolution moves to `SeriesService.prepare(req, settings)` → ≈ 14 |
| `_new_episode` (routes.py) | 17 | Moves to `SeriesService`, taking a `PreparedStart`; `series=` is added there, and the hosts come from `_participating_hosts` → ≈ 18 |
| `_remember_start` (routes.py) | 5 | Unchanged |
| `SQLitePodcastStorage.create_episode` ([sqlite_storage.py](../../backend/app/podcasts/services/sqlite_storage.py)) | 13 | + 1 line (`self._add_series_link(...)`) → 14 |
| `get_episode` / `_episode_record` (sqlite_storage.py) | 8 / 17 | Left join on the link table; the record's `series` comes from `_series_facts(link)` → 9 / 18 |
| `build_standing_prompt` ([prompts.py](../../backend/app/podcasts/prompts.py)) | 12 | + `series` parameter, and the sections tuple gains `_series_section(series, cast, label)` (filtered when None) → 14 |
| `render_cue` (prompts.py) | 10 | The instruction lookup moves to `_instruction(cue, cast, label, series)` → ≈ 10 |
| `LoadedEpisode.standing_prompt` ([episodes.py](../../backend/app/podcasts/services/episodes.py)) | 5 | + `self.series_brief` → 5 |
| `episode_history` / `next_turn_history` / `_cue_turn` ([cues.py](../../backend/app/podcasts/services/cues.py)) | 11 / 4 / 4 | + `series` argument passed through → 11 / 4 / 4 |
| `EpisodeTurns.warm` / `_request` / `_after` ([episode_turns.py](../../backend/app/podcasts/services/episode_turns.py)) | 8 / 4 / 7 | Pass the brief; `_after` + 1 line (`self._deps.endings.episode_finished(...)`) → 8 / 4 / 8 |
| `validate_draft` / `_host_problem` ([schemas.py](../../backend/app/podcasts/schemas.py)) | 14 / 10 | The show-level checks move to `show_problem(draft, language)`, which series starts after episode 1 use alone, with `SeriesRecord.matches` and the series name clash, so 007's pair rules never refuse a series' fixed hosts. Name-clash wording is chosen by a `clash_message` argument → ≈ 10 / 10 |
| `HostCaster.recast` ([casting.py](../../backend/app/podcasts/services/casting.py)) | 11 | + optional `personality_id`, used instead of the random choice when given → ≈ 12 |
| `_episode_turns` (routes.py) | 16 | + `endings = Depends(get_episode_endings)`, passed to `EpisodeDependencies` → 17 |
| `show_draft` / `_episode_fields` / `summary_row` / `_show_model` ([responses.py](../../backend/app/podcasts/responses.py)) | 12 / 14 / 11 / 8 | + 1 field each → 13 / 15 / 12 / 9 |
| `ShowGenerator.generate`, `_parse_reply`, `_show_reply` ([generator.py](../../backend/app/podcasts/services/generator.py)) | 8 / 9 / 13 | `_show_reply` becomes the public `parse_show`, shared with discovery; no length change |
| `HostCard` ([HostCard.tsx](../../frontend/src/components/podcasts/HostCard.tsx)) | 15 | `<select>` → `<ThemedSelect>` → ≈ 15 |
| `ShowCard` (ShowCard.tsx) | 14 | The card becomes a group: the choose button plus `FavouriteToggle`, with series text in the description → ≈ 18 |
| `ShowList`, `Podcasts`, `PodcastSetup`, `SetupForm`, `useSetupShow` | 9 / 15 / 14 / 18 / 16 | `Podcasts` + `<MyShows>`, `<FindNewShow>`. `SetupForm` gains `kind` and moves its Start button into `StartActions` to stay ≤ 20. `useSetupShow` gains `?saved=`, with lookup moved to `findShow(catalog, params)` |
| `SelectField`, `ConversationLevelControl`, `LlmProviderFields` | all ≤ 20 | `<select>` → `<ThemedSelect>`, with the props unchanged |
| `WordFilterBar` ([WordFilterBar.tsx](../../frontend/src/components/flashcards/WordFilterBar.tsx)) | **197**, with inner arrow functions of 40 and 27 | First a behaviour-preserving split into colocated components (`ClassificationPills`, `WordSortSelect`, `DatePresetChips`) with module-level style constants, each function ≤ 20; then `<select>` → `<ThemedSelect>` inside `WordSortSelect` |

### Post-Phase-1 re-evaluation: **PASS**

The design added nothing that weakens a row above:
- the contracts confirm that no provider, engine, TTS, level, summary or `conversation_turns`
  module changes. Every API change is additive, and `PodcastStorage` gains no abstract method;
- the data model confirms five additive tables, every one cascading from `conversations` or a new
  parent, with no existing column or row touched;
- the quickstart gives every Principle IV claim and every success criterion a concrete check;
- research R6 keeps the model out of `POST /episodes`, which is what SC-006 needs. When memory is
  behind, the wait is a visible, bounded step on the setup screen (Principle IV), not a silent
  delay. R11 makes
  SC-008 automatable rather than manual-only.

---

## Project Structure

### Documentation (this feature)

```text
specs/010-recurring-podcast-shows/
├── spec.md                    # input
├── plan.md                    # this file
├── research.md                # Phase 0: R1–R13
├── data-model.md              # Phase 1
├── quickstart.md              # Phase 1
├── contracts/
│   └── api.md                 # Phase 1
├── checklists/
│   └── requirements.md        # from /speckit-specify
├── series-review-sheet.md     # created during validation (SC-002, SC-003, SC-004)
└── tasks.md                   # Phase 2 (/speckit-tasks; NOT created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── podcasts/
│   │   ├── catalog.py                      # + "suggested" source, memory caps, discovery seeds
│   │   ├── models.py                       # + podcast_shows, podcast_series, podcast_series_hosts,
│   │   │                                   #   podcast_series_episodes, podcast_series_memories
│   │   ├── schemas.py                      # + ShowListing, Series*, Recast/Favourite/Discover requests,
│   │   │                                   #   kind, saved_show_id, series, episode_number
│   │   ├── prompts.py                      # + series section and cue variants, memory and
│   │   │                                   #   discovery prompts + schemas
│   │   ├── responses.py                    # + listings and series fields
│   │   ├── routes.py                       # catalogue listings; start delegates to SeriesService
│   │   ├── series_routes.py                # NEW: favourites, remove a kept show, series detail,
│   │   │                                   #   recast, reset, memory
│   │   ├── discovery_routes.py             # NEW: Find a new show
│   │   └── services/
│   │       ├── library.py                  # NEW: ShowLibrary, ShowRef
│   │       ├── series.py                   # NEW: SeriesService (prepare start, recast, reset)
│   │       ├── series_snapshot.py          # NEW: SeriesSnapshot, SeriesBrief (imported by prompts.py)
│   │       ├── series_memory.py            # NEW: SeriesMemoryKeeper, MemoryCatchUps, parser
│   │       ├── discovery.py                # NEW: ShowDiscovery, SuggestionSeeds
│   │       ├── episode_endings.py          # NEW: EpisodeEndings ABC
│   │       ├── series_storage.py           # NEW: ShowLibraryStorage + SeriesStorage ABCs, records
│   │       ├── sqlite_series_storage.py    # NEW
│   │       ├── storage.py, sqlite_storage.py   # NewEpisode.series, EpisodeRecord.series, link row
│   │       ├── episodes.py                 # LoadedEpisode.series_brief
│   │       ├── cues.py                     # brief passed to render_cue
│   │       ├── episode_turns.py            # EpisodeDependencies.endings; _after reports finish
│   │       ├── casting.py                  # HostCaster.recast takes an optional personality_id
│   │       └── generator.py                # parse_show shared with discovery
│   └── services/factory.py                 # + library, series storage, keeper, catch-ups, endings
│   # NOT modified: prompts/templates.py, conversation_levels/*, conversation_summary/*,
│   #   conversation_turns/*, services/llm/*, services/conversation/*, services/tts/*,
│   #   practice_languages/*, language_data/*, language_kit/*, database.py, main.py
└── tests/
    ├── unit/podcasts/                      # library, series (prepare/recast/reset), snapshot,
    │                                       #   series prompt + budget, one-off golden, memory parser +
    │                                       #   grounding + caps (property), discovery seeds + filters,
    │                                       #   catch-up guard
    ├── unit/test_module_boundaries.py      # extended composition-root list
    ├── contract/                           # catalogue listings, favourites, discover, series detail,
    │                                       #   recast, reset, memory; storage ABCs
    ├── integration/podcasts/               # series lifecycle across episodes and languages, one-off
    │                                       #   isolation, resume with a stale snapshot, sign-off →
    │                                       #   catch-up, upgrade from schema_007 (SC-009, FR-022),
    │                                       #   *_benchmark.py (hand-run, quickstart §3)
    ├── support/scripted_memory_llm.py      # NEW: scripted memory and discovery replies (as scripted_show_llm.py)
    └── fixtures/schema_007.sql             # NEW: frozen pre-010 schema

frontend/
├── .eslintrc.json                          # function-length override + the shared files and the four
│                                           #   non-podcast components moved to ThemedSelect
├── src/
│   ├── index.css                           # the `option` rule removed once no native option remains
│   ├── services/podcastsApi.ts             # + listings, series, favourites, remove, discover, recast, reset
│   ├── hooks/podcasts/                     # NEW: useFavourite, useSeries, useShowDiscovery, useRecast,
│   │                                       #   catchUpState.ts (pure reducer);
│   │                                       #   usePodcastCatalog, useSetupShow, useStartEpisode extended
│   ├── components/shared/                  # NEW: ThemedSelect, useListboxNavigation, ConfirmDialog
│   ├── components/podcasts/                # NEW: FavouriteToggle, MyShows, FindNewShow, SeriesHosts,
│   │                                       #   SeriesHostCard, RecastDialog, RememberedPoints,
│   │                                       #   EpisodeKindFieldset, ContinueEpisode, StartActions;
│   │                                       #   ShowCard, ShowList, HostCard, SetupForm, EpisodeHeader changed
│   ├── components/settings/SelectField.tsx, LlmProviderFields.tsx   # → ThemedSelect
│   ├── components/chat/ConversationLevelControl.tsx                 # → ThemedSelect
│   ├── components/flashcards/WordFilterBar.tsx                      # split, then → ThemedSelect
│   │                                       #   (+ ClassificationPills, WordSortSelect, DatePresetChips)
│   └── pages/Podcasts.tsx, PodcastSetup.tsx                         # My shows, discovery, series setup
└── e2e/
    ├── podcast-series.spec.ts, podcast-favourites.spec.ts,
    │   podcast-discovery.spec.ts, themed-select.spec.ts             # NEW
    ├── fixtures.ts                         # + listing/series/suggestion fixtures, chooseOption, contrastRatio
    └── settings, conversation-level, practice-language, flashcards, podcasts specs  # → chooseOption()
```

**Structure Decision**: keep the existing web-application layout, and keep all series code
**inside `app/podcasts/`**:
- a series is made of podcast concepts (shows, hosts, casting, episodes, prompts), and a separate
  domain module would have to import the podcast internals that the boundary test forbids;
- the new routes are split into `series_routes.py` and `discovery_routes.py`, included by
  `routes.py`, as 007 split `show_routes.py` and `host_routes.py`, so `routes.py` does not grow;
- frontend: `ThemedSelect` and `ConfirmDialog` go in `components/shared/` because Settings,
  Chat and Flashcards use them too. Podcast-only components and hooks stay in their podcast
  folders;
- colocated `*.test.tsx` files follow the existing convention and are left out of the tree.

### Suggested phase order (for `/speckit-tasks`)

1. **Foundation**, which blocks every story:
   - the frozen `schema_007.sql` upgrade test and the one-off **golden prompt** test, written
     first;
   - the catalogue constants;
   - the five models;
   - the `ShowLibraryStorage` / `SeriesStorage` / `EpisodeEndings` ABCs, with fakes, then the
     SQLite storage;
   - `NewEpisode.series` and the link row in `create_episode`'s transaction;
   - `SeriesSnapshot` and `SeriesBrief`;
   - the factory wiring and the extended boundary test.
2. **US1 + US3 (P1): series with consistent hosts, the MVP**:
   - backend:
     - `ShowLibrary.keep`;
     - `SeriesService.prepare`: create on episode 1, check hosts after, take the snapshot;
     - `kind` on `POST /episodes`;
     - the series prompt section and cue variants;
     - `LoadedEpisode.series_brief`;
     - the catalogue's `series` summaries and series hosts;
     - `GET /series/{id}`, recast and reset;
     - the memory keeper (parser, grounding, caps, catch-ups) with `EpisodeEndings` and
       `POST /series/{id}/memory`, including `?wait=true` and `memory_status`;
     - `episode_number` in Past Chats and the episode header;
   - frontend:
     - the series badge on cards;
     - series setup: Start/Continue, the catching-up wait and its Try again / Start without it,
       read-only hosts, Recast with `ConfirmDialog`, remembered points, Start over, the
       name-clash hint;
     - `podcast-series.spec.ts`.

   **Run `test_series_recall_benchmark.py` and `test_series_latency_benchmark.py` here**, before
   more is built on recall quality.
3. **US2 (P1): one-off beside the series**:
   - the `EpisodeKindFieldset` on setup, with series as the default;
   - one-off keeps Shuffle and the personality choice;
   - the integration test that a one-off writes no series rows;
   - E2E;
   - `test_one_off_isolation_benchmark.py`.
4. **US6 (P2): themed drop-downs**. Independent, and can run in parallel with 2–3:
   - `ThemedSelect` with unit tests;
   - the five replacements;
   - `chooseOption()` in the existing specs;
   - `themed-select.spec.ts`;
   - removing the `option` CSS rule.
5. **US4 (P2): favourites and My shows**:
   - `PUT /favourites`;
   - `DELETE /shows/{saved_show_id}` and the confirmed **Remove** on kept learner-made shows (FR-024);
   - `my_shows` in the catalogue;
   - `?saved=` setup;
   - `FavouriteToggle`, `MyShows`;
   - `podcast-favourites.spec.ts`.
6. **US5 (P2): Find a new show**:
   - `ShowDiscovery` (seeds, one call, filter, top-up), sharing the generator's parser;
   - `POST /shows/discover`;
   - `FindNewShow` with "Show me others";
   - favourite and start a suggestion;
   - `podcast-discovery.spec.ts`;
   - `test_discovery_benchmark.py`.
7. **Polish**:
   - the review sheet;
   - the experimental label if SC-002 or SC-003 is missed;
   - `docs/architecture.md` (series, memory, ThemedSelect), and the CLAUDE.md domain-module
     note;
   - the quickstart §6 manual accessibility check.

---

## Complexity Tracking

> No Constitution Check violations: nothing to justify.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | n/a | n/a |
