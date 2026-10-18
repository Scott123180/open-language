---

description: "Task list for 010 — Recurring Podcast Shows"
---

# Tasks: Recurring Podcast Shows

**Input**: Design documents from `/specs/010-recurring-podcast-shows/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: Test tasks are MANDATORY under the TDD constitution (Principle III). Write each test task
first, and watch it FAIL before the implementation task that follows it. Each test sits at the
level that the guarantee tables in [contracts/api.md](contracts/api.md) name: unit, contract,
integration, Vitest or Playwright. One pin is an exception to "watch it fail", because it records
today's behaviour on purpose: the one-off golden prompt test (T006). It must pass **before** any
010 code exists, and must keep passing unedited.

The frozen-schema upgrade test (T005) is an ordinary red test: it fails until T019 adds the five
tables, and must then keep passing unedited, except for T043's API-level additions.

**Organization**: Tasks are grouped by user story, in the order of plan.md § "Suggested phase
order":
- **Foundational**: catalogue constants, the five tables, the storage ABCs and their SQLite
  classes, the series link in `create_episode`, snapshot values, `ThemedSelect` (shared by US3 and
  US6), factory wiring and fixtures.
- **US1** (P1): series continuity, with memory and the catching-up wait. Together with US3, this
  is the MVP.
- **US3** (P1): consistent hosts, covering Recast, Start over, the name clash and stable defaults.
- **US2** (P1): one-off episodes beside the series.
- **US6** (P2): themed drop-downs. Independent of US1–US3, so it can run in parallel with them.
- **US4** (P2): favourites and My shows.
- **US5** (P2): Find a new show.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US6 (the spec.md user stories); absent in Setup, Foundational and Polish
- Paths are relative to the repository root (`backend/app`, `backend/tests`, `frontend/src`,
  `frontend/e2e`)

## Standing rules for every task

- **Python** runs through the venv only: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff` and
  `backend/.venv/bin/black`, run from `backend/`.
- **Function length**: every new or modified function is ≤ 20 lines (Constitution I). There are no
  Complexity Tracking exceptions. The existing functions this feature touches, and their target
  lengths, are listed in plan.md § "Function-length plan"; follow the extraction named there.
  `backend/tests/unit/test_function_length.py` and the ESLint override enforce the limit.
- **Imports** (Principle V):
  - `app.podcasts`' package root does not change (`router`, `PODCAST_SCENARIO_ID`,
    `PodcastMessageVoices`, `PodcastSpeakerNames`);
  - all new backend code lives inside `backend/app/podcasts/`;
  - `backend/app/services/factory.py`, the composition root, is the only outside module that may
    import `app.podcasts.services.series_storage`, `sqlite_series_storage`, `series_memory` and
    `episode_endings`;
  - `episode_turns.py` depends on the `EpisodeEndings` ABC, never on `series_memory`;
  - `conversation_summary` is neither imported nor touched.
- **Files not modified** (plan.md § Project Structure):
  - `backend/app/prompts/templates.py`;
  - anything under `backend/app/conversation_levels/`, `conversation_summary/`,
    `conversation_turns/`, `services/llm/`, `services/conversation/`, `services/tts/`,
    `practice_languages/`, `language_data/` or `backend/language_kit/`;
  - `backend/app/database.py`, `backend/app/main.py`;
  - `SHOW_TEMPLATES` in `backend/app/podcasts/catalog.py` (FR-015).
- **Additive only**: five new tables via `create_all()`. No `_ADDITIVE_COLUMNS` entry; no existing
  column is altered and no existing row is updated (FR-022, SC-009).
- **No per-language data**: no language-kit `Requirement`, and no `kit.sh backfill` run (R13).
  The language-literal guard `backend/tests/unit/test_no_language_literals.py` covers the new
  modules automatically.
- **One-off is untouched**: with `series=None`, `build_standing_prompt` and `render_cue` return
  007's text byte for byte (FR-007). T006 pins it.
- **No magic values**: every cap, budget and quota is a named constant in `catalog.py`
  (data-model §1).
- **Provider independence**: the memory keeper and discovery use the selected provider through the
  factory. A discovery failure surfaces as a 503 with the provider's message. A memory failure is
  logged and retried at the next trigger. Neither ever falls back to another provider.
- **Frontend styling** uses design-system tokens only (`docs/design-system.md`):
  - no hex colours;
  - `--radius-lg` for cards, `--shadow-*` for shadows;
  - `var(--color-text-on-primary)` on primary backgrounds;
  - `--color-text-muted` for back links.
- **Frontend completion**: a frontend task is complete only when `cd frontend && npm run test:e2e`
  passes.
- **Benchmarks** are marked `@pytest.mark.benchmark`. The existing addopts deselect them; they are
  never skipped.

---

## Phase 1: Setup

**Purpose**: a green baseline, a database backup, the frozen pre-010 schema, and the lint override.

