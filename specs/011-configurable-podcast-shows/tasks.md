---

description: "Task list for 011 — Configurable Podcast Shows"
---

# Tasks: Configurable Podcast Shows

**Input**: Design documents from `/specs/011-configurable-podcast-shows/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: Test tasks are MANDATORY under the TDD constitution (Principle III). Write each test task
first, and watch it FAIL before the implementation task that follows it. Two kinds of test are
exceptions to "watch it fail", because they record today's behaviour on purpose:
- the legacy pins (T005): 007's one-off golden and 010's series prompt tests, re-pointed through one
  helper. They pass on today's code and must keep passing, with **no expected text edited**, at
  every checkpoint;
- the two configured goldens (T026, T116) start as structural assertions that fail; their JSON is
  generated once the code exists, reviewed against research R5, and then pinned.

**Organization**: Tasks are grouped by user story, in the order of plan.md § "Suggested phase order":
- **Foundational**: the frozen pre-011 schema test, the legacy pins, the catalogues, the two tables
  and three preference columns, `EpisodeSettings`, the `HostTalk` ABC with `LegacyTalk` (a pure
  move of today's code), the settings row in `create_episode`, `talk` on the episode state, the
  scripted streaming provider, and the frontend types and fixtures.
- **US1** (P1, 🎯 MVP): hosts talk like podcast hosts. This covers `with_sentence_rules`,
  `ConfiguredTalk`, the invitation and line-kind policy, Jump in for One host, defaults on every new
  start, and sentence streaming (R13). The SC-001/SC-002/SC-011 benchmarks run at its end.
- **US2** (P1): Episode settings on the setup screen: the request fields, `SubjectCheck`, last-used
  preferences, `episode_options` and the disclosure.
- **US3** (P1): series settings and scopes, the standard-settings reset, and the Panel-this-episode
  expert guest. It also builds the guest-casting backend that US4 reuses.
- **US4** (P2): a guest in a regular host's place, with the away host and the "missed by" marks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 (the spec.md user stories); absent in Setup, Foundational and Polish
- Paths are relative to the repository root (`backend/app`, `backend/tests`, `frontend/src`,
  `frontend/e2e`)

## Standing rules for every task

- **Python** runs through the venv only: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff` and
  `backend/.venv/bin/black`, run from `backend/`.
- **Function length**: every new or modified function is ≤ 20 lines (Constitution I). There are no
  Complexity Tracking exceptions. Follow the extraction named in plan.md § "Function-length plan"
  for each function listed there. `backend/tests/unit/test_function_length.py` and the ESLint
  override enforce the limit. Every new frontend file lives under `src/components/podcasts/` or
  `src/hooks/podcasts/`, which the override already covers, so `frontend/.eslintrc.json` does not
  change.
- **Imports** (Principle V):
  - `app.podcasts`' package root does not change (`test_the_podcast_package_root_is_unchanged`);
  - `backend/app/services/factory.py` is the only module outside `app.podcasts` that may import
    `app.podcasts.services.spoken_parts` and `app.podcasts.services.subject_check`, on top of 010's
    list;
  - `conversation_levels`, `conversation_turns` and `services/conversation` are reached only through
    their package roots.
- **Files not modified** (plan.md § Project Structure): `backend/app/prompts/templates.py`,
  `backend/app/routers/chat.py`, `backend/app/routers/audio.py`, and anything under
  `conversation_summary/`, `services/llm/`, `services/tts/`, `practice_languages/`,
  `language_data/` or `backend/language_kit/`.
- **Additive only**: two new tables via `create_all()`, three `_ADDITIVE_COLUMNS` entries, optional
  snapshot keys. No existing column is altered and no existing row is rewritten (FR-025, SC-010).
- **Legacy is data, not a flag**: an episode with no `podcast_episode_settings` row is pre-feature,
  and `host_talk_for()` is the only place that fact becomes behaviour (R1). Never add an
  `if settings is None` check anywhere else.
- **Legacy pins are never edited**: the 007 golden file `backend/tests/unit/podcasts/golden/one_off_prompts.json`
  and every expected string in `backend/tests/unit/podcasts/test_series_prompts.py` stay byte-identical
  to commit `28ab4c7`. Only the call helper of T005 changes.
- **No per-language data** (FR-027): no language-kit `Requirement`, and no `kit.sh backfill` run.
  Sentence splitting and question detection use only punctuation. The guard
  `backend/tests/unit/test_no_language_literals.py` covers the new modules automatically.
- **No magic values**: every probability, count, limit and timeout is a named catalogue field or
  constant in `backend/app/podcasts/catalog.py` (data-model §1).
- **Provider independence** (Principle VI): streaming uses the selected session provider, and
  `SubjectCheck` uses the selected structured provider, both through the factory. A failure surfaces
  as an error (503 or an SSE error frame) and never falls back to another provider.
- **Only complete lines are stored** (007 R3): a streamed line reaches `messages` and
  `podcast_host_lines` only once its last sentence is kept; a mid-line failure stores nothing and
  ends the session.
- **Frontend styling** uses design-system tokens only (`docs/design-system.md`):
  - no hex colours;
  - `--radius-lg` for cards, `--shadow-*` for shadows;
  - `var(--color-text-on-primary)` on primary backgrounds;
  - every drop-down is `ThemedSelect` (none are needed here: settings are radio groups);
  - dialogs follow `ConfirmDialog`'s `alertdialog` pattern.
- **Frontend completion**: a frontend task is complete only when `cd frontend && npm run test:e2e`
  passes.
- **Benchmarks** are marked `@pytest.mark.benchmark`. The existing addopts deselect them; they are
  never skipped.

---

## Phase 1: Setup

**Purpose**: a green baseline, a database backup, and the frozen pre-011 schema.