- [X] T001 Record the green baseline before any change:
  - from `backend/`: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff check .` and `backend/.venv/bin/black --check .`;
  - from `frontend/`: `npm run lint`, `npm run build`, `npm test` and `npm run test:e2e`.

  All must pass. Note any pre-existing failure in the PR description instead of fixing it here.
- [X] T002 Back up the local database: `cp ~/.open-language/app.db ~/.open-language/app.db.pre-010`. It must hold at least one 007 episode. Quickstart §5 (SC-009) compares against this copy, so take it before the app runs any 010 code.
- [X] T003 Freeze the pre-010 schema as `backend/tests/fixtures/schema_007.sql`, following the pattern of `schema_006.sql`:
  - `git worktree add "$SCRATCH/wt-pre010" 27cf076`. This is the last commit before the 010 docs; `master` is still at 006, so do not use it;
  - in that worktree, run `init_db()` against an empty database with `OPEN_LANGUAGE_DB_PATH` set to a scratch file, using this repository's `backend/.venv/bin/python`;
  - `sqlite3 <file> .schema > backend/tests/fixtures/schema_007.sql`, then `git worktree remove "$SCRATCH/wt-pre010"`;
  - check the dump: `podcast_episodes`, `podcast_hosts`, `podcast_host_lines` and `podcast_preferences` are present, and no `podcast_shows` or `podcast_series*` table exists;
  - add a header comment naming the source commit and "Do not edit", as in `schema_006.sql`.
- [X] T004 [P] Extend the `max-lines-per-function: 20` override's `files` list in `frontend/.eslintrc.json` (Constitution I):
  - the new shared files: `src/components/shared/ThemedSelect.tsx`, `src/components/shared/useListboxNavigation.ts` and `src/components/shared/ConfirmDialog.tsx`;
  - the non-podcast components this feature modifies that are already within the limit: `src/components/settings/SelectField.tsx`, `src/components/settings/LlmProviderFields.tsx` and `src/components/chat/ConversationLevelControl.tsx`. `npm run lint` must stay green;
  - **not** `src/components/flashcards/WordFilterBar.tsx` yet: it is 197 lines today, and T102 adds it once it is split;
  - `src/components/podcasts/**` and `src/hooks/podcasts/**` are already covered.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**:
- the catalogue constants;
- the five tables (data-model §2);
- the `ShowLibraryStorage`, `SeriesStorage` and `EpisodeEndings` ABCs and their SQLite classes;
- `NewEpisode.series` and the link row inside `create_episode`'s transaction;
- the `SeriesSnapshot` and `SeriesBrief` values;
- the catalogue's `ShowListing` shape (`my_shows: []`, `series: null` for now);
- the factory wiring and the extended boundary test;
- `ThemedSelect`, which both US3 (Recast dialog) and US6 (every drop-down) use;
- the test doubles and the frontend types and fixtures.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for the foundation (write first)

- [X] T005 [P] Write the SC-009/FR-022 upgrade test `backend/tests/integration/podcasts/test_series_upgrade_preserves_data.py`, modelled on `backend/tests/integration/podcasts/test_upgrade_preserves_data.py`:
  - build the pre-010 file in `tmp_path` by `executescript` of `backend/tests/fixtures/schema_007.sql` (T003). Never use `create_all()`: the shared metadata will hold the 010 tables;
  - seed:
    - two podcast episodes (one `es`, one `de`), each with `conversations`, `podcast_episodes`, `podcast_hosts` and `podcast_host_lines` rows and their `messages`;
    - one roleplay conversation;
    - two vocabulary items;
    - the `app_settings` row and the `podcast_preferences` row;
  - snapshot every seeded row;
  - run `init_db()` **twice**, rebuilding the engine as `backend/tests/integration/conftest.py` does;
  - assert:
    - every snapshotted row is identical;
    - the five new tables exist;
    - `podcast_series_episodes` is empty.

  This test fails until T019 adds the models, because the five tables don't exist yet. From then on it pins the upgrade, and it must not be edited, except by T043's API-level additions.
- [X] T006 [P] Write the one-off golden test `backend/tests/unit/podcasts/test_one_off_golden.py` (FR-007, contracts §9). Write it **before** any change to `prompts.py`:
  - generate `backend/tests/unit/podcasts/golden/one_off_prompts.json` from the current code with a small script kept in the test module (`python -m tests.unit.podcasts.test_one_off_golden --write`). It holds:
    - `build_standing_prompt(...)` for every format (`one_host`, `panel`, `listen`), each with a learner name and with `learner_name=None`, at Natural and at Beginner;
    - `render_cue(...)` for every cue intent (`open`, `greet`, `discuss`, `reply`, `wrap_up`, `sign_off`), plus the settle and after-pass variants;
  - the test asserts that each call **without** a `series` argument equals the stored text. It passes on today's code;
  - the explicit `series=None` case belongs to T033, so that every checkpoint stays green.
- [X] T007 [P] Extend `backend/tests/unit/podcasts/test_catalog.py` (data-model §1):
  - `"suggested" in SHOW_SOURCES`;
  - `EPISODE_KINDS == ("one_off", "series")`;
  - `MAX_REMEMBERED_TOPICS == 10`, `MAX_REMEMBERED_ABOUT_LEARNER == 8`, `MAX_POINTS_PER_EPISODE == 3`, `REMEMBERED_POINT_MAX_LENGTH == 160`, `REMEMBERED_TEXT_BUDGET == 1200`, `SERIES_SECTION_MAX_LENGTH == 1800`, `MIN_LINES_TO_REMEMBER == 2`, `MEMORY_CHUNK_CHARACTERS == 6000`, `MEMORY_WAIT_SECONDS == 30`, `SUGGESTION_SEEDS == 5`, `MIN_SUGGESTIONS == 3`, `INTEREST_SEEDS == 3`;
  - FR-015: `list(SHOW_TEMPLATES)` equals a literal list of today's eight template ids, in today's order, copied from the current catalogue.
- [X] T008 [P] Extend `backend/tests/unit/test_database.py`: after `init_db()` the five tables exist with exactly the columns, types, nullability and constraints of data-model §2.1–§2.5:
  - `podcast_shows.template_id` is UNIQUE;
  - UNIQUE (`show_id`, `target_language`) on `podcast_series`;
  - UNIQUE (`series_id`, `slot`) on `podcast_series_hosts`;
  - `podcast_series_episodes.conversation_id` is the primary key;
  - `podcast_series_episodes.series_id` and `podcast_series_memories.series_id` are indexed;
  - every foreign key is `ON DELETE CASCADE`;
  - running `init_db()` twice is idempotent.
- [X] T009 [P] Write `backend/tests/contract/service_interfaces/test_series_storage_provider.py` (data-model §4, ISP):
  - `ShowLibraryStorage` is an ABC declaring exactly `keep`, `get`, `set_favourite`, `touch_played`, `list_mine` and `forget`;
  - `SeriesStorage` is an ABC declaring exactly `find`, `get`, `create`, `recast`, `reset`, `remembered`, `pending_episodes` and `remember`;
  - `EpisodeEndings` is an ABC with exactly one abstract method, `episode_finished(conversation_id)`;
  - the SQLite classes implement every method;
  - `PodcastStorage`'s abstract methods equal 007's set (copy the list from `test_podcast_storage_provider.py`), so it gains none.
- [X] T010 [P] Write `backend/tests/unit/podcasts/test_sqlite_show_library.py` against an in-memory database (data-model §2.1, §4, §5.1):
  - `keep` of a ready-made draft creates one row with `template_id` set, `source = "ready_made"` and every content column NULL, and a second `keep` returns the same row;
  - `keep` of a learner-made draft (`generated`, `surprise`, `suggested`) creates a row with `template_id` NULL and title, premise, topic, learner role, both personalities and both angles set; a second `keep` of the same content returns the same row;
  - `get(ShowRef(template_id=…))` and `get(ShowRef(saved_show_id=…))` return a `KeptShow`; a ready-made `KeptShow`'s content is read from `SHOW_TEMPLATES`; an unknown ref returns `None`;
  - `set_favourite(..., True)` sets `favourited_at`;
  - `set_favourite(..., False)` returns `None` and deletes the row in each of these cases:
    - a ready-made show with no series;
    - a learner-made show never played and with no series;
  - `set_favourite(..., False)` keeps the row otherwise;
  - `touch_played` sets `last_played_at`;
  - `list_mine(language)` returns the favourites, the shows with a series in `language`, and the played learner-made shows, ordered by the latest of `last_played_at` and `favourited_at`, newest first (research R9);
  - a show with a series in another language only is not listed, unless it is a favourite or a played learner-made show;
  - `forget(saved_show_id)` deletes a learner-made row and returns `True`; its series in every language cascade away (hosts, links, memories), while the `conversations` and `podcast_episodes` rows stay; an unknown id, or the id of a ready-made row, returns `False` (FR-024).
- [X] T011 [P] Write `backend/tests/unit/podcasts/test_sqlite_series_storage.py` against an in-memory database (data-model §2.2–§2.5, §4):
  - `create(show_row_id, language, hosts)` stores both slots, each with `joined_after_episodes = 0`, and a second `create` for the same (show, language) is rejected;
  - `find` and `get` return a `SeriesRecord` with:
    - `episode_count` = the number of link rows;
    - `unfinished` = the latest linked episode whose conversation is still `active`, or `None`;
  - `recast(series_id, host)` updates that slot's row in place, leaves the other slot unchanged, and records `joined_after_episodes` = the current count;
  - `reset(series_id)` returns `True` and cascades away the hosts, links and memories. The `conversations` and `podcast_episodes` rows stay. An unknown id returns `False`;
  - `remember(series_id, conversation_id, reply, up_to_message_id)`:
    - writes the topic and learner points;
    - replaces the episode's earlier topic, keeping at most one `topic` row per (series, conversation);
    - prunes to `MAX_REMEMBERED_TOPICS` topic rows and `MAX_REMEMBERED_ABOUT_LEARNER` learner rows, keeping the newest by `created_at`;
    - then deletes the oldest row of either kind (ties by `id`) while the series' `conversation_language` texts total more than `REMEMBERED_TEXT_BUDGET`. Assert which rows go for a series at the caps with 160-character points;
    - moves `remembered_up_to_message_id`;
    - does all of this in one transaction: a forced failure leaves neither points nor marker changed;
  - `pending_episodes(series_id)` returns only link rows with at least `MIN_LINES_TO_REMEMBER` messages after the marker;
  - `remembered(series_id)` returns `RememberedPoint`s, each with the `episode_number` of its source episode;
  - deleting a `conversations` row cascades its link row and the memories drawn from it, and `episode_count` follows (spec edge case "episode deleted").
- [X] T012 [P] Extend `backend/tests/unit/podcasts/test_sqlite_storage.py` (data-model §3):
  - `create_episode(NewEpisode(..., series=NewSeriesLink(series_id, episode_number, snapshot)))` writes the link row with the snapshot JSON and a NULL marker;
  - a forced failure while inserting the hosts leaves no conversation, no episode and no link row (one transaction);
  - `create_episode` with `series=None` writes no link row;
  - `get_episode` returns `EpisodeRecord.series` as `EpisodeSeriesFacts(series_id, episode_number, snapshot)` for a linked episode, and `None` for a one-off.
- [X] T013 [P] Write `backend/tests/unit/podcasts/test_series_values.py` (data-model §3):
  - `ShowRef` requires exactly one of `template_id` and `saved_show_id`;
  - `ShowRef.of(draft)` reads `show_id` for a ready-made draft and `saved_show_id` otherwise, and returns `None` for an unsaved learner-made draft;
  - `SeriesHost.to_host()` returns the 007 `Host` with the same slot, name, personality, voice, show role and angle;
  - `is_new_in(n)` is true exactly when `joined_after_episodes == n - 1` and `n > 1`;
  - `has_history(count)` is true exactly when `joined_after_episodes < count`;
  - `SeriesRecord.next_episode_number == episode_count + 1`;
  - `SeriesRecord.matches(draft_hosts)` compares slot, name, personality and voice;
  - `SeriesSnapshot.from_json(s.to_json()) == s` for empty, typical and full snapshots, including non-ASCII text;
  - `SeriesBrief` resolves the names of `new_host_slots` from the episode's cast.
- [X] T014 [P] Write `backend/tests/unit/podcasts/test_series_schemas.py` (data-model §6, contracts §1–§4):
  - `StartEpisodeRequest.kind` defaults to `"one_off"` and rejects any other value with 422;
  - `ShowDraftModel.saved_show_id` defaults to `None`, and `source = "suggested"` is accepted;
  - a `ShowListing` dumped to JSON and posted back as `POST /episodes`'s `show` validates, with the extra fields ignored;
  - `EpisodeSummaryRow.episode_number` defaults to `None`;
  - `DiscoverRequest.avoid_titles` rejects more than 50 entries, and any entry over 200 characters;
  - `RecastRequest.personality_id` is optional.
- [X] T015 [P] Extend `backend/tests/unit/test_module_boundaries.py`:
  - only `backend/app/services/factory.py` may import `app.podcasts.services.series_storage`, `sqlite_series_storage`, `series_memory` and `episode_endings` from outside `app.podcasts`;
  - `app.podcasts.services.episode_turns` never imports `series_memory`;
  - `app.podcasts.__all__` is unchanged;
  - `app.podcasts` never imports `app.conversation_summary`.
- [X] T016 [P] Extend `backend/tests/contract/test_podcasts_catalog_api.py` (contracts §1):
  - every entry of `shows` carries the `ShowListing` fields, with `saved_show_id` null, `is_favourite` false and `series` null on a fresh database;
  - `my_shows == []`;
  - `shows` holds the eight ready-made shows in catalogue order on two consecutive calls (FR-015);
  - every 007 field is unchanged.
- [X] T017 [P] Write `frontend/src/components/shared/ThemedSelect.test.tsx` (research R11, contracts §11), with Vitest and Testing Library. The props mirror a controlled select: `label`, `value`, `options: {value, label}[]`, `onChange`, and optional `id`/`describedBy`/`disabled`. Assert:
  - the trigger has `role="combobox"`, `aria-expanded`, `aria-controls` and the accessible name of its label;
  - the open list has `role="listbox"`, and its items have `role="option"` with `aria-selected` on the current value;
  - Enter, Space and Alt+↓ open the list;
  - ↑/↓/Home/End move `aria-activedescendant`;
  - type-ahead jumps to the next option starting with the typed letters;
  - Enter selects and closes;
  - Escape closes without calling `onChange`;
  - Tab selects the active option and moves focus on;
  - clicking an option selects it, and clicking outside closes;
  - the selected option shows a check mark, and the active option carries the class that draws the focus outline, so both can apply to the same option;
  - `disabled` blocks opening.

### Implementation for the foundation

- [X] T018 Add the data-model §1 constants to `backend/app/podcasts/catalog.py`: `"suggested"` in `SHOW_SOURCES`, `EPISODE_KINDS`, the memory caps and budgets (including `REMEMBERED_TEXT_BUDGET`), `MEMORY_WAIT_SECONDS`, `SUGGESTION_SEEDS`, `MIN_SUGGESTIONS` and `INTEREST_SEEDS`. Leave `SHOW_TEMPLATES` untouched. T007 passes.
- [X] T019 Add the five models to `backend/app/podcasts/models.py`, exactly as specified in data-model §2.1–§2.5:
  - `podcast_shows`:
    - `id`; `template_id` VARCHAR(100) NULL UNIQUE; `source` VARCHAR(12) NOT NULL;
    - `title` VARCHAR(200) NULL; `premise` TEXT NULL; `topic` VARCHAR(200) NULL;
    - `learner_role` VARCHAR(12) NULL;
    - `lead_personality` and `second_personality` VARCHAR(30) NULL; `lead_angle` and `second_angle` TEXT NULL;
    - `favourited_at` DATETIME NULL; `last_played_at` DATETIME NULL; `created_at` DATETIME NOT NULL;
  - `podcast_series`: `id`; `show_id` FK → `podcast_shows.id` ON DELETE CASCADE; `target_language` VARCHAR(10) NOT NULL; `created_at` NOT NULL; UNIQUE (`show_id`, `target_language`);
  - `podcast_series_hosts`:
    - `id`; `series_id` FK ON DELETE CASCADE;
    - `slot` VARCHAR(8) NOT NULL; `name` VARCHAR(40) NOT NULL; `personality` VARCHAR(30) NOT NULL;
    - `voice_key` VARCHAR(200) NOT NULL; `show_role` VARCHAR(20) NOT NULL; `angle` TEXT NULL;
    - `joined_after_episodes` INTEGER NOT NULL DEFAULT 0;
    - UNIQUE (`series_id`, `slot`);
  - `podcast_series_episodes`:
    - `conversation_id` INTEGER PK, FK → `podcast_episodes.conversation_id` ON DELETE CASCADE;
    - `series_id` FK ON DELETE CASCADE, indexed;
    - `episode_number` INTEGER NOT NULL; `snapshot` TEXT NOT NULL;
    - `remembered_up_to_message_id` INTEGER NULL;
  - `podcast_series_memories`:
    - `id`; `series_id` FK ON DELETE CASCADE, indexed;
    - `conversation_id` FK → `conversations.id` ON DELETE CASCADE;
    - `kind` VARCHAR(8) NOT NULL; `conversation_language` TEXT NOT NULL; `english` TEXT NOT NULL;
    - `created_at` DATETIME NOT NULL.

  T008 passes, and T005 must now pass.
- [X] T020 Extend `backend/app/podcasts/schemas.py` (contracts §1–§8, data-model §6):
  - new models: `ShowListing` (a `ShowDraftModel` plus read-only `is_favourite` and `series`), `SeriesSummaryModel`, `UnfinishedEpisodeModel`, `SeriesHostModel`, `RememberedPointModel`, `SeriesDetailResponse`, `RecastRequest`, `FavouriteRequest`, `DiscoverRequest` and `DiscoverResponse`, `MemoryStatusResponse`;
  - `kind: Literal["one_off", "series"] = "one_off"` on `StartEpisodeRequest`;
  - `saved_show_id: int | None = None` on `ShowDraftModel`, and `"suggested"` accepted as its `source`;
  - `series: EpisodeSeriesModel | None` on `EpisodeResponse`;
  - `episode_number: int | None = None` on `EpisodeSummaryRow`;
  - `my_shows: list[ShowListing]` on `CatalogResponse`, with `shows: list[ShowListing]`.

  T014 passes.
- [X] T021 Declare the abstractions:
  - in `backend/app/podcasts/services/library.py`, `ShowRef` (frozen; exactly one of `template_id` and `saved_show_id`; `of(draft)`);
  - in the new `backend/app/podcasts/services/series_storage.py`:
    - the `ShowLibraryStorage` and `SeriesStorage` ABCs with the signatures of data-model §4;
    - the frozen records: `KeptShow`, `SeriesHost` (with `to_host`, `is_new_in`, `has_history`), `SeriesRecord` (with `next_episode_number` and `matches`), `EpisodeRef`, `RememberedPoint`, `PendingEpisode`, `ShelfEntry`, `PointText` and `MemoryReply`;
  - in the new `backend/app/podcasts/services/episode_endings.py`, the `EpisodeEndings` ABC with `episode_finished(conversation_id: int) -> None`, and a `NoEpisodeEndings` null object for tests and one-off wiring.
- [X] T022 Create `backend/app/podcasts/services/series_snapshot.py`:
  - `SeriesSnapshot` (frozen): `episode_number`, `topics_covered`, `about_learner`, `new_host_slots`, with `to_json()` and `from_json()`;
  - `SeriesBrief` (frozen): the snapshot plus `new_host_names` resolved from a `Cast` through `SeriesBrief.of(snapshot, cast)`.

  This module is a deliberate addition to plan.md's module list: `prompts.py` imports these values, and putting them in `series.py` would make the prompts depend on the service. T013 passes.
- [X] T023 Extend `backend/app/podcasts/services/storage.py` and `sqlite_storage.py` (data-model §3):
  - in `storage.py`: `NewSeriesLink(series_id, episode_number, snapshot)`; `NewEpisode.series: NewSeriesLink | None = None`; `EpisodeSeriesFacts`; `EpisodeRecord.series`;
  - in `SQLitePodcastStorage.create_episode`, add one line, `self._add_series_link(...)`, in the same transaction (→ 14 lines);
  - in `get_episode` and `_episode_record`, add a left join on `podcast_series_episodes`, and fill `series` from `_series_facts(link)` (→ 9 and 18 lines).

  T012 passes.
- [X] T024 Implement `SQLiteShowLibraryStorage` in the new `backend/app/podcasts/services/sqlite_series_storage.py`:
  - keep by template id, or by learner-made content;
  - read ready-made content from `SHOW_TEMPLATES`;
  - enforce the row-lifetime invariants of data-model §2.1 inside `set_favourite`;
  - implement `list_mine` with research R9's union and order;
  - implement `forget`, deleting learner-made rows only.

  T010 passes.
- [X] T025 Implement `SQLiteSeriesStorage` in `backend/app/podcasts/services/sqlite_series_storage.py`:
  - `find` and `get`, with the count and the unfinished episode;
  - `create`, `recast` and `reset`;
  - `remembered`, `pending_episodes`;
  - `remember`: write, replace the topic, prune to the caps and then to `REMEMBERED_TEXT_BUDGET`, and move the marker, in one transaction.

  T011 passes.
- [X] T026 Wire the storages in `backend/app/services/factory.py`: `get_show_library_storage` and `get_series_storage`, built over the request's `get_db` session, like `get_podcast_storage`. T009 and T015 pass.
- [X] T027 Return listings from the catalogue:
  - add `catalog_listings(drafts, ...)` to `backend/app/podcasts/responses.py`; it maps each draft to a `ShowListing` with `is_favourite=False`, `series=None` and `saved_show_id=None`;
  - make `get_catalog` in `backend/app/podcasts/routes.py` call it and return `my_shows=[]` (≈ 10 lines).

  T016 passes.
- [X] T028 [P] Write `backend/tests/support/scripted_memory_llm.py`, modelled on `scripted_show_llm.py`:
  - a `StructuredLLMProvider` fake that returns queued JSON replies for the memory and discovery schemas, and records every prompt;
  - it can raise a queued `LLMError`;
  - it can block on a `threading.Event`, for the timeout tests.
- [X] T029 [P] Add the frontend types and fixtures:
  - in `frontend/src/services/podcastsApi.ts`: `ShowListing`, `SeriesSummary`, `UnfinishedEpisode`, `SeriesDetail`, `SeriesHostView`, `RememberedPoint`, `MemoryStatus`, `EpisodeKind`, `EpisodeSeries`; `saved_show_id` on `ShowDraft`; `series` on the episode response; `episode_number` on the Past Chats row; `my_shows` on the catalogue;
  - in `frontend/e2e/fixtures.ts`: `showListingFixture`, `seriesSummaryFixture`, `seriesDetailFixture` and `suggestionsFixture`, shaped exactly as contracts §1, §4 and §5;
  - update the existing catalogue mocks in `frontend/e2e/fixtures.ts` and `frontend/src/pages/podcastPageFixtures.test.utils.ts` to return `my_shows: []` and listing-shaped shows.

  `npm test` and `npm run test:e2e` stay green.
- [X] T030 Implement `frontend/src/components/shared/ThemedSelect.tsx` (research R11):
  - follow the WAI-ARIA APG select-only combobox, with every function ≤ 20 lines. Extract the keyboard map and type-ahead into a colocated `useListboxNavigation` hook in `frontend/src/components/shared/useListboxNavigation.ts`;
  - styling uses tokens only:
    - the list sits on `--color-surface` with `--color-text`, `--radius-lg` and `--shadow-md`;
    - the selected option uses `--color-primary-subtle`/`--color-primary-text` plus a check icon from `components/shared/icons.tsx`;
    - the active option has a 2px `--color-primary` outline;
  - touch targets are ≥ 44px.

  T017 passes.
- [X] T031 Foundation checkpoint. Run the full backend suite, `ruff`, `black --check`, `npm run lint`, `npm test` and `npm run test:e2e`. All are green. Nothing user-visible has changed.

**Checkpoint**: Foundation ready. US1 can start, and so can US6 in parallel.

---

## Phase 3: User Story 1 - Continue a show as a series with the same hosts (Priority: P1) 🎯 MVP

**Goal**: choosing a show offers **Start episode N** (or **Continue episode N** when one is
unfinished). The series' hosts return unchanged, open by welcoming the learner back, and bring up a
remembered point on a new topic. Memory is written in the background after a sign-off and when the
setup opens. Start waits for it with a "catching up" message, and offers Try again or Start without
it on failure.

**Independent Test**: finish one episode of a ready-made show, then start that show again. The setup
offers Episode 2 with unchanged hosts, and the opening lines address the learner and refer to a
specific point from episode 1, on a new topic (spec US1).

Until US2 lands, every start from the setup screen is a series episode. The API's default `kind`
is still `one_off`.

### Tests for User Story 1 (write first, see them fail)

- [X] T032 [P] [US1] Write `backend/tests/unit/podcasts/test_series_service.py` for `SeriesService.prepare(req, settings) -> PreparedStart`, with fake `ShowLibraryStorage` and `SeriesStorage` (data-model §5.2):
  - `kind=series` with no series for (show, language) creates the series from the draft's two hosts. The result is episode 1, with a snapshot of `episode_number=1`, empty lists and no new hosts;
  - `kind=series` with a series whose hosts match gives episode `count + 1`, with a snapshot built from `remembered()`;
  - the participating hosts come from the series for the format's slots: One host gives the lead only, and Panel or Listen gives both;
  - hosts that differ in any of slot, name, personality or voice raise `SeriesHostsChanged`, and nothing is written;
  - after episode 1, the draft is checked with `show_problem` and the host match only, never 007's pair rules: a series whose two hosts share one voice starts its next episode with two voices now installed, and a series host whose voice is no longer installed still starts (data-model §5.2 step 1);
  - the show is kept: `keep(draft)` then `touch_played` for a ready-made show and for a learner-made show (`generated`, `surprise`, `suggested`). The `PreparedStart` carries the `saved_show_id`;
  - an unknown `saved_show_id` raises `ShowNoLongerKept`;
  - the language is `settings.target_language`, never the draft's;
  - `new_host_slots` holds the slots with `joined_after_episodes == count` when `count ≥ 1`.
- [X] T033 [P] [US1] Write `backend/tests/unit/podcasts/test_series_prompts.py` (contracts §9, research R5, R7):
  - with a `SeriesBrief`, the standing prompt has one extra section before the line rules. The section:
    - opens with "This is episode N of a continuing show." (or "the first episode of a continuing show" when N = 1);
    - lists "Earlier episodes covered: …" and "What {label} has told you before: …";
    - holds the rules: refer back where it fits; choose a subject within the show's topic that is not in the covered list; never claim to remember anything not listed;
  - the section names languages, never codes;
  - the section is ≤ `SERIES_SECTION_MAX_LENGTH` for the worst stored set: 10 topics and 8 learner points whose texts total `REMEMBERED_TEXT_BUDGET`, the longest host names and label, and a new host (with T067's wording once T073 lands). The renderer lists every point, newest first, and drops nothing; assert that every point appears;
  - empty lists render no "covered" or "told you" line;
  - the `open` cue for N > 1 asks the lead to welcome {label} back by name, say the show is continuing, and bring up one remembered point. With N = 1, the `open` cue equals 007's;
  - rendering the same brief twice is byte-identical;
  - called with an explicit `series=None`, both functions equal T006's golden text for every stored case. This fails, with a `TypeError`, until T048 adds the parameter.
- [X] T034 [P] [US1] Write `backend/tests/unit/podcasts/test_series_memory.py` (research R6, contracts §8–§9):
  - parser:
    - a valid reply gives a `MemoryReply` with a topic and ≤ 3 learner points, each with `conversation_language` and `english`, trimmed and cut to `REMEMBERED_POINT_MAX_LENGTH`;
    - `topic: null` and `about_learner: []` are accepted;
    - more than 3 points keep the first 3;
    - unreadable JSON raises `UnreadableMemoryError` (an `LLMError`);
  - grounding: learner points from a chunk with no line labelled Learner are dropped in code, and the topic is kept;
  - chunking: lines are folded into chunks of ≤ `MEMORY_CHUNK_CHARACTERS`, with one structured call per chunk;
  - an episode with fewer than `MIN_LINES_TO_REMEMBER` unread lines makes no call;
  - the prompt:
    - labels hosts by name and the learner as "Learner";
    - lists the points already remembered;
    - states the rules (about the learner only from Learner lines; nothing a host said about themselves; no guesses; an empty list when there is nothing; the subject as one short phrase);
    - names languages, never codes;
    - uses `MEMORY_JSON_SCHEMA`, with `maxItems: 3`.
- [X] T035 [P] [US1] Write `backend/tests/unit/podcasts/test_series_memory_properties.py`: 200 seeded random catch-up sequences against an in-memory `SQLiteSeriesStorage`, with random episodes, chunk counts, point counts and lengths. After every `remember`:
  - topics ≤ 10 and learner points ≤ 8;
  - the points' conversation-language texts total ≤ `REMEMBERED_TEXT_BUDGET`;
  - at most one topic per episode;
  - the newest points are kept;
  - the series section rendered from a snapshot of the result is ≤ 1,800 characters and contains every stored point (FR-006, FR-011).
- [X] T036 [P] [US1] Write `backend/tests/unit/podcasts/test_memory_catch_ups.py`, with an injected synchronous executor and fake keepers:
  - `start(series_id, keeper)` returns `started`, and a second call while running returns `running`; only one catch-up runs;
  - the catch-up runs on the keeper passed to its `start`: two successive starts given different keepers each call their own, and `MemoryCatchUps` keeps no keeper or provider between calls (Principle VI, research R6);
  - `status(series_id)` is `running` while held. Otherwise it is `pending` when `pending_episodes` is non-empty, and `up_to_date` when not;
  - `wait(series_id, keeper, limit)` returns `up_to_date` when the catch-up finishes;
  - `wait` returns `failed` with the provider's message when the keeper raises `LLMError`, and the failure is logged;
  - `wait` returns `timed_out` at the limit while the catch-up keeps running;
  - `KeeperEndings.episode_finished(conversation_id)` starts a catch-up, with the keeper it was built with, for a series episode's series, and does nothing for a one-off.
- [X] T037 [P] [US1] Write `backend/tests/unit/podcasts/test_library.py` for `ShowLibrary`, with a fake `ShowLibraryStorage`:
  - `keep(draft)` returns the kept show for ready-made and learner-made drafts;
  - `played(kept)` touches `last_played_at`;
  - `resolve(draft)` raises `ShowNoLongerKept` for an unknown `saved_show_id`.
- [X] T038 [P] [US1] Write `backend/tests/contract/test_podcast_series_api.py` (contracts §5, §8):
  - `GET /api/podcasts/series/{id}` returns 200 with exactly the §5 shape: `remembered.topics` and `about_learner` items carry `point_id`, the English `text` and `episode_number`; `memory_status` is `up_to_date`, `pending` or `running`;
  - an unknown id returns 404 "That series isn't there any more. Open the show again.";
  - `POST /series/{id}/memory` returns 202 with `started`, `running` or `up_to_date`;
  - `?wait=true` returns 200 with `up_to_date`, `failed` and its `detail`, or `timed_out` with "It's taking longer than usual.". Use a short wait limit injected through the `get_memory_wait_seconds` dependency;
  - an unknown series returns 404.
- [X] T039 [P] [US1] Write `backend/tests/contract/test_podcast_series_episodes_api.py` (contracts §1–§2):
  - `POST /episodes` with `kind=series` and no series: 201, `series == {"series_id": …, "episode_number": 1}`;
  - the second start with matching hosts: 201, `episode_number == 2`;
  - differing hosts: 409 "This show's hosts changed. Open the show again.";
  - an unknown `saved_show_id`: 404 "That show isn't kept any more. Pick another one.";
  - `show.saved_show_id` is set for a learner-made show;
  - `GET /episodes/{id}` returns the same `series`;
  - `GET /episodes` rows carry `episode_number`, which is null for a one-off;
  - after one series episode, `GET /catalog` lists that show with the series' hosts and `series == {series_id, episode_count: 1, next_episode_number: 2, unfinished_episode: …}`. `unfinished_episode` is set while the episode is active and null once it has finished.
- [X] T040 [P] [US1] Write `backend/tests/integration/podcasts/test_series_lifecycle.py` over the podcast harness and the scripted line writer:
  - SC-001: across 10 scripted series episodes, mixing One host, Panel and Listen, each episode's `podcast_hosts` rows equal the series' hosts for the format's slots, and the second host keeps its place through One-host episodes;
  - episode numbers 1…10;
  - US1-4: the same show in `de` starts its own series at episode 1 with German-bank names, and the `es` series and hosts are unchanged;
  - US1-5: an unfinished episode is reported as `unfinished_episode`; starting a new one while it is unfinished counts both, and the first stays resumable;
  - an abandoned episode with two lines counts as an episode;
  - switching the provider setting between episodes keeps the hosts, numbers and memory;
  - deleting a series episode's `conversations` row lowers the count and removes the memories drawn from it;
  - a series host whose voice is no longer installed keeps their name, personality and `voice_key`; the next episode still starts, and its lines are stored as text with 007's missing-voice notice (spec edge case);
  - a series cast while only one voice was installed (both hosts share it) still starts its next episode after a second voice is installed, with the shared voice kept (data-model §5.2 step 1);
  - changing the name the hosts call the learner between episodes: the next episode's standing prompt and `open` cue use the new name (spec edge case).
- [X] T041 [P] [US1] Write `backend/tests/integration/podcasts/test_series_memory_catch_up.py`, with the scripted memory provider (T028) and a synchronous executor:
  - a series sign-off triggers `EpisodeEndings`, which runs a catch-up that writes the topic and learner points and moves the marker;
  - a one-off sign-off triggers nothing;
  - a second catch-up reads only the lines after the marker;
  - a Listen episode adds a topic and no learner points;
  - a provider failure leaves the memory and the marker unchanged and logs the error;
  - switching the provider setting after a sign-off: the next `POST /series/{id}/memory` catch-up calls the newly selected provider's fake, and the previous one receives no call (Principle VI);
  - `POST /series/{id}/memory?wait=true` returns `up_to_date`, and the next series start's snapshot contains the new points;
  - with a provider blocked on an event and a 0.2 s limit, `?wait=true` returns `timed_out` without blocking the event loop. A concurrent `GET /catalog` completes meanwhile.
- [X] T042 [P] [US1] Write `backend/tests/integration/podcasts/test_series_resume.py`: start series episode 2, add lines, and record its standing prompt and cue history. Then let the series gain new memories through a catch-up of episode 1's later lines. On resuming episode 2:
  - the standing prompt and cue history are byte-identical (snapshot stability);
  - the conversation session is not rebuilt, because the fingerprint is unchanged.
- [X] T043 [P] [US1] Extend `backend/tests/integration/podcasts/test_series_upgrade_preserves_data.py` (T005) for FR-022. After the upgrade, through the API:
  - `GET /episodes` lists both pre-010 episodes with `episode_number: null`;
  - `GET /catalog` lists every show with `series: null`;
  - a `kind=series` start of a show that a pre-010 episode used becomes episode 1.
- [X] T044 [P] [US1] Write Vitest tests for the client and hooks:
  - `frontend/src/services/podcastsApi.test.ts`: `getSeries(id)`, `catchUpSeriesMemory(id)` (202) and `catchUpSeriesMemory(id, {wait: true})`; `startEpisode` sends `kind`;
  - `frontend/src/hooks/podcasts/useSeries.test.tsx`: fetches the series detail and fires the catch-up once when the setup opens;
  - `frontend/src/hooks/podcasts/useStartEpisode.test.tsx`:
    - with `memory_status = up_to_date`, it starts at once;
    - otherwise it enters `catchingUp`, calls the wait, then starts;
    - on `failed` or `timed_out`, it exposes the message, `retry()` and `startWithoutUpdate()`.
- [X] T045 [P] [US1] Write the component tests:
  - `frontend/src/components/podcasts/ShowCard.test.tsx` (extended): the choose button's description includes "Episode 2 next", or "Episode 1 unfinished" when unfinished, and has no series text without a series;
  - `SeriesHostCard.test.tsx`: name, personality label and a ▶ sample button; no Shuffle and no personality control; when the host's voice is not installed, the sample button is disabled and 007's plain missing-voice message is shown, with the name and personality unchanged;
  - `ContinueEpisode.test.tsx`: **Continue episode N** primary, with "Start a new episode instead" as a secondary text button;
  - `StartActions.test.tsx`:
    - **Start episode N**;
    - while catching up, the button is `aria-busy` and a `role="status"` message reads "Hugo and Inés are catching up on episode 3. This takes a few seconds.";
    - on failure, "The hosts couldn't catch up on episode 3. {detail}" with **Try again** (primary) and **Start without it**;
  - `EpisodeHeader.test.tsx`: "Big Little Questions · Episode 2".
- [X] T046 [P] [US1] Extend `frontend/src/pages/PodcastSetup.test.tsx`:
  - a show with a series renders `SeriesHosts`, with **Start episode 2** as the single primary action;
  - with an unfinished episode, **Continue episode 1** navigates to that episode;
  - starting while memory is pending shows the catching-up status, then navigates to the new episode.
- [X] T047 [P] [US1] Write `frontend/e2e/podcast-series.spec.ts` (US1 part), with every call mocked through `page.route()`:
  - the card shows "Episode 2 next", and choosing it opens setup with **Start episode 2** and read-only hosts;
  - Start sends `kind: "series"` and the listing's hosts, and the episode header reads "· Episode 2";
  - with `unfinished_episode` set, **Continue episode 1** is first;
  - with `memory_status: "pending"`, Start shows the catching-up message, then the episode opens on its own once the mocked wait returns `up_to_date`;
  - with the wait returning `failed`, the failure message, **Try again** and **Start without it** appear, and Start without it starts the episode.

### Implementation for User Story 1

- [X] T048 [US1] Add the series section and cue variants to `backend/app/podcasts/prompts.py`:
  - `build_standing_prompt(show, cast, label, languages, level, series: SeriesBrief | None = None)`: the sections tuple gains `_series_section(series, cast, label)`, filtered out when it is None (→ 14 lines);
  - `_series_section` renders every point of the snapshot, newest first. It never drops points: the stored set fits by construction (`REMEMBERED_TEXT_BUDGET`, T025);
  - `render_cue(cue, cast, label, series=None)`: the instruction lookup moves to `_instruction(cue, cast, label, series)` (≈ 10 lines), and adds the series `open` variant for N > 1.

  T033 (including its `series=None` case) and T006 pass. **Leave the new-host wording to T073.**
- [X] T049 [US1] Add `MEMORY_JSON_SCHEMA` and `memory_prompt(chunk, names, remembered, languages)` to `backend/app/podcasts/prompts.py` (contracts §9).
- [X] T050 [US1] Pass the brief through the episode pipeline:
  - `LoadedEpisode.series_brief` in `backend/app/podcasts/services/episodes.py`: `SeriesBrief.of(record.series.snapshot, cast)`, or `None`; `standing_prompt` passes it (5 lines);
  - `episode_history`, `next_turn_history` and `_cue_turn` in `backend/app/podcasts/services/cues.py` take and forward `series`;
  - `EpisodeTurns.warm` and `_request` in `backend/app/podcasts/services/episode_turns.py` pass `episode.series_brief`.
- [X] T051 [US1] Report finished episodes:
  - add `endings: EpisodeEndings` to `EpisodeDependencies` in `backend/app/podcasts/services/episode_turns.py`;
  - `_after` calls `self._deps.endings.episode_finished(conversation_id)` once the `sign_off` line is stored (+1 line → 8);
  - add `get_episode_endings` to `backend/app/services/factory.py`, returning `NoEpisodeEndings()` for now; T056 replaces it with `KeeperEndings`;
  - `_episode_turns` in `backend/app/podcasts/routes.py` takes the endings from `get_episode_endings` (16 → 17 lines).
- [X] T052 [US1] Implement `ShowLibrary` in `backend/app/podcasts/services/library.py`: `keep(draft)`, `played(kept)` and `resolve(draft)`, raising `ShowNoLongerKept`. T037 passes.
- [X] T053 [US1] Implement `SeriesService` in the new `backend/app/podcasts/services/series.py`:
  - extract the show-level checks of `validate_draft` (language, learner role, slots) into `show_problem(draft, language)` in `backend/app/podcasts/schemas.py`, and have `validate_draft` call it (14 → ≈ 10 lines, 007 behaviour unchanged);
  - `prepare(req, settings) -> PreparedStart`: validate (`validate_draft` for the series' first episode, `show_problem` after it), keep the show, find or create the series, check the hosts (`SeriesHostsChanged`), take the snapshot, and build the participating hosts from the series for the format's slots;
  - move `_new_episode` from `routes.py` into it, taking a `PreparedStart` (≈ 18 lines);
  - `start_episode` in `backend/app/podcasts/routes.py` delegates for `kind=series` (≈ 14 lines), and maps `SeriesHostsChanged` → 409 and `ShowNoLongerKept` → 404 with the data-model §6 messages.

  For `kind=one_off`, 007's path runs unchanged; US2 adds keeping the show for one-offs. T032 passes.
- [X] T054 [US1] Implement the parser and `SeriesMemoryKeeper` in the new `backend/app/podcasts/services/series_memory.py`:
  - `parse_memory_reply(raw) -> MemoryReply`;
  - `SeriesMemoryKeeper(structured_provider, session_factory, languages)`, whose `catch_up(series_id)` does the following:
    - for each pending episode, build the labelled chunks of `MEMORY_CHUNK_CHARACTERS` from the lines after the marker;
    - make one `chat_json` call per chunk;
    - apply the grounding rule;
    - call `SeriesStorage.remember(...)`;
    - log and re-raise on `LLMError`, leaving the marker unchanged.

  T034 and T035 pass.
- [X] T055 [US1] Implement `MemoryCatchUps` and `KeeperEndings` in `backend/app/podcasts/services/series_memory.py`:
  - `MemoryCatchUps`, with an injected executor and a per-series guard plus a completion `threading.Event`, provides `start(series_id, keeper)`, `status(series_id)` and `wait(series_id, keeper, limit)`, which waits in the executor so the event loop is never blocked. It stores no keeper or provider: each catch-up runs on the keeper it was started with;
  - `KeeperEndings(EpisodeEndings)`, built per request with the catch-ups, the series storage and that request's keeper, looks up the link row and starts a catch-up for series episodes only.

  T036 passes.
- [X] T056 [US1] Wire the memory pieces in `backend/app/services/factory.py`:
  - `get_series_memory_keeper`: per request, over `get_structured_llm` (the provider selected at that moment), plus its own `SessionLocal` session factory;
  - `get_memory_catch_ups`: one process-wide instance over a `ThreadPoolExecutor(max_workers=1)`, holding no keeper or provider;
  - `get_episode_endings`: replace T051's `NoEpisodeEndings()` with a `KeeperEndings` over the catch-ups, the series storage and the request's keeper.
- [X] T057 [US1] Add the series fields to the responses:
  - in `backend/app/podcasts/responses.py`:
    - `catalog_listings` lists a show that has a series in the current language with the series' hosts and its `SeriesSummaryModel`;
    - `_episode_fields` adds `series` and `show.saved_show_id` (+1 field → 15);
    - `summary_row` adds `episode_number` (+1 → 12);
  - `list_episodes` in `backend/app/podcasts/services/sqlite_storage.py` left-joins `podcast_series_episodes` for the number.

  T039 and T043 pass.
- [X] T058 [US1] Create `backend/app/podcasts/series_routes.py` with:
  - `GET /series/{series_id}`: the `SeriesDetailResponse`, including `memory_status` from `MemoryCatchUps.status` and English remembered texts;
  - `POST /series/{series_id}/memory` returning 202, with `?wait=true` returning 200 through `get_memory_wait_seconds` (default `MEMORY_WAIT_SECONDS`). Both pass the request's `get_series_memory_keeper` to `MemoryCatchUps`.

  Include it from `backend/app/podcasts/routes.py`, as `show_routes.py` is included. T038, T040, T041 and T042 pass.
- [X] T059 [P] [US1] Add `getSeries`, `catchUpSeriesMemory(id, options?)` and the `kind` argument of `startEpisode` to `frontend/src/services/podcastsApi.ts`.
- [X] T060 [US1] Implement the hooks:
  - `frontend/src/hooks/podcasts/useSeries.ts` (TanStack Query; fires the catch-up once on mount);
  - extend `frontend/src/hooks/podcasts/useStartEpisode.ts` with the catch-up state machine (`idle → catchingUp → failed | timedOut`, `retry`, `startWithoutUpdate`). Put the transitions in a pure reducer in `frontend/src/hooks/podcasts/catchUpState.ts`, so each function stays ≤ 20 lines.

  T044 passes.
- [X] T061 [P] [US1] Implement the components in `frontend/src/components/podcasts/`:
  - `ShowCard.tsx`: the series text goes in the description;
  - `SeriesHosts.tsx` and `SeriesHostCard.tsx`: read-only, with a voice sample through the existing sample player;
  - `ContinueEpisode.tsx`;
  - `StartActions.tsx`: the Start button, the catching-up `role="status"` message, and Try again / Start without it;
  - `EpisodeHeader.tsx`: "· Episode N" when `series` is set.

  T045 passes.
- [X] T062 [US1] Integrate the series setup:
  - `frontend/src/components/podcasts/SetupForm.tsx` moves its Start button into `StartActions` (≤ 20 lines);
  - `frontend/src/hooks/podcasts/useSetupShow.ts` reads the listing's `series`;
  - `frontend/src/pages/PodcastSetup.tsx` renders `ContinueEpisode` or `StartActions`, and `SeriesHosts` instead of `SetupHosts` when `series.episode_count ≥ 1`.

  T046 and T047 pass, and `npm run test:e2e` is green.
- [X] T063 [P] [US1] Write the hand-run benchmarks (research R12, quickstart §3), marked `@pytest.mark.benchmark`:
  - `backend/tests/integration/podcasts/test_series_recall_benchmark.py`:
    - 20 scripted two-episode series on the default local setup;
    - each episode 1 has learner lines with a known fact, and each episode 2 runs to 10 host lines;
    - writes rows to `specs/010-recurring-podcast-shows/series-review-sheet.md` (SC-002, SC-003);
  - `backend/tests/integration/podcasts/test_series_latency_benchmark.py`:
    - the median time to the first `line` frame of episode 1 and of episode 10 on the same series with full memory, 10 runs each (SC-006), with prompt token counts printed;
    - the p90 of the `?wait=true` catch-up straight after a Medium sign-off, 10 runs, with a target of ≤ 15 s.
- [X] T064 [US1] Run T063 against `llama3.1:8b`: `backend/.venv/bin/pytest -m benchmark tests/integration/podcasts -k "series" -s`. Record the results in `specs/010-recurring-podcast-shows/series-review-sheet.md`, and fill the SC-002 and SC-003 review columns by hand. If SC-002 or SC-003 is missed, note it for T135 before building further on recall quality.
- [ ] T065 [US1] US1 checkpoint: run the full backend and frontend suites, then quickstart §4 steps 1–4 by hand (series continuity, per language, unfinished, waiting for memory).

**Checkpoint**: a show continues as a series with the same hosts and remembered points.

---

## Phase 4: User Story 3 - Hosts stay consistent unless deliberately changed (Priority: P1) 🎯 MVP

**Goal**:
- a series episode's setup has no one-click Shuffle;
- **Recast…** replaces one host on purpose, after a confirmation, for this and later episodes, and the new host is introduced as new;
- the learner can see what the hosts remember and **Start over**;
- an unstarted ready-made show always shows its card's hosts;
- a name clash is pointed out.

**Independent Test**: on episode 2's setup there is no Shuffle. Recast one host, confirm, and verify
that episode 3 keeps the new host while the other host and the count are unchanged (spec US3).

### Tests for User Story 3 (write first, see them fail)

- [X] T066 [P] [US3] Extend `backend/tests/unit/podcasts/test_series_service.py` with recast and reset (research R8, data-model §6):
  - `recast(series_id, slot, personality_id, learner_name, language)` uses `HostCaster.recast`:
    - the slot gets a new name, unlike the other host's and the learner's;
    - the personality is the chosen one, or a random one the other host does not have;
    - `joined_after_episodes` is set to the current count;
    - the other slot, the count and the memories are unchanged;
  - the other host's personality raises `PersonalityTaken` ("{other} already has that personality. Pick another one.");
  - a series in another language than `settings.target_language` raises `LanguageChanged`;
  - `reset(series_id)` deletes the series; the show row stays if it is a favourite, or if it is a learner-made show (which has been played), and is deleted otherwise (data-model §2.1, §5.1);
  - a series host's name equal to `learner_name` (casefold) raises the clash with "{name} has the same name as you. Change the name the hosts call you.", and **no** Shuffle advice.

  Extend `backend/tests/unit/podcasts/test_casting.py` too: `HostCaster.recast(..., personality_id="joker")` gives that personality; without `personality_id` it behaves exactly as today (007's Shuffle).
- [X] T067 [P] [US3] Extend `backend/tests/unit/podcasts/test_series_prompts.py` with new hosts:
  - with `new_host_slots=("second",)`, the section tells the hosts to introduce {name} as new to the show, someone who does not know the earlier episodes;
  - that host's `greet` cue asks them to introduce themselves as new to the show;
  - with a new lead, the `open` cue adds "introduce yourself as the show's new host".
- [X] T068 [P] [US3] Write `backend/tests/contract/test_podcast_series_hosts_api.py` (contracts §1, §6, §7):
  - `POST /series/{id}/hosts/{slot}/recast` returns 200 with the §5 shape: the recast slot has `has_history: false` and `is_new_next_episode: true`;
  - recast returns 422 for a bad slot, for the other host's personality, and for `LANGUAGE_CHANGED`, and 404 for an unknown series;
  - `DELETE /series/{id}` returns 204, then the series is 404; an unknown id returns 404;
  - FR-010: two `GET /catalog` calls with the same language and learner name list identical hosts for every unstarted ready-made show;
  - a `kind=series` start whose series host is named like the learner returns 422 with the clash message.
- [X] T069 [P] [US3] Write `backend/tests/integration/podcasts/test_series_recast_and_reset.py`:
  - after episode 2, recast the second host and start episode 3: the snapshot's `new_host_slots == ("second",)`, the lead is unchanged, and the standing prompt introduces the new host;
  - episode 4 keeps the new host, with no new-host line;
  - SC-001 holds across the recast;
  - a reset deletes the series, hosts, links and memories; the episodes stay in `GET /episodes` with `episode_number: null`; the show then offers episode 1.
- [X] T070 [P] [US3] Write `frontend/src/components/shared/ConfirmDialog.test.tsx`:
  - `role="alertdialog"`, labelled and described;
  - focus moves into it and is trapped;
  - Escape and Cancel call `onCancel` and return focus to the opener;
  - Confirm calls `onConfirm`.
- [X] T071 [P] [US3] Write the US3 component and hook tests in `frontend/src/components/podcasts/` and `frontend/src/hooks/podcasts/`:
  - `RecastDialog.test.tsx`:
    - the message says the new host will not know the earlier history;
    - a `ThemedSelect` offers "Any" plus the personalities the other host does not have;
    - the voice note appears when the recast host keeps the slot's voice;
    - Cancel sends nothing;
  - `useRecast.test.tsx`: posts and refreshes the series and catalogue queries;
  - `RememberedPoints.test.tsx`:
    - a disclosure lists topics and "about you" points with their episode numbers;
    - it shows "Updating…" while `memory_status` is `running`;
    - **Start over** opens a `ConfirmDialog`;
  - `LearnerNameField.test.tsx` (extended): a `role="status"` clash hint is linked to the field by `aria-describedby`.
- [X] T072 [P] [US3] Extend `frontend/e2e/podcast-series.spec.ts`:
  - episode 2's setup has no Shuffle and no personality drop-down;
  - **Recast…** → Cancel sends no request;
  - **Recast…** → choose a personality → Confirm posts the recast and shows the new host in place;
  - the remembered points disclosure lists the mocked points;
  - **Start over** → Confirm sends `DELETE` and the setup then offers Episode 1;
  - the name-clash hint shows when the learner's name equals a host's.

### Implementation for User Story 3

- [X] T073 [US3] Add the new-host wording to `_series_section` and `_instruction` in `backend/app/podcasts/prompts.py` (contracts §9). T067 passes, and T006 stays green.
- [X] T074 [US3] Recast and reset:
  - give `HostCaster.recast` in `backend/app/podcasts/services/casting.py` an optional keyword `personality_id: str | None = None`, used instead of the random choice when given (11 → ≈ 12 lines). 007's Shuffle calls it without one and is unchanged;
  - add `recast(...)` and `reset(...)` to `SeriesService` in `backend/app/podcasts/services/series.py`, with `PersonalityTaken` and `LanguageChanged`, and the series name-clash check in `prepare` (for every series episode, including after the first).

  T066 passes.
- [X] T075 [US3] Give `validate_draft` and `_host_problem` in `backend/app/podcasts/schemas.py` a `clash_message` argument (≈ 10 and 10 lines after T053's `show_problem` split), so that series starts use the data-model §6 wording, while one-offs keep 007's.
- [X] T076 [US3] Add `POST /series/{series_id}/hosts/{slot}/recast` and `DELETE /series/{series_id}` to `backend/app/podcasts/series_routes.py`, mapping the errors as in data-model §6. T068 and T069 pass.
- [X] T077 [P] [US3] Add `recastHost(seriesId, slot, body)` and `resetSeries(seriesId)` to `frontend/src/services/podcastsApi.ts`.
- [X] T078 [P] [US3] Implement `frontend/src/components/shared/ConfirmDialog.tsx`: an `alertdialog` with a focus trap and focus return, tokens only, and a `--color-error` confirm style for destructive actions. T070 passes.
- [X] T079 [US3] Implement `frontend/src/hooks/podcasts/useRecast.ts` and `frontend/src/components/podcasts/RecastDialog.tsx` (`ConfirmDialog` plus `ThemedSelect`).
- [X] T080 [US3] Implement `frontend/src/components/podcasts/RememberedPoints.tsx`: a disclosure with Start over through `ConfirmDialog` and `resetSeries`.
- [X] T081 [US3] Add the name-clash hint to `frontend/src/components/podcasts/LearnerNameField.tsx`, which receives the series host names from `SetupForm`. T071 passes.
- [X] T082 [US3] Wire **Recast…** into `SeriesHostCard.tsx`, and `RememberedPoints` into `frontend/src/pages/PodcastSetup.tsx`. T072 passes, and `npm run test:e2e` is green.
- [ ] T083 [US3] US3 checkpoint: run the full suites, then quickstart §4 step 6 and the step 10 edge cases (name clash, Start over).

**Checkpoint (MVP)**: US1 + US3 deliver a long-running show with consistent, deliberately changeable
hosts.

---

## Phase 5: User Story 2 - Quick one-off episode instead (Priority: P1)

**Goal**: from the same show, the learner can choose a one-off episode, as in 007. It has free
Shuffle and personality choice, and neither reads nor adds to the series.

**Independent Test**: with a series in progress, start a one-off. It is labelled one-off, makes no
reference to earlier episodes, and leaves the series' count and memory unchanged (spec US2).

### Tests for User Story 2 (write first, see them fail)

- [X] T084 [P] [US2] Write `backend/tests/integration/podcasts/test_one_off_isolation.py` (FR-007, quickstart §1):
  - with a series at episode 2 and remembered points, a `kind=one_off` start, its lines and its sign-off write no `podcast_series*` row, no link row and no memory;
  - `EpisodeEndings` is not triggered;
  - the next episode number and `remembered` are unchanged;
  - the one-off's standing prompt has no series section and equals the golden one-off text for its inputs;
  - US2-4: one-off hosts that differ from the series' hosts start fine and leave the series' hosts unchanged.
- [X] T085 [P] [US2] Extend `backend/tests/contract/test_podcast_series_episodes_api.py`:
  - a request with no `kind` gives a 007-shaped 201 response with `series: null`;
  - a one-off of a learner-made show assigns `show.saved_show_id` and sets `last_played_at` (FR-014, plan interpretation 7);
  - a one-off of a ready-made show creates no `podcast_shows` row when none exists, and touches `last_played_at` when one does.
- [X] T086 [P] [US2] Write `frontend/src/components/podcasts/EpisodeKindFieldset.test.tsx`, and extend `frontend/src/pages/PodcastSetup.test.tsx`:
  - the two choice tiles are "Episode N" (the default) and "One-off episode";
  - choosing one-off swaps `SeriesHosts` for 007's `SetupHosts` with Shuffle and personality, and the primary action reads **Start one-off episode**;
  - Start sends `kind: "one_off"` with the shuffled hosts.
- [X] T087 [P] [US2] Extend `frontend/e2e/podcast-series.spec.ts`:
  - choose One-off, Shuffle a host, and Start: the request has `kind: "one_off"`, and the episode header reads "· One-off";
  - back on the show, the card still says "Episode 2 next".

### Implementation for User Story 2

- [X] T088 [US2] Add the one-off path to `SeriesService.prepare` in `backend/app/podcasts/services/series.py`:
  - keep and touch a learner-made show;
  - touch a ready-made show only if its row exists;
  - never read or write a series.

  `start_episode` in `backend/app/podcasts/routes.py` now always delegates. T084 and T085 pass.
- [X] T089 [US2] Implement `frontend/src/components/podcasts/EpisodeKindFieldset.tsx`, built on `ChoiceTile`.
- [X] T090 [US2] Integrate the one-off choice:
  - `SetupForm.tsx` gains `kind`;
  - `StartActions.tsx` labels **Start one-off episode**;
  - `useStartEpisode.ts` sends `kind` and skips the memory wait for one-offs;
  - `EpisodeHeader.tsx` shows "· One-off" when `series` is null on an episode started from a show with a series;
  - `frontend/src/pages/PodcastSetup.tsx` shows `SetupHosts` for one-offs.

  T086 and T087 pass, and `npm run test:e2e` is green.
- [X] T091 [P] [US2] Write `backend/tests/integration/podcasts/test_one_off_isolation_benchmark.py` (`@pytest.mark.benchmark`, SC-004, research R12): 20 one-off episodes of shows with a series in progress. It lists every host line mentioning "last time", "last episode" or the known facts in `series-review-sheet.md`.
- [ ] T092 [US2] US2 checkpoint: run the full suites, then quickstart §4 step 5.

**Checkpoint**: the series and the quick one-off sit side by side.

---

## Phase 6: User Story 6 - Drop-downs match the theme when open (Priority: P2)

**Goal**: every drop-down in the app draws its open list in the current theme. The selected and
focused options are distinguishable, with ≥ 4.5:1 contrast (FR-021, SC-008).

**Independent Test**: in light, dark and system-dark themes, open each drop-down. The options use the
theme's surface and text with readable contrast, and the selected and focused options are distinct
(spec US6).

This phase depends only on Phase 2 (`ThemedSelect`), so it can run in parallel with Phases 3–5.
Its HostCard change (T103) and the US2 setup work both touch the podcast setup, so finish T103
before T090, or after it, never at the same time.

### Tests for User Story 6 (write first, see them fail)

- [X] T093 [US6] Add `chooseOption(page, label, optionName)` to `frontend/e2e/fixtures.ts`: it opens the combobox named `label` and clicks the option named `optionName`. Also add `contrastRatio(foreground, background)` (the WCAG relative-luminance formula over computed `rgb()` strings).
- [X] T094 [P] [US6] Write `frontend/e2e/themed-select.spec.ts`. Open each drop-down below in light, dark and system-dark themes (`page.emulateMedia({ colorScheme })` plus the app's theme setting):
  - the podcast setup personality drop-down;
  - Settings' `SelectField`s;
  - the chat Level control;
  - the flashcards word filter;
  - the provider model and effort fields.

  For each, assert:
  - the listbox's computed background equals `--color-surface` and the option text equals `--color-text`;
  - `contrastRatio` is ≥ 4.5 for normal, selected and focused options;
  - the focused option's outline differs from the other options';
  - keyboard navigation (↓, Enter, Escape) works.
- [X] T095 [P] [US6] Update the Settings Vitest tests to open the combobox and click an option instead of `selectOptions`, and to assert the combobox roles: `frontend/src/components/settings/LlmProviderFields.test.tsx`, `ConversationLevelSection.test.tsx` and `frontend/src/pages/Settings.test.tsx`.
- [X] T096 [P] [US6] Update the same way `frontend/src/components/chat/ConversationLevelControl.test.tsx` and `frontend/src/pages/Chat.test.tsx`.
- [X] T097 [P] [US6] Update the same way `frontend/src/components/flashcards/WordFilterBar.test.tsx` and the flashcards page tests that drive the filter (`frontend/src/pages/Flashcards.test.tsx`, `FlashcardDecks.test.tsx`).
- [X] T098 [P] [US6] Update the same way `frontend/src/components/podcasts/HostCard.test.tsx` and the personality cases in `frontend/src/pages/PodcastSetup.test.tsx`.

### Implementation for User Story 6

- [X] T099 [P] [US6] Replace the `<select>` in `frontend/src/components/settings/SelectField.tsx` with `ThemedSelect`, keeping the props unchanged.
- [X] T100 [P] [US6] Replace the `<select>`s in `frontend/src/components/settings/LlmProviderFields.tsx` with `ThemedSelect`.
- [X] T101 [P] [US6] Replace the `<select>` in `frontend/src/components/chat/ConversationLevelControl.tsx` with `ThemedSelect`.
- [X] T102 [P] [US6] Bring `WordFilterBar` under the function-length limit, then replace its `<select>` (Constitution I: a modified function longer than 20 lines is brought within the limit):
  - **Refactor first**, with `WordFilterBar.test.tsx` and `flashcards.spec.ts` green before and after. Split `frontend/src/components/flashcards/WordFilterBar.tsx` (197 lines, with inner arrow functions of 40 and 27) into colocated components, `ClassificationPills.tsx`, `WordSortSelect.tsx` and `DatePresetChips.tsx`, and move the inline style objects to module-level constants. Every function ends ≤ 20 lines, and the behaviour and accessible names are unchanged;
  - replace the `<select>` inside `WordSortSelect` with `ThemedSelect`;
  - add `src/components/flashcards/WordFilterBar.tsx`, `ClassificationPills.tsx`, `WordSortSelect.tsx` and `DatePresetChips.tsx` to the `max-lines-per-function` override in `frontend/.eslintrc.json`. `npm run lint` is green.
- [X] T103 [P] [US6] Replace the personality `<select>` in `frontend/src/components/podcasts/HostCard.tsx` with `ThemedSelect` (≈ 15 lines). The rule that two hosts never share a personality is unchanged.
- [X] T104 [US6] Move the existing E2E specs from `selectOption()` to `chooseOption()`: `frontend/e2e/settings.spec.ts`, `conversation-level.spec.ts`, `practice-language.spec.ts`, `flashcards.spec.ts` and `podcasts.spec.ts`.
- [X] T105 [US6] Delete the `option { … }` rule and its comment from `frontend/src/index.css` (around line 225). Confirm that `grep -rn "<select\|<option" frontend/src --include=*.tsx` returns nothing.
- [X] T106 [US6] US6 checkpoint: `npm run lint`, `npm test` and `npm run test:e2e` are green, including T094; then quickstart §4 step 9.

**Checkpoint**: every drop-down is themed and checked automatically in both themes.

---

## Phase 7: User Story 4 - Favourite shows at the top (Priority: P2)

**Goal**:
- any show can be favourited, and the favourite is the same in every language;
- **My shows** lists the favourites, the series in this language and the played learner-made shows, each with its next episode number;
- a kept learner-made show reopens with the same title, premise and hosts;
- a kept learner-made show can be removed from My shows after a confirmation (FR-024).

**Independent Test**: favourite a ready-made show and a generated show with an episode, then reload.
Both appear in My shows with their next episode numbers. Unfavouriting removes a show unless it
has a series or is a played learner-made show; Remove takes the played generated show out; the
ready-made list is unchanged (spec US4).

### Tests for User Story 4 (write first, see them fail)

- [X] T107 [P] [US4] Write `backend/tests/contract/test_podcast_favourites_api.py` (contracts §3):
  - `PUT /favourites {show, is_favourite: true}` returns 200 with the updated `ShowListing` (`is_favourite: true`), and an unsaved learner-made draft gains `saved_show_id`;
  - unfavouriting returns 204 when the row was deleted (a ready-made show with no series, or a learner-made show never played and with no series), and 200 otherwise;
  - a bad draft returns 422;
  - `DELETE /shows/{saved_show_id}` returns 204 for a kept learner-made show, and 404 "That show isn't kept any more. Pick another one." for an unknown id or a ready-made row (contracts §3, FR-024).
- [X] T108 [P] [US4] Write `backend/tests/integration/podcasts/test_my_shows.py` (contracts §1, §3, research R9):
  - `my_shows` is exactly the favourites, the shows with a series in this language and the played learner-made shows, newest activity first;
  - a ready-made show in `my_shows` equals its entry in `shows`;
  - a favourite made in `es` appears in `de` too, while the series and hosts stay per language;
  - a favourite survives a restart (a new engine over the same file);
  - unfavouriting a show with a series keeps it in `my_shows`, and so does unfavouriting a played learner-made show;
  - removing a played learner-made show with series in `es` and `de` takes it out of `my_shows` in both languages and deletes both series; its episodes stay in `GET /episodes` with `episode_number: null` (FR-024);
  - favouriting the same unsaved draft twice keeps one show;
  - a played generated show appears without a favourite, and its next series episode keeps the same hosts (US4-3);
  - `POST /episodes` with a stale `saved_show_id` returns 404;
  - with no favourites, series or kept shows, `my_shows == []` (US4-4).
- [X] T109 [P] [US4] Write the US4 Vitest tests:
  - `frontend/src/hooks/podcasts/useFavourite.test.tsx`: optimistic toggle, rollback with a message on failure;
  - `frontend/src/components/podcasts/FavouriteToggle.test.tsx`: a separate `button` with `aria-pressed`, named "Favourite {title}";
  - `MyShows.test.tsx`: a labelled region, hidden when empty, with "Episode N next" per show; a kept learner-made show has a secondary **Remove** button named "Remove {title}", which opens a `ConfirmDialog`; Cancel sends nothing, Confirm calls `removeShow` and the show leaves the list; ready-made shows have no Remove;
  - `ShowCard.test.tsx` (extended): the card is a group with the choose button and the toggle side by side, never nested;
  - `frontend/src/pages/Podcasts.test.tsx`: My shows sits above the ready-made list;
  - `frontend/src/hooks/podcasts/useShowDraft.test.tsx` or a new `useSetupShow.test.tsx`: `?saved=<id>` finds the show in `my_shows`.
- [X] T110 [P] [US4] Write `frontend/e2e/podcast-favourites.spec.ts`:
  - favourite and unfavourite: the request body and the toggle state;
  - My shows appears and hides;
  - a series show stays after unfavouriting;
  - after a reload, the mocked catalogue lists the favourite;
  - choosing a kept learner-made show opens `/podcasts/setup?saved=<id>` with its title and hosts;
  - **Remove** on a kept learner-made show: Cancel sends no request; Confirm sends `DELETE /api/podcasts/shows/<id>` and the show leaves My shows;
  - SC-005: from `/podcasts`, choosing a favourite in My shows and then **Start episode N** sends the `POST /episodes` request, which is two choices.

### Implementation for User Story 4

- [X] T111 [US4] Add `favourite(draft, is_favourite)`, `mine(language)` and `remove(saved_show_id)` to `ShowLibrary` in `backend/app/podcasts/services/library.py`, delegating to `set_favourite`, `list_mine` and `forget`; `remove` raises `ShowNoLongerKept` when `forget` returns `False`.
- [X] T112 [US4] Add to `backend/app/podcasts/series_routes.py`:
  - `PUT /favourites`, returning 200 with a `ShowListing`, or 204 when the row was deleted;
  - `DELETE /shows/{saved_show_id}`, returning 204, or 404 with the data-model §6 message for `ShowNoLongerKept`.

  T107 passes.
- [X] T113 [US4] Fill `my_shows` and `is_favourite`:
  - in `backend/app/podcasts/responses.py`: `catalog_listings` and a new `my_show_listings(entries, ...)`;
  - in `get_catalog` in `backend/app/podcasts/routes.py`: still ≤ 11 lines.

  T108 passes.
- [X] T114 [P] [US4] Add `setFavourite(show, isFavourite)` and `removeShow(savedShowId)` to `frontend/src/services/podcastsApi.ts`.
- [X] T115 [US4] Implement `frontend/src/hooks/podcasts/useFavourite.ts`: optimistic update of the catalogue query, rolled back with a plain message on failure.
- [X] T116 [US4] Implement the US4 components in `frontend/src/components/podcasts/`:
  - `FavouriteToggle.tsx`;
  - `ShowCard.tsx` as a group, ≈ 18 lines;
  - `MyShows.tsx`, with the **Remove** button and its `ConfirmDialog` on kept learner-made shows (extract a `RemoveShowButton.tsx` if `MyShows` would pass 20 lines); removing invalidates the catalogue query.
- [X] T117 [US4] Integrate My shows:
  - `frontend/src/pages/Podcasts.tsx` adds `<MyShows>` above `ShowList`;
  - `frontend/src/hooks/podcasts/useSetupShow.ts` accepts `?saved=`, with the lookup moved to `findShow(catalog, params)`;
  - `ShowList.tsx` passes the toggle through.

  T109 and T110 pass, and `npm run test:e2e` is green.
- [ ] T118 [US4] US4 checkpoint: run the full suites, then quickstart §4 step 7, including the app restart.

**Checkpoint**: favourites and series are one choice away from the Podcasts screen (SC-005).

---

## Phase 8: User Story 5 - Find a new show (Priority: P2)

**Goal**: **Find a new show** returns 3–5 fresh, suitable suggestions shaped by the learner's
interests. None duplicates a show they can already see, and none is stored unless favourited or
played. The ready-made list never changes.

**Independent Test**: with interests saved, choose Find a new show twice. Each set is new and differs
from the other; starting one opens setup; the ready-made list is unchanged (spec US5).

### Tests for User Story 5 (write first, see them fail)

- [X] T119 [P] [US5] Write `backend/tests/unit/podcasts/test_discovery.py` (research R10), with the scripted provider (T028) and a seeded `random.Random`:
  - `SuggestionSeeds.draw(interests)` returns `SUGGESTION_SEEDS` distinct seeds: with interests, exactly `INTEREST_SEEDS` come from them; without, all come from the built-in `SurpriseTopics` vocabulary;
  - `normalise_title` casefolds and strips punctuation and spacing;
  - `ShowDiscovery.suggest(avoid_titles, interests, mine, language)`:
    - makes one structured call;
    - drops unsuitable, unreadable and duplicate shows (duplicates of a ready-made title, one of `mine` or an `avoid_titles` entry);
    - casts hosts with `HostCaster.cast_personalities`;
    - returns drafts with `source="suggested"`;
  - fewer than `MIN_SUGGESTIONS` survivors trigger exactly one top-up call for the shortfall, with fresh seeds;
  - still too few raises `NotEnoughSuggestions`;
  - an `LLMError` propagates unchanged.
- [X] T120 [P] [US5] Extend `backend/tests/unit/podcasts/test_generator.py`: the public `parse_show(parsed: dict)` reads one show object exactly as `_show_reply` did, and `ShowGenerator.generate` behaves the same as before.
- [X] T121 [P] [US5] Write `backend/tests/unit/podcasts/test_discovery_prompts.py`:
  - `DISCOVERY_JSON_SCHEMA` is an object with `shows`, an array of `SHOW_JSON_SCHEMA` items with `minItems: 1` and `maxItems: 5`;
  - the prompt lists every seed and every title to avoid;
  - the prompt reuses the generator's suitability and field rules;
  - the prompt names the languages, never their codes.
- [X] T122 [P] [US5] Write `backend/tests/contract/test_podcast_discovery_api.py` (contracts §4):
  - `POST /shows/discover {avoid_titles: []}` returns 200 with 3–5 suggestions, each a `ShowDraft` with `source: "suggested"`;
  - too few survivors return 503 "Find a new show didn't come up with enough shows this time. Please try again.";
  - an `LLMError` returns 503 with the provider's message;
  - `avoid_titles` with more than 50 entries, or with an entry over 200 characters, returns 422.
- [X] T123 [P] [US5] Write `backend/tests/integration/podcasts/test_discovery_keeps_nothing.py`:
  - a discover call writes no row in any table (table counts before and after);
  - a suggestion passed to `PUT /favourites` is kept and appears in `my_shows`;
  - a suggestion started as an episode is kept;
  - ignored suggestions leave nothing behind (FR-019);
  - `shows` is identical before and after (FR-015).
- [X] T124 [P] [US5] Write the US5 Vitest tests:
  - `frontend/src/hooks/podcasts/useShowDiscovery.test.tsx`: it sends every title shown this visit as `avoid_titles` on "Show me others", and exposes the plain error message;
  - `frontend/src/components/podcasts/FindNewShow.test.tsx`:
    - the button and the progress text, in an `aria-live="polite"` region;
    - the cards have a title, topic, premise, hosts and a favourite toggle;
    - choosing a card navigates to setup with the draft in router state;
    - on error, the plain message shows and the rest of the screen still works;
  - `frontend/src/pages/Podcasts.test.tsx` (extended).
- [X] T125 [P] [US5] Write `frontend/e2e/podcast-discovery.spec.ts`:
  - **Find a new show** shows the mocked suggestions;
  - **Show me others** sends `avoid_titles` holding the first set;
  - favouriting a suggestion sends `PUT /favourites` with `source: "suggested"`;
  - starting a suggestion opens the setup;
  - a 503 shows its message;
  - the ready-made list is the same before and after.

### Implementation for User Story 5

- [X] T126 [US5] Make `_show_reply` the public `parse_show` in `backend/app/podcasts/services/generator.py`, with no change in length. T120 passes.
- [X] T127 [US5] Add `DISCOVERY_JSON_SCHEMA` and `discovery_prompt(seeds, avoid_titles, languages)` to `backend/app/podcasts/prompts.py`, reusing the generator's rule text. T121 passes, and T006 stays green.
- [X] T128 [US5] Implement `SuggestionSeeds`, `normalise_title`, `ShowDiscovery` and `NotEnoughSuggestions` in the new `backend/app/podcasts/services/discovery.py`. It takes the `StructuredLLMProvider`, a `HostCaster`, `SurpriseTopics` and an injected `random.Random`. T119 passes.
- [X] T129 [US5] Create `backend/app/podcasts/discovery_routes.py` with `POST /shows/discover`:
  - add a `get_show_discovery` dependency, like `show_routes.get_show_generator`;
  - read the interests from the podcast preferences;
  - build `mine` from `ShowLibrary.mine(language)`;
  - map `NotEnoughSuggestions` to the plain 503.

  Include it from `backend/app/podcasts/routes.py`. T122 and T123 pass.
- [X] T130 [P] [US5] Add `discoverShows(avoidTitles)` to `frontend/src/services/podcastsApi.ts`.
- [X] T131 [US5] Implement and integrate discovery:
  - `frontend/src/hooks/podcasts/useShowDiscovery.ts`;
  - `frontend/src/components/podcasts/FindNewShow.tsx`, reusing `ShowCard` and `FavouriteToggle`;
  - `frontend/src/pages/Podcasts.tsx` adds `<FindNewShow>` as a secondary action.

  T124 and T125 pass, and `npm run test:e2e` is green.
- [X] T132 [P] [US5] Write `backend/tests/integration/podcasts/test_discovery_benchmark.py` (`@pytest.mark.benchmark`, SC-007): 10 requests. Print the time to response, the count, the duplicates and the suitability for each.
- [ ] T133 [US5] US5 checkpoint: run the full suites, quickstart §2 (the API smoke check), and quickstart §4 step 8.

**Checkpoint**: all six stories work independently.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: measured quality, documentation, accessibility and full validation.

- [ ] T134 Run every hand-run benchmark on `llama3.1:8b`: `backend/.venv/bin/pytest -m benchmark tests/integration/podcasts -k "series or one_off or discovery" -s`. Then complete `specs/010-recurring-podcast-shows/series-review-sheet.md` against the quickstart §3 bars:
  - SC-002: ≥ 16/20 correct references and 0 invented memories;
  - SC-003: ≥ 18/20 new topics;
  - SC-004: 0 references in one-offs;
  - SC-006: episode 10 within 20% of episode 1;
  - the catch-up wait: p90 ≤ 15 s;
  - SC-007: ≥ 3 suggestions within 30 s.
- [X] T135 If SC-002 or SC-003 is missed, ship series as **experimental**, as 003 and 005 did:
  - add a note on the series setup screen, in a small component in `frontend/src/components/podcasts/`, with a Vitest test and an E2E assertion in `podcast-series.spec.ts`;
  - record it in `docs/architecture.md` § "Open items".

  Record any other missed bar there too.
- [X] T136 [P] Update `docs/architecture.md`:
  - series beside episodes: the link table, the snapshot, copying hosts per episode;
  - the memory keeper, the catch-ups and the Start wait;
  - My shows and discovery;
  - `ThemedSelect` replacing the native selects;
  - the extended composition-root exception.
- [X] T137 [P] Document `ThemedSelect` and `ConfirmDialog` in the component patterns and do/don't guide of `docs/design-system.md`.
- [X] T138 Update `CLAUDE.md`:
  - add the 010 domain-module note (series code inside `app/podcasts/`, the new factory imports) and a "Recent Changes" entry;
  - list 010 in the overview's shipped features.

  `CLAUDE.md` has uncommitted local edits: read it first, and change only these lines.
- [ ] T139 Run the full quality gate:
  - backend: `backend/.venv/bin/pytest` (≥ 90% coverage, zero skips), including `test_function_length.py`, `test_module_boundaries.py` and `test_no_language_literals.py`;
  - `ruff check .` and `black --check .`;
  - frontend: `npm run lint`, `npm run build`, `npm test` and `npm run test:e2e`.
- [ ] T140 Validate the whole quickstart:
  - §1 automated suites;
  - §4 walkthrough steps 1–10 in dark mode;
  - §5 preservation check against `~/.open-language/app.db.pre-010` (T002);
  - §6 manual accessibility check: keyboard-only, dialogs, Orca, contrast and 44px targets.

  Record the results in the PR description.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T003 is needed by T005.
- **Foundational (Phase 2)**: depends on Setup. **Blocks every story.**
- **US1 (Phase 3)**: depends on Foundational.
- **US3 (Phase 4)**: depends on US1. It extends `SeriesService`, `series_routes.py`, the prompts and the series setup, and its Recast dialog uses `ThemedSelect` from Foundational.
- **US2 (Phase 5)**: depends on US1 (`SeriesService`, `StartActions`, `kind`). It does not need US3.
- **US6 (Phase 6)**: depends only on Foundational, so it can run in parallel with Phases 3–5.
- **US4 (Phase 7)**: depends on US1 (series summaries in listings, `ShowLibrary`). It does not need US2, US3 or US6.
- **US5 (Phase 8)**: depends on US4 (`PUT /favourites`, `my_shows` and `FavouriteToggle` on suggestions).
- **Polish (Phase 9)**: depends on every story. T135 needs T134's results.

### Within the Foundational phase

- The tests T005–T017 run in parallel. T006 passes on today's code, since it is a pin; every
  other test fails first, T005 until T019 adds the tables.
- Backend chain:
  - T018 → T019 → T020;
  - T021 and T022 in parallel after T020;
  - T023 after T021 and T022;
  - T024 → T025, which share `sqlite_series_storage.py`;
  - T026 after T025;
  - T027 after T020.
- T028, T029 and T030 are independent of the backend chain. T030 needs T017.

### Within each story

- Test tasks first; confirm that they fail.
- Backend before the frontend that calls it.
- Components before pages.
- Each story ends with a full-suite run and its quickstart steps (T065, T083, T092, T106, T118,
  T133).

### Shared files: never run two of these tasks at the same time

- `backend/app/podcasts/prompts.py`: T048, T049, T073, T127.
- `backend/app/podcasts/routes.py`: T027, T051, T053, T058, T088, T113, T129.
- `backend/app/podcasts/series_routes.py`: T058, T076, T112.
- `backend/app/podcasts/services/series.py`: T053, T074, T088.
- `backend/app/podcasts/schemas.py`: T020, T053, T075.
- `backend/app/podcasts/services/sqlite_series_storage.py`: T024, T025.
- `backend/app/services/factory.py`: T026, T051, T056.
- `frontend/.eslintrc.json`: T004, T102.
- `backend/app/podcasts/responses.py`: T027, T057, T113.
- `frontend/src/services/podcastsApi.ts`: T029, T059, T077, T114, T130.
- `frontend/src/pages/PodcastSetup.tsx`: T062, T082, T090.
- `frontend/src/pages/Podcasts.tsx`: T117, T131.
- `frontend/src/components/podcasts/ShowCard.tsx`: T061, T116.
- `frontend/e2e/podcast-series.spec.ts`: T047, T072, T087.
- `frontend/e2e/fixtures.ts`: T029, T093.

### Parallel Opportunities

- Setup: T004 alongside T001–T003.
- Foundational: all 13 test tasks (T005–T017) together; then T028, T029 and T030 alongside the
  backend chain.
- US1: the tests T032–T047 together; T059 and T061 alongside the backend T048–T058; T063 at any
  time after T058.
- US3: T066–T072 together; T077 and T078 together.
- US2: T084–T087 together; T091 at any time.
- US6: T094–T098 together after T093; T099–T103 together.
- US4: T107–T110 together.
- US5: T119–T125 together; T130 and T132 alongside the backend.
- Across stories: US6 runs beside US1–US3. After US1, US2 and US4 can proceed in parallel,
  observing the shared-file list above.
- Polish: T136 and T137 together.

---

## Parallel Example: Foundational tests

```bash
# All foundation tests together (T006 is a pin and passes on today's code; the others, T005 included, fail first):
Task: "T005 upgrade pin — backend/tests/integration/podcasts/test_series_upgrade_preserves_data.py"
Task: "T006 one-off golden — backend/tests/unit/podcasts/test_one_off_golden.py"
Task: "T010 show library storage — backend/tests/unit/podcasts/test_sqlite_show_library.py"
Task: "T011 series storage — backend/tests/unit/podcasts/test_sqlite_series_storage.py"
Task: "T013 series values — backend/tests/unit/podcasts/test_series_values.py"
Task: "T017 ThemedSelect — frontend/src/components/shared/ThemedSelect.test.tsx"
```

## Parallel Example: User Story 1

```bash
# All US1 tests together (each must fail first):
Task: "T032 SeriesService.prepare — backend/tests/unit/podcasts/test_series_service.py"
Task: "T033 series prompt section and cues — backend/tests/unit/podcasts/test_series_prompts.py"
Task: "T034 memory parser and grounding — backend/tests/unit/podcasts/test_series_memory.py"
Task: "T035 bounded memory properties — backend/tests/unit/podcasts/test_series_memory_properties.py"
Task: "T040 series lifecycle — backend/tests/integration/podcasts/test_series_lifecycle.py"
Task: "T041 catch-up — backend/tests/integration/podcasts/test_series_memory_catch_up.py"
Task: "T047 E2E — frontend/e2e/podcast-series.spec.ts"

# Independent implementation files together:
Task: "T059 podcastsApi.ts series functions"
Task: "T061 ShowCard, SeriesHosts, SeriesHostCard, ContinueEpisode, StartActions, EpisodeHeader"
```

## Parallel Example: User Story 6

```bash
Task: "T099 SelectField.tsx → ThemedSelect"
Task: "T100 LlmProviderFields.tsx → ThemedSelect"
Task: "T101 ConversationLevelControl.tsx → ThemedSelect"
Task: "T102 WordFilterBar.tsx → ThemedSelect"
Task: "T103 HostCard.tsx → ThemedSelect"
```

---

## Implementation Strategy

### MVP first (User Stories 1 + 3)

1. Phase 1 Setup, including the database backup (T002) and the frozen schema (T003).
2. Phase 2 Foundational. At its checkpoint nothing visible has changed, and the one-off golden and
   upgrade pins are green.
3. Phase 3 US1, **including the recall and latency benchmarks (T063–T064)**, run before more is
   built on recall quality.
4. Phase 4 US3: Recast, Start over, the name clash and stable defaults.
5. **Stop and validate**: quickstart §4 steps 1–4, 6 and 10.

### Incremental delivery

1. Foundation → US1 + US3 (a series with consistent hosts) → demo.
2. + US2: one-off beside the series, which restores 007's quick path in the setup UI.
3. + US6: themed drop-downs. It can land at any point after Foundation.
4. + US4: favourites and My shows.
5. + US5: Find a new show.
6. Polish: benchmarks, the experimental label if needed, docs, and the full quickstart.

---

## Notes

- **[P]** means a different file with no dependency on an incomplete task. Two [P] tasks never edit
  the same file.
- Every test must be seen failing before its implementation (Red → Green → Refactor). The
  exceptions are the T005 and T006 pins, which record today's behaviour.
- **Budget versus caps** (T011, T025, T033, T048): 10 topics and 8 learner points at 160
  characters each would come to 2,880 characters, more than the 1,800-character series section.
  `remember` therefore also prunes to `REMEMBERED_TEXT_BUDGET` (1,200 characters) when it writes,
  so the renderer never drops a point, and plan interpretation 11 ("the learner never sees a list
  that differs from what the hosts get") holds in every case (research R7).
- `services/series_snapshot.py` (T022) keeps `prompts.py` from depending on `SeriesService`.
- Benchmarks are **deselected** by the existing `-m 'not benchmark and not claude_live'` addopts,
  never skipped. Results below a bar go to `docs/architecture.md` § "Open items".
- Commit after each task or logical group, ending commit messages with the attribution line the
  session requires.