- [ ] T001 Record the green baseline before any change:
  - from `backend/`: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff check .` and `backend/.venv/bin/black --check .`;
  - from `frontend/`: `npm run lint`, `npm run build`, `npm test -- --run` and `npm run test:e2e`.

  All must pass. Note any pre-existing failure in the PR description instead of fixing it here.
- [ ] T002 Back up the local database: `cp ~/.open-language/app.db ~/.open-language/app.db.pre-011`. It should hold at least one series with two or more episodes and remembered points, and one one-off episode. T134 (SC-010) compares against this copy, so take it before the app runs any 011 code.
- [ ] T003 Freeze the pre-011 schema as `backend/tests/fixtures/schema_010.sql`, following the pattern of `backend/tests/fixtures/schema_007.sql`:
  - `git worktree add "$SCRATCH/wt-pre011" 28ab4c7`. That commit is the plan; no 011 code exists in it;
  - in that worktree, run `init_db()` against an empty database with `OPEN_LANGUAGE_DB_PATH` set to a scratch file, using this repository's `backend/.venv/bin/python`;
  - `sqlite3 <file> .schema > backend/tests/fixtures/schema_010.sql`, then `git worktree remove "$SCRATCH/wt-pre011"`;
  - check the dump: `podcast_shows`, `podcast_series`, `podcast_series_hosts`, `podcast_series_episodes`, `podcast_series_memories` and `podcast_preferences` are present; `podcast_episode_settings` and `podcast_series_settings` are absent; `podcast_preferences` has no `last_style` column;
  - add a header comment naming the source commit and "Do not edit", as in `schema_007.sql`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**:
- the upgrade pin and the legacy pins;
- the Style, Host lines and How often you're asked catalogues and constants (data-model §1.1–§1.4);
- the two tables and three preference columns (data-model §2.1–§2.3);
- `EpisodeSettings` (data-model §3.1);
- the `HostTalk` ABC, `LegacyTalk` and `host_talk_for` (research R1);
- `PromptContext`, and `talk` on `EpisodeState` and `LoadedEpisode`;
- `settings` on `EpisodeRecord` / `NewEpisode`, and the settings row in `create_episode`;
- the scripted streaming session provider;
- the frontend types and E2E fixtures.

At this phase's checkpoint **nothing visible has changed**: no start writes a settings row yet, so
every episode still runs on `LegacyTalk`.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for the foundation (write first)

- [ ] T004 [P] Write the FR-025/SC-010 upgrade test `backend/tests/integration/podcasts/test_configured_upgrade_preserves_data.py`, modelled on `backend/tests/integration/podcasts/test_series_upgrade_preserves_data.py`:
  - build the pre-011 file in `tmp_path` by `executescript` of `backend/tests/fixtures/schema_010.sql` (T003). Never use `create_all()`, because the shared metadata will hold the 011 tables;
  - seed:
    - an **unfinished One host one-off episode** (`es`, Beginner) with `conversations`, `podcast_episodes`, two `podcast_hosts`, three `podcast_host_lines` with intent `discuss`, and their `messages`;
    - a **series** (`es`) with both `podcast_series_hosts`, two linked episodes in `podcast_series_episodes`, each with a 010 snapshot JSON, and three `podcast_series_memories`;
    - one roleplay conversation, two vocabulary items, the `app_settings` row and the `podcast_preferences` row;
  - snapshot every seeded row;
  - run `init_db()` **twice**, rebuilding the engine as `backend/tests/integration/conftest.py` does;
  - assert:
    - every snapshotted row is identical;
    - `podcast_episode_settings` and `podcast_series_settings` exist and are empty;
    - `podcast_preferences` has `last_style = 'balanced'`, `last_line_length = 'medium'` and `last_invite_frequency = 'sometimes'`;
    - loading the one-off through `SQLitePodcastStorage.get_episode` gives `settings is None`, and its `LoadedEpisode.standing_prompt` equals the matching One host Beginner entry of `backend/tests/unit/podcasts/golden/one_off_prompts.json` byte for byte.

  It fails until T014 adds the tables and T018 adds `talk`. T096 later adds the series' API-level checks; otherwise it is not edited.
- [ ] T005 [P] Re-point the legacy pins through one helper, **before** any change to `backend/app/podcasts/prompts.py`:
  - create `backend/tests/unit/podcasts/legacy_talk_calls.py` with `legacy_standing_prompt(**arguments)` and `legacy_cue(**arguments)`. Today they call `build_standing_prompt(...)` and `render_cue(...)` exactly as the tests do now;
  - change `backend/tests/unit/podcasts/test_one_off_golden.py` (including its `--write` script) and `backend/tests/unit/podcasts/test_series_prompts.py` to call only these helpers;
  - do not edit `golden/one_off_prompts.json` or any expected string. The tests pass on today's code.

  T017 changes the helpers' bodies to build a `PromptContext` with `LegacyTalk()`. That is the only edit these pins ever get.
- [ ] T006 [P] Extend `backend/tests/unit/podcasts/test_catalog.py` (data-model §1.1–§1.4):
  - `EPISODE_STYLES` holds `conversation`, `balanced` and `presented`, in that order, with the labels and learner-facing descriptions of §1.1 and the weights react/explain/story **0.90/0.07/0.03**, **0.55/0.30/0.15** and **0.35/0.40/0.25**; `DEFAULT_EPISODE_STYLE == "balanced"`;
  - `HOST_LINE_LENGTHS` holds `short` (1–2, "in one or two sentences"), `medium` (3–5, "in three to five sentences") and `long` (5–8, "in five to eight sentences"); `DEFAULT_HOST_LINE_LENGTH == "medium"`;
  - `INVITE_FREQUENCIES` holds `often` (1.0, 1.0, 1.0), `sometimes` (0.35, 0.45, 0.55) and `rarely` (0.0, 0.05, 0.10); `DEFAULT_INVITE_FREQUENCY == "sometimes"`; `INVITE_DEADLINE == 4`;
  - each catalogue is a `MappingProxyType`;
  - validation: an `EpisodeStyle` whose weights are not all positive or do not sum to 1 raises `ValueError`; a `HostLineLength` with `min_sentences < 1` or `min_sentences > max_sentences` raises; an `InviteFrequency` hazard outside [0, 1] raises;
  - the constants `TODAY_SUBJECT_MAX_LENGTH == 120`, `SERIES_SETTING_NAMES == ("format", "length", "style", "line_length", "invite_frequency", "learner_role")`, `ANSWER_INTENTS == ("answer", "follow_up")`, `DISCUSSION_INTENTS == ("react", "explain", "story")`, `QUESTION_MARK == "?"`, `MIN_SENTENCE_CHARACTERS == 12`, `PART_WAIT_SECONDS == 30` and `PART_TTL_SECONDS == 600`;
  - every intent in `ANSWER_INTENTS + DISCUSSION_INTENTS` fits `podcast_host_lines.intent` (≤ 10 characters).
- [ ] T007 [P] Extend `backend/tests/unit/test_database.py` (data-model §2.1–§2.3). After `init_db()`:
  - `podcast_episode_settings` has exactly: `conversation_id` Integer PK and FK to `podcast_episodes.conversation_id` **ON DELETE CASCADE**; `style` String(14) not null; `line_length` String(8) not null; `invite_frequency` String(10) not null; `today_subject` String(120) **nullable**; `covered_personality` String(30) **nullable**;
  - `podcast_series_settings` has exactly: `series_id` Integer PK and FK to `podcast_series.id` **ON DELETE CASCADE**; `format` String(12), `length` String(8), `style` String(14), `line_length` String(8), `invite_frequency` String(10), `learner_role` String(12) and `updated_at` DateTime(tz), all not null;
  - `podcast_preferences` gains `last_style VARCHAR(14) NOT NULL DEFAULT 'balanced'`, `last_line_length VARCHAR(8) NOT NULL DEFAULT 'medium'` and `last_invite_frequency VARCHAR(10) NOT NULL DEFAULT 'sometimes'`;
  - running `init_db()` twice is idempotent.
- [ ] T008 [P] Write `backend/tests/unit/podcasts/test_episode_settings.py` (data-model §3.1):
  - `EpisodeSettings.defaults("guest")` is Balanced, Medium, Sometimes, role `guest`, with no subject and no covered personality;
  - `from_ids(style=…, line_length=…, invite_frequency=…, learner_role=…, today_subject=…, covered_personality=…)` resolves the catalogue entries, and raises `ValueError` naming the setting for an unknown id;
  - `summary()` of the defaults is exactly `"Balanced · Medium lines · Asked sometimes"`, and of Presented · Long · Rarely is `"Presented · Long lines · Asked rarely"`;
  - the value is frozen: assigning a field raises.
- [ ] T009 [P] Write the shared contract test `backend/tests/contract/service_interfaces/test_host_talk_contract.py` (research R1, LSP):
  - `HostTalk` is an ABC with exactly six abstract methods: `invites(run, format, rng)`, `discussion_intent(state, rng)`, `line_rules(label, languages)`, `speech_rules(prompt, level)`, `instruction(cue, cast, label)` and `closing(cue, label)`. The plan's three-argument `invites` is used; research R1's table omits `format`, which `LegacyTalk` needs;
  - one contract, parametrised over the implementations (today `[LegacyTalk()]`; T025 adds `ConfiguredTalk`):
    - `invites(INVITE_DEADLINE, format, rng)` is `True` for every speaking format;
    - `speech_rules(prompt, NATURAL)` returns `prompt` unchanged;
    - `line_rules(...)` and `closing(...)` return non-empty strings;
    - `discussion_intent(...)` returns a value that fits `podcast_host_lines.intent`;
  - `host_talk_for(None)` returns a `LegacyTalk`.
- [ ] T010 [P] Extend `backend/tests/unit/podcasts/test_sqlite_storage.py` (data-model §3.2):
  - `create_episode(NewEpisode(..., settings=EpisodeSettings(...)))` writes one `podcast_episode_settings` row with the given ids, subject and covered personality;
  - `create_episode` with `settings=None` writes no row;
  - a failure forced after the settings insert rolls back the conversation, the episode, the hosts and the settings row together;
  - `get_episode` returns `settings` equal to what was written, or `None` when there is no row;
  - deleting the `podcast_episodes` row cascades its settings row.

  `backend/tests/contract/service_interfaces/test_podcast_storage_provider.py` stays unedited: `PodcastStorage` gains no abstract method.
- [ ] T011 [P] Update the policy test helpers in `backend/tests/unit/podcasts/test_turn_policy.py` and `backend/tests/unit/podcasts/test_turn_policy_properties.py`, so every `EpisodeState` they build carries `talk=LegacyTalk()`. Change no expectation. Add one test with a spy `HostTalk` asserting that `TurnPolicy` asks `state.talk.invites(...)` for invitations and `state.talk.discussion_intent(...)` for discussion lines, while `open`, `greet`, `wrap_up` and `sign_off` keep their own rules (wrap-up invites in a speaking format; sign-off never invites).
- [ ] T012 [P] Extend `backend/tests/unit/services/test_scripted_line_writer.py` for streaming:
  - `ScriptedLineWriter.script_tokens(["Hola a ", "todos. Hoy ", "hablamos."])` makes the next reply yield exactly those tokens in order;
  - `fail_after_tokens(2, error)` yields two tokens and then raises `error`;
  - a reply yields its line as one token when no split is scripted, as today.

### Implementation for the foundation

- [ ] T013 Add the catalogues and constants to `backend/app/podcasts/catalog.py` (data-model §1.1–§1.4): frozen dataclasses `EpisodeStyle` (`style_id`, `label`, `description`, `weights` for react/explain/story, validated in `__post_init__`), `HostLineLength` (`line_length_id`, `label`, `min_sentences`, `max_sentences`, `cue_phrase`, validated) and `InviteFrequency` (`invite_frequency_id`, `label`, `hazards`, validated); `EPISODE_STYLES`, `HOST_LINE_LENGTHS` and `INVITE_FREQUENCIES` as `MappingProxyType`s in display order; the `DEFAULT_…` constants; `INVITE_DEADLINE` and the §1.4 constants. Makes T006 green.
- [ ] T014 Add `PodcastEpisodeSettings` and `PodcastSeriesSettings` to `backend/app/podcasts/models.py` with the exact columns of T007, and the three `last_…` columns to `PodcastPreferences`. Add the three `("podcast_preferences", "last_style VARCHAR(14) NOT NULL DEFAULT 'balanced'")`-style entries to `_ADDITIVE_COLUMNS` in `backend/app/database.py`. Makes T007 green, and T004 as far as the tables.
- [ ] T015 [P] Create `backend/app/podcasts/services/episode_settings.py` with the frozen `EpisodeSettings` value: `defaults(learner_role)`, `from_ids(...)` raising `ValueError` on an unknown id, and `summary()` built from the catalogue labels ("{Style} · {Lines} lines · Asked {frequency in lower case}"). Makes T008 green.
- [ ] T016 Create `backend/app/podcasts/services/host_talk.py`:
  - the `HostTalk` ABC with the six methods of T009;
  - `LegacyTalk`, a **pure move** of today's behaviour: `_line_rules` from `prompts.py`; the One host "always invite" rule and Panel's hazards (0.25, 0.45, 0.60) with deadline 4 from `turn_policy.py`; `discuss` as the discussion intent; `with_partner_speech_rules` as `speech_rules`; today's cue instructions and closing sentences from `prompts.py`. Copy the hazards into a named constant (`LEGACY_PANEL_HAZARDS`);
  - `host_talk_for(settings)`, which returns `LegacyTalk()`. T043 adds the configured branch, test first.

  Makes T009 green.
- [ ] T017 Refactor `backend/app/podcasts/prompts.py` onto `HostTalk` (plan.md § Function-length plan):
  - add the frozen `PromptContext` (show, cast, label, languages, level, series, talk);
  - `build_standing_prompt(context)`: sections from the context, line rules from `talk.line_rules`, level block from `talk.speech_rules` (≈ 14 lines);
  - `render_cue` / `_instruction`: the closing from `talk.closing(cue, label)`, and unknown intents from `talk.instruction(...)`;
  - update every caller in `backend/app/podcasts/` to the new signature;
  - change the bodies of `backend/tests/unit/podcasts/legacy_talk_calls.py` (T005) to build a `PromptContext` with `talk=LegacyTalk()`.

  T005's pins must pass with no expected text changed.
- [ ] T018 Thread `talk` through the episode in `backend/app/podcasts/services/turn_policy.py`, `backend/app/podcasts/services/episodes.py` and `backend/app/podcasts/services/cues.py`:
  - `EpisodeState` gains `talk: HostTalk`;
  - `LoadedEpisode.state` sets it with `host_talk_for(record.settings)` (≈ 10 lines);
  - `LoadedEpisode.standing_prompt` builds a `PromptContext` (≈ 6 lines);
  - `TurnPolicy._invites` asks `state.talk.invites(run, format, self._rng)` and keeps Panel's balance rule; `_intent` becomes a method so it can pass the policy's `rng` to `state.talk.discussion_intent(state, rng)`;
  - `episode_history` / `next_turn_history` pass `talk` through to `render_cue`.

  Makes T011 green; T004 is now fully green.
- [ ] T019 Add `settings: EpisodeSettings | None` to `EpisodeRecord` and `NewEpisode` in `backend/app/podcasts/services/storage.py`. In `backend/app/podcasts/services/sqlite_storage.py`:
  - `create_episode` inserts the settings row in its existing transaction when `settings` is set (≈ 17 lines);
  - `get_episode` left-joins the row;
  - first move `_episode_record`'s scalar fields into `_record_fields(row)`, then add `settings=_settings_of(row)` (≈ 14 lines).

  Every caller passes `settings=None` for now. Makes T010 green.
- [ ] T020 [P] Extend `backend/tests/support/scripted_line_writer.py` with `script_tokens(tokens)` and `fail_after_tokens(count, error)` on `ScriptedLineWriter`, read by `ScriptedLineSession.reply` and `reply_to_opening`. Makes T012 green.
- [ ] T021 [P] Add the 011 types and fixtures to the frontend:
  - in `frontend/src/services/podcastsApi.ts`, **types only**: `EpisodeSettings`, `EpisodeOptions`, `SeriesUsualSettings`, `GuestDraft`, `LineStartedEvent`, `LinePartEvent`, the optional `stream_id` on the error event, `settings` / `away_host_name` on the episode, `is_guest` on a host, and `has_jump_in` / `has_pass` on a format;
  - in `frontend/e2e/fixtures.ts`: `episodeOptions` (contracts §1), `seriesWithSettings` (contracts §6, with `usual_settings`, `is_standard` and `second_role_personality_id`), `guestDraft` (a `HostDraftModel` for "Marco", Expert), and `streamedLineFrames(parts)`, which builds the contracts §4 SSE body: `line_started`, one `line_part` per text with `audio_url` `/api/podcasts/episodes/{id}/parts/{stream_id}/{n}`, then `line` (content = the parts joined by single spaces) and `done`.

  `npm run lint` and `npm run build` pass.
- [ ] T022 Foundation checkpoint:
  - run the full backend suite, ruff and black, plus `npm run lint`, `npm test -- --run` and `npm run test:e2e`;
  - `git diff 28ab4c7 -- backend/tests/unit/podcasts/golden/one_off_prompts.json` is empty, and no expected string in `test_series_prompts.py` has changed.

**Checkpoint**: foundation ready. Every episode still runs on `LegacyTalk`, and nothing the learner sees has changed.

---

## Phase 3: User Story 1 - Hosts talk like podcast hosts, at the learner's level (Priority: P1) 🎯 MVP

**Goal**: every new episode runs on `ConfiguredTalk` with the defaults (Balanced · Medium · Sometimes):
- lines of three to five sentences, each within the level's sentence limits;
- not every line invites;
- questions get answered;
- some lines explain or tell;
- One host covers the second host's role, and the learner can Jump in;
- long lines start playing as fast as short ones.

**Independent Test**: at Beginner, play a Medium One host episode of Big Little Questions with the
defaults:
- host lines are several sentences long, and each stays within the Beginner limits;
- not every line asks the learner something;
- a question the learner asks is answered in the next host line;
- some lines explain or tell.

Pre-feature episodes resume unchanged.

### Tests for User Story 1 (write first, see them fail)

- [ ] T023 [P] [US1] Extend `backend/tests/unit/conversation_levels/test_rules.py` (FR-001, R2):
  - `with_sentence_rules(prompt, NATURAL)` returns `prompt` unchanged;
  - at Beginner, Elementary and Intermediate, the block has no `Say at most` line, and keeps the per-sentence word limit, the joining rule, tenses, vocabulary, idioms, the "Questions to the learner" line and the four behaviour lines, in the same wording as `with_partner_speech_rules`;
  - `with_partner_speech_rules` output is unchanged; the existing tests pin it and are not edited;
  - `with_sentence_rules` is in `app.conversation_levels.__all__`.
- [ ] T024 [P] [US1] Pin the format flags (R15, data-model §1.5): in `backend/tests/unit/podcasts/test_catalog.py`, `one_host` has `has_jump_in=True, has_pass=False`, `panel` has `True, True`, and `listen` has `False, False`. In `backend/tests/contract/test_podcasts_catalog_api.py`, every `formats` entry of `GET /api/podcasts/catalog` carries `has_jump_in` and `has_pass` with those values.
- [ ] T025 [P] [US1] Write `backend/tests/unit/podcasts/test_host_talk.py` for `ConfiguredTalk` (R2–R6), and add `ConfiguredTalk(EpisodeSettings.defaults("guest"))` to the parametrisation of `backend/tests/contract/service_interfaces/test_host_talk_contract.py`:
  - `host_talk_for(settings)` returns a `ConfiguredTalk` for any `EpisodeSettings`;
  - `line_rules` states "Each host line has three to five sentences unless the producer note says otherwise; every sentence follows the rules at the end" for Medium (and the Short and Long counts), "When {label} asks a question, answer it first; never answer only with a question." and "Only ask {label} something when the producer note says so.", and no longer says "Keep each line to a few sentences";
  - `speech_rules` equals `with_sentence_rules(prompt, level)`;
  - `instruction` for `react`, `explain`, `story`, `answer` and `follow_up` gives the R4 wording, each with the episode's cue phrase ("in three to five sentences");
  - `closing` is "End by asking {label} a question." (or the settle variant) when the cue invites, and exactly "Don't ask {label} anything this time." when it does not;
  - with `covered_personality="expert"` in One host, the extra section is "This show usually has a second host, the Expert: {description}. Today you play that part too: {speaking_style}"; it is absent in Panel and Listen, and when `covered_personality` is `None`.
- [ ] T026 [P] [US1] Write `backend/tests/unit/podcasts/test_configured_golden.py`, modelled on `test_one_off_golden.py`, with a `--write` script and the golden file `backend/tests/unit/podcasts/golden/configured_prompts.json`:
  - cases: `build_standing_prompt` for a configured one-off with the default settings in `one_host` (with a covered Expert), `panel` and `listen`, at Natural and at Beginner; `render_cue` for every configured intent (`open`, `greet`, `react`, `explain`, `story`, `answer`, `follow_up`, `wrap_up`, `sign_off`), each inviting and not inviting where both apply;
  - until T056 writes the JSON, the test asserts only structure, so it fails today: the Medium count sentence is present, `Say at most` is absent, and the non-inviting cue ends "Don't ask {label} anything this time.";
  - bounds (contracts §9), with the token estimate the existing budget test in `test_prompts.py` uses: a configured standing prompt with a full series section is ≤ 900 tokens, and every cue is ≤ 60 tokens.
- [ ] T027 [P] [US1] Extend the policy tests for configured talk (FR-003, FR-005, FR-006, SC-005, R3, R4), all seeded:
  - in `backend/tests/unit/podcasts/test_turn_policy_properties.py`, over 10,000 simulated runs per `InviteFrequency` in One host and in Panel: the share of inviting host lines (before wrap-up) is 1.0 for `often`, in [0.40, 0.50] for `sometimes` and in [0.22, 0.30] for `rarely`; there are never five host lines in a row without an invitation; a sign-off never invites; Listen never invites;
  - over 10,000 Style draws per style, the react/explain/story shares are each within ±0.02 of the catalogue weights;
  - in `backend/tests/unit/podcasts/test_turn_policy.py`:
    - a learner line containing `?` makes the next discussion intent `answer`, whatever the draw;
    - a learner line with two or more `?`, followed by one `answer` host line, makes the next one `follow_up`;
    - Panel's balance rule still applies under configured talk;
    - `turn_actions` gives `can_jump_in=True, can_pass=False` at One host's Continue, and `True, True` in Panel;
  - the existing legacy expectations stay unedited.
- [ ] T028 [P] [US1] Extend `backend/tests/unit/services/conversation/test_pool.py` and `backend/tests/unit/services/conversation/test_engine.py` (R13.1):
  - `run_turn_live` yields each token as the session produces it, before the reply has finished (use a gated session);
  - it holds the key's lock for the generator's life: a second turn on the same key waits until the first generator is exhausted or closed;
  - a retryable error before the first token retries once on a rebuilt session, like `_reply_with_one_retry`;
  - an error after the first token finishes the turn as incomplete (the next turn rebuilds the session from saved history) and is raised;
  - closing the generator early finishes the turn as incomplete;
  - `run_turn` behaviour is unchanged;
  - `ConversationEngine.stream_live(provider, request)` delegates to `run_turn_live`.
- [ ] T029 [P] [US1] Write `backend/tests/unit/conversation_turns/test_streaming.py` (R13.2), and add `iterate_in_thread` to the expected surface in `backend/tests/unit/conversation_turns/test_public_surface.py`:
  - `iterate_in_thread(make_iterator)` yields the sync iterator's items in order to an `async for`;
  - an exception raised by the iterator is re-raised in the async caller;
  - `aclose()` on the async iterator closes the sync one, and the sync generator's `finally` runs on the worker thread, not the event loop's.
- [ ] T030 [P] [US1] Write `backend/tests/unit/podcasts/test_sentences.py` for `SentenceSplitter` (R13.3):
  - boundaries after `.`, `!`, `?` and `…`, with or without a closing quote or bracket, when followed by whitespace and an upper-case letter, a digit, `¿`, `¡` or an opening quote;
  - a newline is always a boundary;
  - no boundary inside "3.5" or "¿Sí? sí", or before a lower-case word;
  - a sentence shorter than `MIN_SENTENCE_CHARACTERS` joins the next ("Sr. Pérez llega." stays one sentence);
  - `flush()` returns the remainder, or `""`;
  - property (seeded): for random multi-sentence texts in the three practice languages' scripts, feeding any random split of tokens gives the same sentences as feeding the whole text at once.
- [ ] T031 [P] [US1] Extend `backend/tests/unit/podcasts/test_sanitiser.py` for `StreamingSanitiser` (R13.4):
  - the first sentence has its own speaker label stripped;
  - every sentence has stage directions removed;
  - a sentence starting with another speaker's label returns `SentenceVerdict(text, is_cut=True)`, drops the rest, and sets `was_trimmed`;
  - property (seeded): for random lines and random token splits, the kept sentences joined by spaces equal `LineSanitiser.clean` on the whole text, ignoring whitespace.
- [ ] T032 [P] [US1] Write `backend/tests/unit/podcasts/test_line_writer.py` for `LineWriter`, using `ScriptedLineWriter` token splits (T020):
  - it yields one part per kept sentence, as soon as each sentence completes;
  - the final line equals the parts' texts joined by single spaces;
  - a line cut or empty before its first kept sentence is retried, up to `LINE_WRITING_ATTEMPTS`, with nothing yielded first;
  - an `LLMError` before any part keeps 007's behaviour (retry once if retryable, then raise);
  - an error after a part raises a mid-line error carrying the line's `stream_id`.
- [ ] T033 [P] [US1] Write `backend/tests/unit/podcasts/test_spoken_parts.py` for `SpokenParts`, with `backend/tests/support/fake_speech.py`, `backend/tests/support/synchronous_executor.py` and an injected clock (R13.5–R13.6):
  - `begin(stream_id, voice_key, language)` then `add(stream_id, text)` returns `LinePart(stream_id, index, text, audio_url)` with indexes 0, 1, 2… and `audio_url` `/api/podcasts/episodes/{id}/parts/{stream_id}/{index}`;
  - parts are synthesised in order on one worker into `tts_cache/parts/{stream_id}-{n}.wav`;
  - `audio(stream_id, index, timeout)` returns the part's path once ready, raises a timeout error after `timeout`, and raises a not-found error for an unknown stream or index;
  - `assemble(stream_id, message_id)` joins the parts with the standard-library `wave` module into `tts_cache/{message_id}.wav`: the frame count is the sum of the parts' frames, and the format is the parts' format;
  - with the voice missing, `add` returns `audio_url=None`, nothing is synthesised, and `assemble` returns `None`;
  - `discard(stream_id)` removes the parts, and a stream expires `PART_TTL_SECONDS` after its line ends.
- [ ] T034 [P] [US1] Extend `backend/tests/unit/test_module_boundaries.py`: `app.podcasts.services.spoken_parts` is importable (so the test fails until T052), and the factory is the only module outside `app.podcasts` that imports it.
- [ ] T035 [P] [US1] Write `backend/tests/contract/test_podcast_line_parts_api.py` (contracts §4):
  - `POST /episodes/{id}/next` streams `line_started {stream_id, host_id}`, then one `line_part {stream_id, index, text, audio_url}` per sentence, then `line` and `done`, in that order;
  - the `line` frame's `content` is exactly the parts' texts joined by single spaces;
  - `GET /api/podcasts/episodes/{id}/parts/{stream_id}/{index}` returns 200 `audio/wav`;
  - it returns 404 "That part of the line isn't there any more." for an unknown part, an expired stream, or another episode's stream;
  - it returns 504 "The line's audio took too long. Press Replay when the line has arrived." when the part is not ready in time (inject a short wait);
  - it returns 503 with 007's host voice message when the voice became unavailable;
  - `done` carries `can_jump_in=True, can_pass=False` at a configured One host Continue.
- [ ] T036 [P] [US1] Write `backend/tests/integration/podcasts/test_streamed_lines.py` (FR-002a, R13):
  - every `line_part` frame arrives before the `line` frame;
  - each part's audio is served;
  - after `line`, `GET /api/audio/tts/{message_id}` returns the joined WAV at once, and the host line was not synthesised a second time (`schedule_speech` is not called for host lines);
  - an error after the second part sends `{"error": "The host lost their words. Press Retry.", "stream_id": …}`, stores no message and no host line, ends the engine session, and discards the parts;
  - with the host's voice missing, every `audio_url` is `null` and the line is stored as text (007 FR-031);
  - a **legacy** episode (seeded without a settings row) streams too, and its stored line equals what the batched path would have stored.
- [ ] T037 [P] [US1] Write `backend/tests/integration/podcasts/test_configured_talk.py` (FR-001–FR-007, FR-026):
  - a new one-off One host episode stores a settings row with the defaults, the show's role and `covered_personality` = the draft's second host's personality;
  - a new series One host episode stores `covered_personality` = the series' second host's personality;
  - a new Panel or Listen episode stores `covered_personality` NULL;
  - the session's standing prompt has the Medium count and the covered-role sentence, and no `Say at most`;
  - with a seeded policy, some host lines carry the "Don't ask" closing and the learner is invited by the fourth host line at the latest;
  - while One host has the floor, `POST /episodes/{id}/message` is accepted (Jump in);
  - after a learner line with `?`, the next host line is stored with intent `answer`;
  - a legacy One host episode, seeded without a settings row, still invites on every line and stores `discuss`.
- [ ] T038 [US1] Move the legacy expectations in the existing podcast integration tests onto legacy episodes. Some tests start new episodes and assert 007 cue text, One host invitations on every line, or `discuss` intents. They are in `backend/tests/integration/podcasts/test_one_host_episode.py`, `test_panel_episode.py`, `test_listen_episode.py`, `test_episode_lines.py`, `test_episode_resume.py` and any other file found by `grep -l "discuss\|End by asking" backend/tests/integration/podcasts/`:
  - add `legacy_episode(...)` to `backend/tests/support/podcast_harness.py`, which seeds an episode without a settings row;
  - switch each legacy assertion to an episode built with it, keeping the expected text unchanged;
  - keep the remaining assertions on new episodes, updated only where configured talk is the point (T037 covers configured behaviour).

  These tests must pass at T040's end.
- [ ] T039 [P] [US1] Write the Vitest tests for the arriving line:
  - `frontend/src/hooks/podcasts/episodeState.test.ts`: `line_started` creates an `arriving` line for the host; each `line_part` appends its text; `line` replaces `arriving` with the stored line; an error with a `stream_id` drops `arriving`;
  - `frontend/src/hooks/podcasts/usePartQueue.test.ts`: parts play in index order, the next part waits for the current one to end, a part that arrives late plays when it arrives, and `stop()` halts playback and clears the queue;
  - `frontend/src/components/podcasts/HostLine.test.tsx` and `frontend/src/components/podcasts/ArrivingLine.test.tsx`: the arriving line renders its sentences with `aria-busy="true"`, and shows no Replay or Slower until the `line` arrives; in Listen with Show text off it is hidden like any line;
  - `frontend/src/hooks/podcasts/usePodcastEpisode.test.tsx`: `onLineStarted` and `onLinePart` reach the state, and `useEpisodeAudio` does not auto-play a streamed line again when its `line` frame arrives;
  - `frontend/src/services/podcastsApi.test.ts`: the SSE parser hands `line_started`, `line_part` and an error with `stream_id` to their handlers.
- [ ] T040 [P] [US1] Extend `frontend/e2e/podcast-episode.spec.ts` with `streamedLineFrames` (T021):
  - streamed parts are requested and played in index order, and the text appears sentence by sentence;
  - Replay and Slower appear after the `line` frame, and Replay requests `GET /api/audio/tts/{message_id}`;
  - an error frame with a `stream_id` mid-line removes the arriving line, stops its audio, and shows "The host lost their words. Press Retry.";
  - in One host, Jump in is offered at Continue when `can_jump_in` is true, and Pass is not;
  - in Listen with Show text off, the arriving line's words stay hidden.

### Implementation for User Story 1

- [ ] T041 [P] [US1] Add `with_sentence_rules(prompt, level)` to `backend/app/conversation_levels/rules.py` and export it from `backend/app/conversation_levels/__init__.py`. Refactor `_partner_speech_block` into `(precedence, cap_line, *_sentence_lines(limits))` and have the new `_sentence_block` reuse `_sentence_lines`, so the partner block stays byte-identical (≈ 8 lines). Makes T023 green.
- [ ] T042 [US1] Give `PodcastFormat` `has_pass` in `backend/app/podcasts/catalog.py` and set One host's `has_jump_in` to true (data-model §1.5). `turn_actions` in `backend/app/podcasts/services/episodes.py` gives `can_pass` from `has_pass`. `_check_pass` in `backend/app/podcasts/routes.py` reads `has_pass`, and `_check_message` keeps reading `has_jump_in`. Add both flags to the format model in `backend/app/podcasts/schemas.py` and to the catalogue in `backend/app/podcasts/responses.py`. Makes T024 green.
- [ ] T043 [US1] Implement `ConfiguredTalk(settings)` in `backend/app/podcasts/services/host_talk.py`, and make `host_talk_for` return it for any non-None settings:
  - `invites(run, format, rng)`: the episode's `InviteFrequency` hazard for runs 1–3, always at `INVITE_DEADLINE`;
  - `discussion_intent(state, rng)`: `answer` if the learner's last line contains `QUESTION_MARK`; else `follow_up` if that line had two or more and the one host line since was `answer`; else a draw of `react` / `explain` / `story` by the Style's weights;
  - `line_rules`, `speech_rules`, `instruction` and `closing` with the T025 wording and the cue phrase from `HostLineLength`;
  - the covered-role section for One host.

  If `EpisodeState` does not already hold the learner's last line and the intent of the host line since, add `last_learner_line: str | None` and `last_host_intent: str | None`, filled by `LoadedEpisode.state` from stored history. Makes T025 green.
- [ ] T044 [US1] Render configured sections in `backend/app/podcasts/prompts.py`: the covered-role sentence after the hosts section in One host (R5 order: language, show, hosts, covered role, series, line rules, level sentence rules), through `talk` rather than a branch on settings. Keep `_show_section` and `_line_rules` within the plan's lengths.
- [ ] T045 [US1] Finish the policy in `backend/app/podcasts/services/turn_policy.py` for configured talk: the 4th-line deadline in every speaking format, wrap-up always inviting, sign-off never, Listen never, and Panel's `_gap_after` balance rule kept; `_intent` (≈ 13 lines) gives `answer` / `follow_up` priority through `state.talk.discussion_intent`. Makes T027 green.
- [ ] T046 [US1] Start every new episode on the defaults:
  - in `backend/app/podcasts/routes.py` (one-off), build `EpisodeSettings.defaults(show role)` with `covered_personality` = the draft's second host's personality in One host, and pass it as `NewEpisode.settings`;
  - in `backend/app/podcasts/services/series.py`, `SeriesService.new_episode` does the same with the series' second host's personality (≈ 19 lines), and `learner_role` comes from the settings;
  - in Panel and Listen, `covered_personality` is `None`.

  Together with T043–T045, this makes T037 green.
- [ ] T047 [P] [US1] Add `ConversationSessionPool.run_turn_live` in `backend/app/services/conversation/pool.py`, with `_first_token_with_one_retry`, each ≤ 20 lines, and `ConversationEngine.stream_live` in `backend/app/services/conversation/engine.py`. `run_turn` and `stream_turn` stay unchanged. Makes T028 green.
- [ ] T048 [P] [US1] Create `backend/app/conversation_turns/streaming.py` with `iterate_in_thread(make_iterator)`: the default executor, an `asyncio.Queue` fed with `loop.call_soon_threadsafe`, a sentinel for the end and for exceptions, and `aclose()` closing the sync iterator in its thread. Export it from `backend/app/conversation_turns/__init__.py`. Makes T029 green.
- [ ] T049 [P] [US1] Create `backend/app/podcasts/services/sentences.py` with `SentenceSplitter.feed(token) -> list[str]` and `flush() -> str`, using the boundary rules of T030 and `MIN_SENTENCE_CHARACTERS`. Use no abbreviation list and no per-language data. Makes T030 green.
- [ ] T050 [P] [US1] Add `StreamingSanitiser` and `SentenceVerdict(text, is_cut)` to `backend/app/podcasts/services/sanitiser.py`, wrapping `LineSanitiser`'s label and stage-direction rules and exposing `was_trimmed`. Makes T031 green.
- [ ] T051 [US1] Create `backend/app/podcasts/services/line_writer.py` with `LineWriter`: it consumes `engine.stream_live` through `iterate_in_thread`, splits tokens with `SentenceSplitter`, cleans each sentence with `StreamingSanitiser`, and yields kept sentences. It retries a line cut or empty before its first sentence (`_attempt`, `_kept_sentences`, each ≤ 20 lines; this is `EpisodeTurns._write_line` moved), and raises a mid-line error with the `stream_id` after a part. Depends on T047–T050. Makes T032 green.
- [ ] T052 [P] [US1] Create `backend/app/podcasts/services/spoken_parts.py` with `LinePart` and `SpokenParts` (`begin`, `add`, `audio`, `assemble`, `discard`, expiry after `PART_TTL_SECONDS`), taking the speech lookup, a single-worker executor and a clock through its constructor. Use the standard-library `wave` module to join the parts. Makes T033 green.
- [ ] T053 [US1] Wire the streaming pieces in `backend/app/services/factory.py`: `get_spoken_parts()`, process-wide like `MemoryCatchUps`, with its worker shut down where the app's other workers are; and a `LineWriter` and `SpokenParts` in `EpisodeDependencies`. No module outside `app.podcasts` other than the factory imports `spoken_parts`. Makes T034 green.
- [ ] T054 [US1] Stream host lines in `backend/app/podcasts/services/episode_turns.py`:
  - `_line_events` (≈ 18 lines) relays `line_started` and each `line_part` from `LineWriter`, adds each kept sentence to `SpokenParts`, and then stores the complete line;
  - `_assemble_audio(line, stream_id)` (≈ 8 lines, replacing `_speak`) calls `SpokenParts.assemble` and `set_tts_path`. `schedule_speech` is no longer called for host lines;
  - an error after a part ends the engine session, discards the parts, and sends `{"error": "The host lost their words. Press Retry.", "stream_id": …}`. Nothing is stored.

  This applies to every podcast host line, legacy included.
- [ ] T055 [US1] Add `GET /api/podcasts/episodes/{conversation_id}/parts/{stream_id}/{index}` to `backend/app/podcasts/routes.py`. It returns 200 `audio/wav` after waiting up to `PART_WAIT_SECONDS`, 404, 503 and 504, with the contracts §4 messages, and checks that the stream belongs to that episode. `_episode_turns` (≈ 18 lines) adds the `writer` and `spoken = Depends(get_spoken_parts)`. Makes T035 and T036 green.
- [ ] T056 [US1] Generate `backend/tests/unit/podcasts/golden/configured_prompts.json` with `python -m tests.unit.podcasts.test_configured_golden --write`. Review every entry against research R5 and the T025 wording. Then switch `test_configured_golden.py` to byte comparison, keeping its structural and budget assertions. Makes T026 green.
- [ ] T057 [P] [US1] Parse the new SSE events in `frontend/src/services/podcastsApi.ts`: `line_started`, `line_part`, and an error with `stream_id`, each passed to an optional handler (`onLineStarted`, `onLinePart`, `onLineLost`). Add a `partAudioUrl` helper. Old handlers are unchanged.
- [ ] T058 [US1] Add the `arriving` line (host, sentences so far, `stream_id`) to `frontend/src/hooks/podcasts/episodeState.ts`, with the `line_started`, `line_part`, `line` and lost-line transitions of T039. Then add `onLineStarted` and `onLinePart` to `streamHandlers` in `frontend/src/hooks/podcasts/usePodcastEpisode.ts` (≈ 10 lines).
- [ ] T059 [US1] Create `frontend/src/hooks/podcasts/usePartQueue.ts`, which plays `audio_url`s in index order and offers `stop()`. Use it from `frontend/src/hooks/podcasts/useEpisodeAudio.ts` (≤ 20 lines per function). `useNewLineSpeech` skips lines that were streamed, so a streamed line is not played twice.
- [ ] T060 [US1] Create `frontend/src/components/podcasts/ArrivingLine.tsx` (sentences so far, `aria-busy="true"`, announced once complete). Render it from `frontend/src/components/podcasts/EpisodeTranscript.tsx` and `frontend/src/components/podcasts/HostLine.tsx`. Replay and Slower stay absent until the `line` arrives, and Listen with Show text off hides it through `HiddenLine.tsx`. Makes T039 green.
- [ ] T061 [US1] Make the episode screen's actions follow the server's flags: `frontend/src/components/podcasts/EpisodeControls.tsx` (and `TurnBanner.tsx` if it names the action) offers Jump in whenever `can_jump_in`, and Pass only when `can_pass`, so One host gets Jump in without Pass. The lost-line message shows through `EpisodeError.tsx` with Retry. Makes T040 green.
- [ ] T062 [US1] Write the hand-run benchmarks (`@pytest.mark.benchmark`):
  - create `backend/tests/integration/podcasts/test_host_talk_benchmark.py`: 20 Medium One host Beginner episodes of Big Little Questions with the defaults, on the selected local model. Episodes are created through the harness with `NewEpisode.settings`, so US2's API is not needed. Each episode includes scripted learner questions. It prints the median sentences per discussion line, the inviting share, the share of sentences within 8 words, the share of present-tense sentences (using the level benchmark's tense check), the intent counts, and the question/answer transcripts;
  - extend `backend/tests/integration/podcasts/test_podcast_latency_benchmark.py` to measure, after Continue, the time to the first `line_part`'s audio being ready, for Short, Medium and Long lines (p90 each), and to record `prompt_eval_count` at the end of a Long-episode, Long-lines run (R18).
- [ ] T063 [US1] Run T062 on `llama3.1:8b`: `backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k "host_talk or latency"`. Create `specs/011-configurable-podcast-shows/talk-review-sheet.md` and record SC-001, SC-002, SC-005, SC-011 and the R18 count, plus the SC-003 transcripts to review. If SC-011 misses (p90 > 5 s for any length), stop and report before US2. SC-001/SC-002 misses go to T131.
- [ ] T064 [US1] US1 checkpoint:
  - the full backend suite, ruff and black, plus `npm run lint`, `npm test -- --run` and `npm run test:e2e`;
  - the legacy golden diff of T022 is still empty;
  - quickstart §4 steps 1–4 by hand.

**Checkpoint**: the learner's complaint is fixed with no settings opened, and pre-feature episodes resume unchanged. This is the MVP.

---

## Phase 4: User Story 2 - Learner shapes an episode with a few settings (Priority: P1)

**Goal**: the setup screen offers Episode settings (Style, Host lines, How often you're asked, Your
role, Today's subject):
- closed by default, with a summary;
- remembered for one-offs (except Your role and Today's subject);
- validated on the server;
- frozen into each episode.

**Independent Test**: start one episode of a show with Presented · Long · Rarely and one with
Conversation · Short · Often. Check that:
- the first has longer lines, more explaining and fewer invitations;
- each keeps its settings when resumed;
- the next setup offers the last Style, Host lines and How often you're asked, with Your role on the
  show's own role.

### Tests for User Story 2 (write first, see them fail)

- [ ] T065 [P] [US2] Write `backend/tests/unit/podcasts/test_episode_settings_schemas.py` for `EpisodeSettingsModel` and the start request (contracts §3):
  - every field of `settings` is optional, and a missing one takes its default;
  - a request without `settings` validates;
  - `today_subject` is trimmed, newlines are folded to spaces, an empty value becomes `None`, and it may be at most `TODAY_SUBJECT_MAX_LENGTH` (120) characters;
  - an unknown `style`, `line_length` or `invite_frequency` id fails with "That {setting} isn't in the list. Pick one of the listed ones.";
  - a role outside `LEARNER_ROLES` fails with "Your role must be guest, co-host or caller.".
- [ ] T066 [P] [US2] Write `backend/tests/unit/podcasts/test_subject_check.py` for `SubjectCheck`, with `backend/tests/support/scripted_show_llm.py` or a scripted structured provider (R14):
  - it makes one structured call, with 007's suitability rule worded for a subject and the schema `{is_suitable, decline_reason}`;
  - a suitable subject passes;
  - an unsuitable one raises `SubjectDeclined`, with the reason logged and never in the raised message;
  - an `LLMError` propagates unchanged.
- [ ] T067 [P] [US2] Write `backend/tests/contract/test_podcast_episode_settings_api.py` (contracts §3, §5; data-model §5.1, §5.3):
  - `POST /api/podcasts/episodes` with `settings` → 201, and `EpisodeResponse.settings` carries the ids, the labels, the role and the subject;
  - without `settings`: Balanced · Medium · Sometimes and the show's role;
  - each §5.1 refusal returns 422 with its message;
  - a declined subject returns 422 "That subject can't be used for an episode. Change it or clear it, then start." and creates no conversation;
  - a `SubjectCheck` provider failure returns 503 with the provider's message and creates nothing;
  - with no subject, the structured provider is not called;
  - in Listen, `invite_frequency` and `learner_role` are stored as the default and the show's role, whatever was sent;
  - `GET` of a pre-feature episode returns `"settings": null`.
- [ ] T068 [P] [US2] Extend `backend/tests/contract/test_podcasts_catalog_api.py` and `backend/tests/contract/test_podcast_preferences_api.py`:
  - `GET /api/podcasts/catalog` returns `episode_options` exactly as contracts §1 shows (styles with descriptions and `is_default`, line lengths, invite frequencies, learner roles with labels, `today_subject_max_length: 120`);
  - `GET /api/podcasts/preferences` carries `last_style`, `last_line_length` and `last_invite_frequency`;
  - a `PUT` that includes them leaves them unchanged;
  - a one-off start writes them; a series start does not.
- [ ] T069 [P] [US2] Extend `backend/tests/unit/podcasts/test_prompts.py` (R5, plan interpretation 13):
  - with Today's subject set, the show section adds "Today's subject, chosen by {label}: {subject}. Talk about it within the show's topic.";
  - the learner's role in the show section is the episode's `learner_role`, not the show's;
  - in a series episode with a subject, the "choose a subject not in the covered list" rule becomes "Today's subject was chosen by {label}: talk about it even if it was covered before";
  - with no subject, the prompt is unchanged.
- [ ] T070 [P] [US2] Write `backend/tests/integration/podcasts/test_episode_settings.py` (FR-012, FR-013, US2 acceptance):
  - an episode started with Presented · Long · Rarely resumes with the same prompt and cues after the preferences have changed to Conversation · Short · Often;
  - its prompt has the Long count, and its non-inviting cues have the "Don't ask" closing;
  - a one-off start updates the three `last_…` preferences; a series start leaves them unchanged;
  - the role and the subject are never remembered.
- [ ] T071 [P] [US2] Extend `backend/tests/unit/test_module_boundaries.py`: `app.podcasts.services.subject_check` is importable, and the factory is the only module outside `app.podcasts` that imports it.
- [ ] T072 [P] [US2] Write the Vitest tests:
  - `frontend/src/components/podcasts/EpisodeSettings.test.tsx`:
    - the toggle is a `button` with `aria-expanded="false"` and the name "Episode settings: Balanced · Medium lines · Asked sometimes";
    - the summary updates as choices change;
    - each of Style, Host lines, How often you're asked and Your role is a `radiogroup` with a legend;
    - in Listen, the last two are absent;
  - `frontend/src/components/podcasts/TodaySubjectField.test.tsx`: the textbox "Today's subject (optional)" has `maxlength=120` and a live character count;
  - `frontend/src/hooks/podcasts/useEpisodeSettingsForm.test.tsx`: it starts Style, Host lines and How often you're asked on the preferences' `last_…` values (or the defaults), Your role on the show's role, and Today's subject empty;
  - `frontend/src/hooks/podcasts/useSetupStart.test.tsx`: Start sends `settings`, and a 422 subject decline is shown beside the field without starting;
  - `frontend/src/pages/PodcastSetup.test.tsx`: Start remains the single primary action.
- [ ] T073 [P] [US2] Write `frontend/e2e/podcast-episode-settings.spec.ts` with `episodeOptions` (contracts §11):
  - the disclosure is closed with its summary;
  - starting with the defaults needs no opening (SC-008), and the request carries the defaults;
  - the last-used values are offered on the next setup, with Your role on the show's role;
  - Listen hides two settings;
  - a declined subject shows the plain message, and the episode does not start until the subject is changed or cleared;
  - one primary action.

### Implementation for User Story 2

- [ ] T074 [US2] Add the schemas to `backend/app/podcasts/schemas.py`: `EpisodeSettingsModel` (every field optional, `today_subject` normalised and ≤ 120 characters), `settings` on the start request, `EpisodeOptions` and its item models, the three read-only `PreferencesResponse` fields, and `settings` on `EpisodeResponse`. `PUT` preferences ignores the `last_…` fields. Makes T065 green.
- [ ] T075 [US2] Create `backend/app/podcasts/services/subject_check.py` with `SubjectCheck` (taking a `StructuredLLMProvider`) and `SubjectDeclined`. Add the subject-check prompt and reply schema to `backend/app/podcasts/prompts.py`. Makes T066 green.
- [ ] T076 [US2] Add `get_subject_check()` to `backend/app/services/factory.py`, built on the selected structured provider. Makes T071 green.
- [ ] T077 [US2] Accept settings on Start in `backend/app/podcasts/routes.py` (contracts §3's order of work):
  - move preparation, the subject check and the refusal mapping into `_prepared_start(...)`, bringing `start_episode` to ≈ 15 lines;
  - build `EpisodeSettings.from_ids(...)` from the request, normalised for Listen (the default frequency and the show's role), with T046's `covered_personality`;
  - run `SubjectCheck` only when a subject is set, mapping `SubjectDeclined` → 422 and `LLMError` → 503;
  - pass the settings to `SeriesService.new_episode` for series starts (`backend/app/podcasts/services/series.py`);
  - `_remember_start` (≈ 10 lines) writes the last-used values via `_last_used(req)` for one-off starts only.
- [ ] T078 [US2] Read and write the three preference columns in `backend/app/podcasts/services/storage.py` (the preferences record) and `backend/app/podcasts/services/sqlite_storage.py`.
- [ ] T079 [US2] Extend `backend/app/podcasts/responses.py`:
  - `episode_options` in the catalogue, from the three catalogues and `LEARNER_ROLES`;
  - `settings` with labels on `EpisodeResponse`, via `_settings_model(record)`; `episode_response` stays ≈ 16 lines;
  - the `last_…` fields on preferences.

  With T074–T078, this makes T067, T068 and T070 green.
- [ ] T080 [US2] Render Today's subject and the episode's role in `backend/app/podcasts/prompts.py`: `_subject_sentence(talk)` in `_show_section` (≈ 12 lines), and the series subject-rule replacement in `_series_section`. Makes T069 green.
- [ ] T081 [P] [US2] Extend `frontend/src/services/podcastsApi.ts`: `episode_options` on the catalogue, `settings` in the start body, the preference fields, and `settings` on the episode.
- [ ] T082 [US2] Create `frontend/src/hooks/podcasts/useEpisodeSettingsForm.ts`, which holds the settings state and summary and is initialised as in T072.
- [ ] T083 [US2] Create `frontend/src/components/podcasts/EpisodeSettings.tsx`, `StyleFieldset.tsx`, `HostLinesFieldset.tsx`, `AskedFieldset.tsx`, `RoleFieldset.tsx` and `TodaySubjectField.tsx`. Build the radio fieldsets like `FormatFieldset.tsx`, and the disclosure with `aria-expanded` and `aria-controls`. Labels and descriptions come from `episode_options`. Use design-system tokens only.
- [ ] T084 [US2] Put Episode settings on the setup screen:
  - move the format, length and name fields of `frontend/src/components/podcasts/SetupForm.tsx` into a new `SetupFields.tsx`, and add `<EpisodeSettings>` (≈ 17 lines);
  - `frontend/src/hooks/podcasts/useSetupForm.ts` delegates the settings to `useEpisodeSettingsForm`;
  - `frontend/src/hooks/podcasts/useSetupStart.ts` sends `settings` and shows a subject decline beside the field.

  Makes T072 and T073 green.
- [ ] T085 [US2] US2 checkpoint: the full suites (backend, `npm test -- --run`, `npm run test:e2e`), lint, and the US2 independent test by hand with two episodes.

**Checkpoint**: the learner can shape one-off episodes, and US1's defaults still apply when nothing is opened.

---

## Phase 5: User Story 3 - Learner changes a series' settings for one episode or from now on (Priority: P1)

**Goal**: every series has usual settings:
- set by episode 1;
- changed per setting for **Just this episode** or **This and later episodes**, with marks on the
  setup;
- resettable to the show's standard settings.

A One host series can bring the show's expert in for one episode by switching to Panel (an expert
guest, cast fresh), or for good (the stored second host, introduced as new).

**Independent Test**: in a series, change the format and the style for Just this episode and play
the episode; the next setup shows the series' previous settings. Then change the style for This and
later episodes; the next two episodes use it. The episode count and the memory are unaffected.

### Tests for User Story 3 (write first, see them fail)

- [ ] T086 [P] [US3] Write `backend/tests/unit/podcasts/test_series_settings.py` (data-model §3.3):
  - `SeriesSettings.standard(show)` is `one_host`, `medium`, `balanced`, `medium`, `sometimes` and the show's role;
  - `with_changes(values, names)` copies only the named fields, and raises `ValueError` for a name outside `SERIES_SETTING_NAMES`;
  - `is_standard_for(show)` is true for `standard(show)` and false after any change.
- [ ] T087 [P] [US3] Extend `backend/tests/unit/podcasts/test_sqlite_series_storage.py` and `backend/tests/contract/service_interfaces/test_series_storage_provider.py` (data-model §3.4):
  - `create(show_row_id, language, hosts, settings)` also inserts the settings row;
  - `get` and `find` fill `SeriesRecord.settings` from the row, or from `SeriesSettings.standard` when there is none;
  - `reset_settings(series_id)` deletes the row and returns `True`, also when no row existed, and returns `False` for an unknown series;
  - `hosts_present(series_id)` maps each series episode's conversation id to the `frozenset` of names in its `podcast_hosts`, in one query;
  - resetting the series (010) cascades the settings row;
  - `SeriesStorage`'s abstract methods are 010's set plus exactly `hosts_present` and `reset_settings`.
- [ ] T088 [P] [US3] Extend `backend/tests/unit/podcasts/test_sqlite_storage.py`: `NewSeriesLink.settings_update` upserts the series settings row in `create_episode`'s transaction, with `updated_at` set. A failure forced after the upsert leaves the series settings, the link and the episode all unwritten.
- [ ] T089 [P] [US3] Extend `backend/tests/unit/podcasts/test_series_service.py` (data-model §5.2, plan interpretations 3–7):
  - **episode 1**: `settings_update` is the full set from the episode's choices, and `from_now_on` is ignored;
  - **later episodes**:
    - only the `from_now_on` names are updated, each to this episode's value;
    - an empty `from_now_on` gives no update;
    - a name outside `SERIES_SETTING_NAMES` fails 422 "That setting can't be kept for later episodes.";
  - a one-off with a non-empty `from_now_on` fails 422 "Only a series keeps settings for later episodes.";
  - **guest checks** (shared with US4): a guest on episode 1 fails 422 "A guest can join from the second episode."; a guest in a slot the format does not use (`second` in `one_host`) fails 422 "That guest has no seat in this format. Pick Panel, or invite them in the host's place."; a guest named like any series host or the learner fails 422 "{name} is already a host of this show. Invite another guest." or the 010 name-clash message; an unknown personality or a voice that does not speak the language gives 007's host messages; a personality or voice equal to the other present host's gives 007's pair messages (voice only with two or more installed);
  - a valid second-slot guest in a Panel-this-episode switch becomes the episode's second host, with the snapshot's `guest_slot = "second"` and no away host;
  - **R12**: a series switched to Panel from now on brings in the stored second host, whose slot is in `new_host_slots` because `hosts_present` shows they were never in an episode.
- [ ] T090 [P] [US3] Extend `backend/tests/unit/podcasts/test_casting.py` for `HostCaster.cast_guest(slot, personality_id, present, avoid_names, language)` (R10):
  - the name is never a series host's (the away host's included), the learner's, or one in `avoid_names`;
  - the voice differs from the other present host's when two or more are installed;
  - the personality is the one given, or the show's second personality (`KeptShow.personalities[1]`) when none is given for the second slot of a One host series;
  - a personality equal to the other present host's is refused.
- [ ] T091 [P] [US3] Extend `backend/tests/unit/podcasts/test_series_values.py`: `SeriesSnapshot` round-trips `guest_slot`. A 010 snapshot JSON (no new keys) loads with `guest_slot is None`. `to_json` of a snapshot with no guest is byte-identical to 010's. `SeriesBrief.of` gives `guest_name` from the cast and `guest_slot`.
- [ ] T092 [P] [US3] Extend `backend/tests/unit/podcasts/test_series_prompts.py` with **new** tests only:
  - a second-slot guest is introduced in the series section as joining for this episode, without knowledge of earlier episodes;
  - the `open` cue names the guest as today's guest, and the `greet` cue has the guest introduce themself as today's guest;
  - a host in `new_host_slots` after a from-now-on switch to Panel is introduced as new to the show;
  - with no guest, every existing expectation is unchanged.
- [ ] T093 [P] [US3] Write the contract tests (contracts §3, §6–§8):
  - extend `backend/tests/contract/test_podcast_series_api.py`: `GET /api/podcasts/series/{id}` returns `usual_settings`, `is_standard` and `second_role_personality_id`, and each `SeriesHostModel` returns `has_taken_part`;
  - create `backend/tests/contract/test_podcast_series_settings_api.py`:
    - `DELETE /api/podcasts/series/{id}/settings` returns 200 with standard `usual_settings` and leaves the count, the hosts and the memory unchanged; 404 with 010's message for an unknown series; 422 `LANGUAGE_CHANGED` in another language;
    - `POST /api/podcasts/series/{id}/guest` returns 200 with a `HostDraftModel`; without `personality_id` on the second slot of a One host series it uses the show's second personality; `avoid_names` gives a new name; 404 for an unknown series; 422 for an unknown slot or personality, for "Hugo already has that personality. Pick another one.", and for a slot the `format` does not use; nothing is stored;
  - extend `backend/tests/contract/test_podcast_series_episodes_api.py`:
    - `from_now_on` and `guest` on `POST /episodes` with each §5.2 message;
    - a JSON array as `guest` fails 422 "Only one guest can join an episode.";
    - `EpisodeResponse.hosts[].is_guest` is true for the guest only.
- [ ] T094 [P] [US3] Write `backend/tests/integration/podcasts/test_series_settings.py` (FR-014–FR-019, SC-006):
  - episode 1 with Panel · Long · Presented sets the series' `usual_settings`;
  - a Just-this-episode Style change leaves the next `usual_settings` unchanged, and the next episode uses the usual Style;
  - a This-and-later Style change appears in the next **two** setups' `usual_settings`;
  - one start can mix both scopes;
  - an abandoned Just-this-episode episode leaves the next setup on the usual settings;
  - a setup left without starting changes nothing;
  - the episode count, the episode numbers and the memory read and write behave as for any series episode (FR-018);
  - the reset returns standard settings, and the past episodes' settings rows are unchanged;
  - an `es` series and a `de` series of the same show keep separate settings.
- [ ] T095 [P] [US3] Write `backend/tests/integration/podcasts/test_guest_episodes.py`, with the Panel-this-episode expert cases (FR-024a):
  - in a One host series, a Panel start for this episode with the cast expert guest stores the guest in the second slot, and the snapshot's `guest_slot = "second"` with no away host;
  - the series' hosts are unchanged, and the next episode's draft has the regular hosts only;
  - the count includes the guest episode;
  - a second Panel-this-episode episode casts afresh.

  US4 (T118) extends this file.
- [ ] T096 [P] [US3] Extend `backend/tests/integration/podcasts/test_configured_upgrade_preserves_data.py` (T004) with its API-level checks. `GET /api/podcasts/series/{id}` for the seeded pre-feature series returns standard `usual_settings` and `is_standard: true`, with its hosts, episode count and memory unchanged. Its next episode's prompt is configured, and its 010 snapshots still load. No other line of the test changes.
- [ ] T097 [P] [US3] Write the Vitest tests:
  - `frontend/src/hooks/podcasts/useSeriesScopes.test.ts`, covering the data-model §6.1 state machine:
    - the first change opens the question;
    - Just this episode → `this-episode`; This and later episodes → `from-now-on`;
    - Cancel or Escape reverts;
    - changing again keeps the scope; setting back to the usual value clears it;
    - `fromNowOn()` lists the names in `from-now-on`;
    - episode 1 asks nothing;
  - `frontend/src/components/podcasts/ScopeDialog.test.tsx`: an `alertdialog` "Change for which episodes?" with the two buttons; it traps focus, returns it to the changed control, and Escape reverts;
  - `frontend/src/components/podcasts/ScopeMark.test.tsx`: the legend text reads "this episode" or "from now on";
  - `frontend/src/components/podcasts/StandardSettingsButton.test.tsx`: shown only when `is_standard` is false; it opens `ConfirmDialog` and calls the reset;
  - `frontend/src/components/podcasts/GuestCard.test.tsx` and `frontend/src/hooks/podcasts/useGuest.test.tsx`: switching a One host series to Panel for Just this episode casts the expert guest (showing "Casting…" first), and the card reads "Guest · this episode" with **Another guest**, which re-casts with `avoid_names`;
  - `frontend/src/pages/PodcastSetup.test.tsx`: a series setup starts on `usual_settings`, not on the last-used preferences; a joining host reads "New to the show" from `has_taken_part`.
- [ ] T098 [P] [US3] Write `frontend/e2e/podcast-series-settings.spec.ts` with `seriesWithSettings` and `guestDraft`:
  - a scope question on the first change of each setting, and a mark per setting;
  - the request's `settings` and `from_now_on`;
  - the next setup after a Just-this-episode start shows the usual settings, and after a from-now-on start shows the change;
  - **Use the show's standard settings**, then confirm, sends `DELETE` and returns the setup to standard;
  - **SC-007**: from a One host series' setup, Panel → Just this episode → Start (three choices) starts an episode with the expert guest in the request's `guest`.

### Implementation for User Story 3

- [ ] T099 [P] [US3] Create `backend/app/podcasts/services/series_settings.py` with the frozen `SeriesSettings`: `standard(show)`, `with_changes(values, names)` and `is_standard_for(show)`. Makes T086 green.
- [ ] T100 [US3] Extend `backend/app/podcasts/services/series_storage.py` and `backend/app/podcasts/services/sqlite_series_storage.py`:
  - `SeriesRecord.settings`, filled via `_settings_record(...)` (`_series_record` ≈ 16 lines);
  - `create(..., settings)` inserts the row;
  - the new abstract methods `reset_settings` and `hosts_present`, and their SQLite implementations.

  Update `backend/tests/support/fake_series_storage.py` to match. Makes T087 green.
- [ ] T101 [US3] Add `settings_update: SeriesSettings | None` to `NewSeriesLink` in `backend/app/podcasts/services/storage.py`, and apply it as an upsert beside the link row in `SQLitePodcastStorage.create_episode` (`backend/app/podcasts/services/sqlite_storage.py`). Makes T088 green.
- [ ] T102 [P] [US3] Add `HostCaster.cast_guest(...)` to `backend/app/podcasts/services/casting.py`, reusing `_free_names` and a voice helper. `recast` is unchanged. Makes T090 green.
- [ ] T103 [P] [US3] Add `guest_slot: str | None = None` to `SeriesSnapshot`, and `guest_name` to `SeriesBrief`, in `backend/app/podcasts/services/series_snapshot.py`. Absent keys load as `None`, and `to_json` omits `None`. Makes T091 green.
- [ ] T104 [US3] Extend `SeriesService` in `backend/app/podcasts/services/series.py`:
  - `_series_start` (≈ 14 lines) resolves the episode's settings with `_series_settings(...)`, and builds `settings_update` (the full set on episode 1, `with_changes` for `from_now_on` later);
  - the §5.2 guest checks;
  - `_participating` (≈ 8 lines) puts the guest in its slot via `_with_guest`;
  - `_snapshot` (≈ 16 lines) sets `guest_slot`, and adds never-present hosts to `new_host_slots` from episode 2 via `_joining_slots(series, present)`.

  Makes T089 green.
- [ ] T105 [US3] Extend `backend/app/podcasts/schemas.py`:
  - `from_now_on: list[str] = []` and `guest: GuestModel | None = None` on the start request; an array `guest` fails with "Only one guest can join an episode.";
  - `GuestRequest` for the guest endpoint;
  - `usual_settings`, `is_standard` and `second_role_personality_id` on the series detail;
  - `has_taken_part` on `SeriesHostModel`;
  - `is_guest` on the episode host.
- [ ] T106 [US3] Render the second-slot guest in `backend/app/podcasts/prompts.py`: `_guest_lines(series)` in `_series_section` (≈ 18 lines), the `open` cue naming today's guest, and the `greet` cue for a second-slot guest (`_series_open` ≈ 13 lines). Legacy series sections stay byte-identical. Makes T092 green.
- [ ] T107 [US3] Add the endpoints and response fields:
  - in `backend/app/podcasts/series_routes.py`: `DELETE /api/podcasts/series/{series_id}/settings` and `POST /api/podcasts/series/{series_id}/guest`, with contracts §7–§8's statuses;
  - in `backend/app/podcasts/routes.py`: `from_now_on` and `guest` passed to `SeriesService.prepare`, and the one-off 422;
  - in `backend/app/podcasts/responses.py`: `series_detail` moves its host and memory fields into `_series_members(...)`, then gains `usual_settings`, `is_standard` and `second_role_personality_id` (≈ 18 lines); hosts gain `has_taken_part` from `hosts_present`; episode hosts gain `is_guest`.

  Makes T093–T096 green.
- [ ] T108 [P] [US3] Extend `frontend/src/services/podcastsApi.ts`: `resetSeriesSettings(seriesId)`, `castGuest(seriesId, request)`, `from_now_on` and `guest` in the start body, and the new series and host fields.
- [ ] T109 [US3] Create `frontend/src/hooks/podcasts/useSeriesScopes.ts`, `frontend/src/components/podcasts/ScopeDialog.tsx` (built like `ConfirmDialog`) and `frontend/src/components/podcasts/ScopeMark.tsx`. Show the marks in the legends of `FormatFieldset.tsx`, `LengthFieldset.tsx`, `StyleFieldset.tsx`, `HostLinesFieldset.tsx`, `AskedFieldset.tsx` and `RoleFieldset.tsx`.
- [ ] T110 [US3] Create `frontend/src/hooks/podcasts/useGuest.ts` (cast, Another guest) and `frontend/src/components/podcasts/GuestCard.tsx` ("Guest · this episode", **Another guest**, "Casting…"). In `frontend/src/components/podcasts/SetupHosts.tsx` / `SeriesHostCard.tsx`, casting the expert guest when a One host series turns Panel for Just this episode, and removing it when the format goes back. A joining regular host reads "New to the show" from `has_taken_part`.
- [ ] T111 [US3] Wire the series setup:
  - create `frontend/src/components/podcasts/StandardSettingsButton.tsx` (`ConfirmDialog`, then the reset);
  - `frontend/src/pages/PodcastSetup.tsx` passes `usual_settings` to the form;
  - `useSetupForm.ts` and `useEpisodeSettingsForm.ts` start a series setup on `usual_settings`;
  - `useSetupStart.ts` sends `from_now_on` (from `useSeriesScopes`) and `guest`.

  Makes T097 and T098 green.
- [ ] T112 [US3] US3 checkpoint: the full suites, lint, and quickstart §4 steps 5, 6 and 8 by hand.

**Checkpoint**: series keep usual settings, and each change is scoped. The expert joins for one episode in three choices (SC-007).

---

## Phase 6: User Story 4 - A guest host joins a series for one episode (Priority: P2)

**Goal**: in a series episode, the learner can invite a guest in either regular host's place:
- the regular host is "away";
- the guest is introduced as joining for today;
- the series' memory marks that episode's points as missed by the away host, who later speaks of them
  only as heard secondhand.

**Independent Test**: in a two-host series, invite a guest in place of the second host for one
episode. Check that:
- the guest is introduced as a guest, and the regular host is said to be away;
- the next episode returns to the regular host, who never claims to have been there;
- the count and the other host's memory include the guest episode.

### Tests for User Story 4 (write first, see them fail)

- [ ] T113 [P] [US4] Extend `backend/tests/unit/podcasts/test_series_values.py` (data-model §2.5, §3.5):
  - `RememberedLine(text, missed_by=())`;
  - `SeriesSnapshot.topics_covered` and `about_learner` are tuples of `RememberedLine`;
  - `to_json` writes unmarked points as plain strings and marked ones as `{"text": …, "missed_by": ["second"]}`;
  - `from_json` reads both forms, and every 010 snapshot loads with no marks;
  - `away_host_name` round-trips and is absent when `None`;
  - a snapshot with no marks, guest or away host is byte-identical to 010's;
  - `SeriesBrief.of` gives `away_host_name`, and `missed_names(line)` resolves the slots present in the cast to names.
- [ ] T114 [P] [US4] Extend `backend/tests/unit/podcasts/test_sqlite_series_storage.py`: `remembered(series_id)` returns `RememberedPoint`s with the `conversation_id` of the episode each came from (≈ 12 lines).
- [ ] T115 [P] [US4] Extend `backend/tests/unit/podcasts/test_series_service.py` (FR-020–FR-024, R10–R12):
  - a guest in the second slot of a Panel series replaces Clara: the snapshot's `guest_slot = "second"` and `away_host_name = "Clara"`;
  - a guest in the lead slot of a One host series replaces the one host (US4-6), with `away_host_name` = the lead's name;
  - the next episode's points from the guest episode carry `missed_by = ("second",)` while Clara is present;
  - two guest episodes in a row mark every point from both;
  - a second host joining a One host series from now on gets marks on every earlier point;
  - points from episodes the present hosts were all in stay unmarked;
  - a guest named like the away host is refused;
  - at most three people: a guest never adds a fourth seat.
- [ ] T116 [P] [US4] Extend `backend/tests/unit/podcasts/test_series_prompts.py` (new tests only) and `backend/tests/unit/podcasts/test_configured_golden.py`:
  - the away host is "away today", never "left the show";
  - the `open` cue names both the guest and the away host;
  - a lead-slot guest opens as standing in for the away host;
  - a marked point renders `- {text} [Clara was away for this]`, and the rule "Clara only heard about points marked [Clara was away]: Clara may mention them as something heard from the other host, never as having been there or having heard {label} say it." appears only when a mark is present;
  - add a configured series guest case to the golden test, with structure assertions first. Its file `backend/tests/unit/podcasts/golden/configured_series_guest_prompt.json` is written in T124.
- [ ] T117 [P] [US4] Extend `backend/tests/contract/test_podcast_series_episodes_api.py` and `backend/tests/contract/test_podcast_series_settings_api.py`:
  - a guest episode's `EpisodeResponse` has `is_guest: true` on the guest only, and `away_host_name: "Clara"`;
  - a Panel-this-episode expert episode has `away_host_name: null`;
  - `POST /series/{id}/guest` for the lead slot refuses the second host's personality, with "{name} already has that personality. Pick another one.".
- [ ] T118 [P] [US4] Extend `backend/tests/integration/podcasts/test_guest_episodes.py` (T095):
  - a Panel series' guest in Clara's place is introduced as joining today, and Clara is away;
  - the next episode has Clara back with the same name, personality and voice, no guest, and a snapshot marking the guest episode's points as missed by her;
  - the series count and Hugo's memory include the guest episode;
  - a One host series' lead guest works the same way;
  - a missing guest voice behaves as 007 FR-031.
- [ ] T119 [P] [US4] Write the Vitest tests:
  - `frontend/src/components/podcasts/GuestDialog.test.tsx`: a personality `radiogroup`, then **Invite**, then the cast guest is shown; an `alertdialog` with focus trap and return;
  - `frontend/src/components/podcasts/SeriesHostCard.test.tsx`: **Invite a guest…** beside **Recast…**; with a guest in that chair, the regular card reads "Away this episode";
  - `frontend/src/components/podcasts/GuestCard.test.tsx`: **Remove guest** restores the regular host;
  - `frontend/src/hooks/podcasts/useGuest.test.tsx`: inviting a guest on the lead chair while the automatic expert sits in the second chair replaces the expert, so there is still one guest;
  - `frontend/src/components/podcasts/EpisodeHeader.test.tsx`: "Guest: Marco" and "Clara is away" from `is_guest` and `away_host_name`, as text, not colour alone.
- [ ] T120 [P] [US4] Write `frontend/e2e/podcast-guests.spec.ts` with `guestDraft`:
  - Invite a guest… → personality → Invite shows the guest card;
  - Another guest sends `avoid_names`;
  - Remove guest restores the host;
  - the away label;
  - the Start request's `guest`;
  - the episode header shows the guest and away text.

### Implementation for User Story 4

- [ ] T121 [P] [US4] Add `RememberedLine`, `away_host_name` and both point forms to `backend/app/podcasts/services/series_snapshot.py`: `to_json` / `from_json` via `_line_json` / `_line_of` (≈ 13 / 12 lines), and `SeriesBrief.of` with `guest_name`, `away_host_name` and `missed_names` (≈ 10 lines). Makes T113 green.
- [ ] T122 [P] [US4] Add `conversation_id` to `RememberedPoint` in `backend/app/podcasts/services/series_storage.py`, filled by `SQLiteSeriesStorage.remembered` in `backend/app/podcasts/services/sqlite_series_storage.py`. Update `backend/tests/support/fake_series_storage.py` and `backend/tests/support/series_records.py`. Makes T114 green.
- [ ] T123 [US4] Extend `backend/app/podcasts/services/series.py`:
  - a guest in place of either regular host, with `away_host_name`;
  - `_snapshot` marks points via `_remembered_lines(points, present, cast)`, using `hosts_present`: a point is missed by every present regular host who was not in its episode.

  Makes T115 green.
- [ ] T124 [US4] Render the away host, the lead-slot stand-in and the missed marks in `backend/app/podcasts/prompts.py`: `_point_line(point, series)`, the away lines in `_guest_lines`, the `open` cue naming both, and the marks rule only when a mark is present. Then generate `backend/tests/unit/podcasts/golden/configured_series_guest_prompt.json` with the `--write` script, review it against R10–R11, and pin it. Makes T116 green.
- [ ] T125 [US4] Add `away_host_name` and the replacement guest's `is_guest` to the episode in `backend/app/podcasts/responses.py`, via `_guest_fields(episode)` (`_episode_fields` ≈ 19 lines). Makes T117 and T118 green.
- [ ] T126 [US4] Create `frontend/src/components/podcasts/GuestDialog.tsx`. Add **Invite a guest…** and "Away this episode" to `frontend/src/components/podcasts/SeriesHostCard.tsx`, **Remove guest** to `GuestCard.tsx`, and the single-guest rule (a lead-chair guest replaces the automatic expert) to `frontend/src/hooks/podcasts/useGuest.ts`, through small child components so each stays ≤ 20 lines.
- [ ] T127 [US4] Show "Guest: {name}" and "{name} is away" in `frontend/src/components/podcasts/EpisodeHeader.tsx`, through a small child component. Makes T119 and T120 green.
- [ ] T128 [US4] Write `backend/tests/integration/podcasts/test_guest_episode_benchmark.py` (`@pytest.mark.benchmark`): 10 guest episodes in a two-host series and each following episode, printing the guest's introduction and every returning-host line that mentions the guest episode, for SC-009 review. Run it on `llama3.1:8b` and record the results in `specs/011-configurable-podcast-shows/talk-review-sheet.md`.
- [ ] T129 [US4] US4 checkpoint: the full suites, lint, and quickstart §4 step 7 by hand.

**Checkpoint**: all four stories work, and each is independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T130 Complete `specs/011-configurable-podcast-shows/talk-review-sheet.md`:
  - run `backend/.venv/bin/pytest -m benchmark -s tests/integration/podcasts -k "host_talk or guest_episode or latency"` again on the final code;
  - add 10 Presented and 10 Conversation episodes to the host-talk run for SC-004, with intents counted from storage and spot-checked;
  - review SC-003 (≥ 20 learner questions, answered in the very next line) and SC-009 (10 guest episodes);
  - record every SC-001–SC-005, SC-009 and SC-011 figure against its target, and the R18 `prompt_eval_count`.
- [ ] T131 If SC-001–SC-004 miss on `llama3.1:8b`, ship configured talk as experimental, as in 005 and 010:
  - write a failing test first in `frontend/src/components/podcasts/EpisodeSettings.test.tsx` for a short experimental note inside the disclosure;
  - add the note to `EpisodeSettings.tsx`, built like `SeriesExperimentalNote.tsx`;
  - record the figures in `docs/architecture.md` § "Open items".

  If R18 shows truncation, also record it there, with the configurable `num_ctx` option. If every target is met, record that instead and add no note.
- [ ] T132 [P] Update `docs/architecture.md`:
  - host talk (`HostTalk`, `LegacyTalk` / `ConfiguredTalk`, `host_talk_for`);
  - the line kinds and invitation hazards;
  - sentence streaming: amend the "batched tokens" note for podcast lines, and keep it for roleplay;
  - series settings and scopes;
  - guests and the missed-by marks.
- [ ] T133 [P] Update `CLAUDE.md`:
  - add the 011 domain-module note to "Active Technologies", covering the new `app/podcasts/services/` modules, `with_sentence_rules`, `stream_live` / `iterate_in_thread`, and the factory being the only outside importer of `spoken_parts` and `subject_check`;
  - add a 011 entry at the top of "Recent Changes", with the experimental status from T131;
  - add 011 to the shipped-features sentence in "Project Overview";
  - point the plan reference at `specs/011-configurable-podcast-shows/plan.md`.
- [ ] T134 SC-010 check against the backup (T002). Run the app once on the real `~/.open-language/app.db`. Then compare, between it and `app.db.pre-011`, the row counts and contents of `conversations`, `messages`, `podcast_*`, `podcast_series*`, vocabulary and `app_settings`: every pre-existing row is present and unchanged. Open a pre-feature series' setup and an unfinished pre-feature episode in the app.
- [ ] T135 Run the quickstart §5 accessibility check by hand, in both themes, at 360 px and at desktop width. Record the result in the PR description.
- [ ] T136 Final gate:
  - quickstart §2 in full: `backend/.venv/bin/pytest` (≥ 90% coverage, zero skips), `ruff check .`, `black --check .`, `npm run lint`, `npm test -- --run` and `npm run test:e2e`;
  - `git diff 28ab4c7 -- backend/tests/unit/podcasts/golden/one_off_prompts.json` is empty;
  - `git diff 28ab4c7 -- backend/app/prompts/templates.py backend/app/routers/chat.py backend/app/routers/audio.py backend/app/services/llm backend/app/services/tts backend/app/conversation_summary backend/app/practice_languages backend/app/language_data backend/language_kit` is empty;
  - quickstart §4 walk-through, steps 1–8.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T003 is needed by T004.
- **Foundational (Phase 2)**: depends on Setup. **Blocks every story.**
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on US1. It extends T046's default settings on Start, and its settings
  only mean something once `ConfiguredTalk` exists.
- **US3 (Phase 5)**: depends on US2, for the `settings` request fields, the Episode settings
  fieldsets that carry scope marks, and `useEpisodeSettingsForm`.
- **US4 (Phase 6)**: depends on US3, for `cast_guest`, the guest endpoint, the guest checks at
  Start, `guest_slot`, `hosts_present`, `GuestCard` and `useGuest`.
- **Polish (Phase 7)**: depends on every story. T131 needs T130's results; T134 needs T002.

### Within the Foundational phase

- The tests T004–T012 run in parallel. T005 passes on today's code, since it is a pin; every other
  test fails first.
- Backend chain:
  - T013 → T014;
  - T015 after T013;
  - T016 after T015;
  - T017 after T016;
  - T018 after T017;
  - T019 after T015 and T014.
- T020 and T021 are independent of the backend chain. T022 is last.

### Within each story

- Test tasks first; confirm that they fail.
- Backend before the frontend that calls it, except the frontend tests, which can be written at any
  time after T021.
- US1's streaming chain: T047, T048, T049 and T050 in parallel → T051 → T053 → T054 → T055.
  T052 is in parallel with T051.
- US1's talk chain: T041 and T043 → T044 → T045 → T046.
- Each story ends with a full-suite checkpoint (T064, T085, T112, T129).

### Shared files: never run two of these tasks at the same time

- `backend/app/podcasts/prompts.py`: T017, T044, T075, T080, T106, T124.
- `backend/app/podcasts/routes.py`: T042, T046, T055, T077, T107.
- `backend/app/podcasts/services/series.py`: T046, T077, T104, T123.
- `backend/app/podcasts/schemas.py`: T042, T074, T105.
- `backend/app/podcasts/responses.py`: T042, T079, T107, T125.
- `backend/app/podcasts/catalog.py`: T013, T042.
- `backend/app/podcasts/services/host_talk.py`: T016, T043.
- `backend/app/podcasts/services/storage.py` / `sqlite_storage.py`: T019, T078, T101.
- `backend/app/podcasts/services/series_storage.py` / `sqlite_series_storage.py`: T100, T122.
- `backend/app/podcasts/services/series_snapshot.py`: T103, T121.
- `backend/app/services/factory.py`: T053, T076.
- `backend/tests/unit/test_module_boundaries.py`: T034, T071.
- `backend/tests/unit/podcasts/test_catalog.py`: T006, T024.
- `backend/tests/unit/podcasts/test_series_values.py`: T091, T113.
- `backend/tests/unit/podcasts/test_series_service.py`: T089, T115.
- `backend/tests/unit/podcasts/test_series_prompts.py`: T005, T092, T116.
- `backend/tests/unit/podcasts/test_sqlite_storage.py`: T010, T088.
- `backend/tests/unit/podcasts/test_sqlite_series_storage.py`: T087, T114.
- `backend/tests/contract/test_podcasts_catalog_api.py`: T024, T068.
- `backend/tests/contract/test_podcast_series_episodes_api.py`: T093, T117.
- `backend/tests/integration/podcasts/test_guest_episodes.py`: T095, T118.
- `backend/tests/support/fake_series_storage.py`: T100, T122.
- `frontend/src/services/podcastsApi.ts`: T021, T057, T081, T108.
- `frontend/src/hooks/podcasts/useSetupForm.ts` / `useSetupStart.ts`: T084, T111.
- `frontend/src/hooks/podcasts/useGuest.ts`: T110, T126.
- `frontend/src/components/podcasts/SeriesHostCard.tsx` / `GuestCard.tsx`: T110, T126.
- `frontend/src/pages/PodcastSetup.test.tsx`: T072, T097.
- `frontend/e2e/fixtures.ts`: T021.
- `specs/011-configurable-podcast-shows/talk-review-sheet.md`: T063, T128, T130.

### Parallel Opportunities

- Foundational: all nine test tasks (T004–T012) together; T020 and T021 alongside the backend chain.
- US1: T023–T037 and T039–T040 together; then T041, T047, T048, T049, T050 and T052 together; T057
  alongside the whole backend.
- US2: T065–T073 together; T081 alongside the backend T074–T080.
- US3: T086–T098 together; T099, T102 and T103 together; T108 alongside the backend.
- US4: T113–T120 together; T121 and T122 together.
- Polish: T132 and T133 together.

---

## Parallel Example: Foundational tests

```bash
# All foundation tests together (T005 is a pin and passes on today's code; the others fail first):
Task: "T004 upgrade pin — backend/tests/integration/podcasts/test_configured_upgrade_preserves_data.py"
Task: "T005 legacy pins via helper — backend/tests/unit/podcasts/legacy_talk_calls.py"
Task: "T006 catalogues — backend/tests/unit/podcasts/test_catalog.py"
Task: "T008 EpisodeSettings — backend/tests/unit/podcasts/test_episode_settings.py"
Task: "T009 HostTalk contract — backend/tests/contract/service_interfaces/test_host_talk_contract.py"
Task: "T010 settings row — backend/tests/unit/podcasts/test_sqlite_storage.py"
```

## Parallel Example: User Story 1

```bash
# US1 tests together (each must fail first):
Task: "T023 with_sentence_rules — backend/tests/unit/conversation_levels/test_rules.py"
Task: "T025 ConfiguredTalk — backend/tests/unit/podcasts/test_host_talk.py"
Task: "T027 policy properties — backend/tests/unit/podcasts/test_turn_policy_properties.py"
Task: "T028 run_turn_live — backend/tests/unit/services/conversation/test_pool.py"
Task: "T030 splitter — backend/tests/unit/podcasts/test_sentences.py"
Task: "T033 spoken parts — backend/tests/unit/podcasts/test_spoken_parts.py"
Task: "T036 streamed lines — backend/tests/integration/podcasts/test_streamed_lines.py"
Task: "T040 E2E — frontend/e2e/podcast-episode.spec.ts"

# Independent streaming pieces together:
Task: "T047 pool.run_turn_live + engine.stream_live"
Task: "T048 conversation_turns/streaming.py iterate_in_thread"
Task: "T049 services/sentences.py SentenceSplitter"
Task: "T050 sanitiser.py StreamingSanitiser"
Task: "T052 services/spoken_parts.py SpokenParts"
```

## Parallel Example: User Story 3

```bash
Task: "T086 SeriesSettings — backend/tests/unit/podcasts/test_series_settings.py"
Task: "T090 cast_guest — backend/tests/unit/podcasts/test_casting.py"
Task: "T093 series settings + guest endpoints — backend/tests/contract/test_podcast_series_settings_api.py"
Task: "T094 SC-006 — backend/tests/integration/podcasts/test_series_settings.py"
Task: "T098 E2E — frontend/e2e/podcast-series-settings.spec.ts"
```

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup, including the database backup (T002) and the frozen schema (T003).
2. Phase 2 Foundational. At its checkpoint nothing visible has changed, and the legacy and upgrade
   pins are green.
3. Phase 3 US1, **including the host-talk and latency benchmarks (T062–T063)**, run before the
   settings build on the defaults. Stop if SC-011 misses.
4. **Stop and validate**: quickstart §4 steps 1–4. The learner's complaint is fixed without opening
   any settings.

### Incremental delivery

1. Foundation → US1 (podcast-like hosts, streamed long lines) → demo.
2. + US2: Episode settings for every episode, including Conversation · Short · Often for the old feel.
3. + US3: series settings, scopes, the reset, and the expert for one episode in three choices.
4. + US4: a guest in a regular host's place, with away hosts and missed marks.
5. Polish: the full benchmarks and review sheet, the experimental label if needed, docs, SC-010 on
   the real database, and the accessibility check.

---

## Notes

- **[P]** means a different file with no dependency on an incomplete task. Two [P] tasks never edit
  the same file.
- Every test must be seen failing before its implementation (Red → Green → Refactor). The
  exceptions are the T005 legacy pins, which record today's behaviour, and the configured goldens
  (T026, T116), whose JSON is written from reviewed output.
- **Spec readings fixed in these tasks**:
  - `HostTalk.invites` takes `(run, format, rng)`, as in plan.md's function-length plan; research
    R1's table omits `format`;
  - a guest may take the only host's place in a One host series (spec US4-6 and edge cases), so
    research R10's "at least one regular host takes part" is not enforced; at most one guest is
    (plan interpretation 6);
  - every podcast host line streams, legacy episodes included. FR-025 pins their prompts, cues and
    invitations, and T036 checks that the stored text is the same.
- Benchmarks are **deselected** by the existing addopts, never skipped. Results below a bar go to
  `docs/architecture.md` § "Open items".
- Commit after each task or logical group, ending commit messages with the attribution line the
  session requires.
