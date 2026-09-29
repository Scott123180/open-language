---

description: "Task list for 007 — Podcast Mode"
---

# Tasks: Podcast Mode

**Input**: Design documents from `/specs/007-podcast-mode/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: Test tasks are MANDATORY per the TDD constitution (Principle III). Every test task is
written first and must be seen to FAIL before the implementation task that follows it. Tests sit at
the level each guarantee in [contracts/api.md](contracts/api.md) names: unit, contract,
integration, Vitest or Playwright. The one exception to "see it fail" is the `conversation_turns`
move (T022): its safety net is the existing chat suite, which must stay green **and unedited**.

**Organization**: Tasks are grouped by user story, in the order plan.md § "Suggested phase order"
gives:
- **Foundational** builds the shared turn mechanics, catalogues, tables, storage, the turn policy,
  cues, the sanitiser, casting, per-host speech and the test doubles.
- **US1** (P1) is the MVP: One host, end to end, with Past Chats.
- **US2** (P1) is Listen: two hosts, Continue, hidden text.
- **US6** (P2) is Summary, for roleplay and episodes. It needs nothing from US2–US5.
- **US3** (P2) is Panel: Jump in, Pass, the addressed host.
- **US4** (P2) is the generator and Surprise me.
- **US5** (P3) is shaping hosts before starting.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US6 (the spec.md user stories); absent in Setup, Foundational and Polish
- Paths are relative to the repository root (`backend/app`, `backend/tests`, `frontend/src`,
  `frontend/e2e`)

## Standing rules for every task

- **Python** runs through the venv only: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff` and
  `backend/.venv/bin/black`, run from `backend/`.
- **Function length**: every new or modified function is ≤ 20 lines (Constitution I). The only
  permitted exceptions are the three React pages in plan.md § Complexity Tracking (`Chat`,
  `History`, `Home`), each of which gains one element or one hook and nothing else.
- **Imports** (Principle V):
  - code outside `app.podcasts` imports only its package root (`router`, `PODCAST_SCENARIO_ID`,
    `PodcastMessageVoices`, `PodcastSpeakerNames`);
  - code outside `app.conversation_summary` imports only its root (`router`, `SpeakerNames`);
  - the one exception is `backend/app/services/factory.py`, the composition root. It may import
    the storage, lock, caster and surprise implementations from `app.podcasts.services.*` and
    `app.conversation_summary.services.*`, as it already does for `app.flashcards.services.*` and
    `app.corrections.services.*`. Nothing else may;
  - `app.podcasts` and `app.conversation_summary` never import each other;
  - `PodcastMessageVoices` and `PodcastSpeakerNames` are constructed only in
    `backend/app/services/factory.py`;
  - `backend/app/routers/audio.py` never imports `app.podcasts`.
- **Files not modified** (plan.md § Project Structure):
  - `backend/app/prompts/templates.py`;
  - anything under `backend/app/corrections/`, `backend/app/conversation_levels/`,
    `backend/app/services/llm/`, `backend/app/services/stt/` and `backend/app/flashcards/`;
  - `backend/app/services/conversation/{engine,pool,sync}.py` (only `session.py` gains one enum
    member);
  - `backend/app/routers/{conversations,learning,vocabulary,scenarios}.py`;
  - `frontend/src/components/chat/MessageBubble.tsx`.
- **Language literals**: no code outside `backend/app/practice_languages/catalog.py` and
  `backend/app/services/tts/voices.py` hard-codes `"es"` or `"de"`. The existing
  `backend/tests/unit/test_no_language_literals.py` scans all of `backend/app` and `frontend/src`,
  so it covers the new modules automatically.
- **No magic values**: every limit (run cap, invite deadline, hazard rates, lengths, the summary
  chunk budget, the surprise history size, the 200-character idea limit, the interest limits) is a
  named constant or a catalogue field.
- **Frontend styling** uses design-system tokens only (`docs/design-system.md`): no hex colours,
  `--color-text`/`--color-text-muted` for navigation and labels, `--radius-lg` for cards,
  `--shadow-*` for shadows, `var(--color-text-on-primary)` on primary backgrounds.
- **Frontend completion**: a frontend task is complete only when `cd frontend && npm run test:e2e`
  passes.
- **Benchmarks** are marked `@pytest.mark.benchmark` and are deselected by the existing addopts,
  never skipped.

---

## Phase 1: Setup

**Purpose**: Package skeletons, a green baseline, and the frozen pre-007 schema.

- [X] T001 [P] Create empty package files:
  - `backend/app/podcasts/__init__.py`, `backend/app/podcasts/services/__init__.py`;
  - `backend/app/conversation_summary/__init__.py`, `backend/app/conversation_summary/services/__init__.py`;
  - `backend/app/conversation_turns/__init__.py`;
  - `backend/tests/unit/podcasts/__init__.py`, `backend/tests/unit/conversation_summary/__init__.py`, `backend/tests/unit/conversation_turns/__init__.py`;
  - `backend/tests/integration/podcasts/__init__.py`, `backend/tests/integration/conversation_summary/__init__.py`.
- [X] T002 Record the green baseline before any change:
  - from `backend/`: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff check .` and `backend/.venv/bin/black --check .`;
  - from `frontend/`: `npm run lint`, `npm run build`, `npm test` and `npm run test:e2e`.

  All must pass. Note any pre-existing failure in the PR description rather than fixing it here.
- [X] T003 Back up the local database: `cp ~/.open-language/app.db ~/.open-language/app.db.pre-007`. Quickstart §5 (SC-011) compares against it, so take it before the app runs any 007 code.
- [X] T004 Freeze the pre-007 schema as `backend/tests/fixtures/schema_006.sql`, as 006 did with `schema_005.sql`:
  - `git worktree add "$SCRATCH/wt-006" 736cde7` (the last 006 commit on `master`).
  - In that worktree, run `init_db()` against an empty database with `OPEN_LANGUAGE_DB_PATH` set to a scratch file, using this repository's `backend/.venv/bin/python`.
  - `sqlite3 <file> .schema > backend/tests/fixtures/schema_006.sql`, then `git worktree remove "$SCRATCH/wt-006"`.
  - Check the dump: it has `voice_choices`, has no `podcast_*` or `conversation_summaries` table, and `app_settings` has no `summary_language` column.
  - Add a header comment naming the source commit and "Do not edit", in the style of `schema_005.sql`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**:
- the turn mechanics moved out of `routers/chat.py` into `conversation_turns/` (research R11);
- the podcast catalogues and the `PracticeLanguage` additions;
- the podcast tables, the `PodcastStorage` ABC and its SQLite implementation;
- `SessionKind.PODCAST`, `MessageVoiceLookup`, `provider_for_voice` and per-host audio;
- the pure core: `TurnPolicy`, `render_cue` and the history builder, `LineSanitiser`, `HostCaster`,
  `EpisodeLocks`;
- the factory wiring, the scripted line writer, and the frontend API types and E2E fixtures.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for the foundation (write first, see them fail)

- [X] T005 [P] Write the SC-011 upgrade test `backend/tests/integration/podcasts/test_upgrade_preserves_data.py`, modelled on `backend/tests/integration/practice_languages/test_upgrade_preserves_data.py`:
  - build a pre-007 SQLite file in `tmp_path` by `executescript` of `backend/tests/fixtures/schema_006.sql` (T004). Never `create_all()`: the shared metadata already holds the 007 tables;
  - seed two conversations (one `es`, one `de`) with messages, three vocabulary items, one deck with cards, an `app_settings` row and a `voice_choices` row;
  - snapshot every row of `conversations`, `messages`, `vocabulary_items`, `decks`, `voice_choices` and `app_settings` (pre-007 columns only);
  - run `init_db()` **twice** against that file, rebuilding the engine as `backend/tests/integration/conftest.py` does;
  - assert every snapshotted row is identical, and the tables `podcast_episodes`, `podcast_hosts`, `podcast_host_lines` and `podcast_preferences` exist.

  US6 extends this test with `conversation_summaries` and `app_settings.summary_language` (T083).
- [X] T006 [P] Write `backend/tests/unit/conversation_turns/test_public_surface.py` (contracts §12, research R11):
  - `set(app.conversation_turns.__all__) == {"sse", "EngineTurn", "SavedReply", "relay_engine_reply", "start_warming", "LearnerMessageRequest", "save_learner_message", "Corrections", "plan_learner_turn", "schedule_speech"}`;
  - `sse({"a": 1}) == 'data: {"a": 1}\n\n'`;
  - `LearnerMessageRequest(content="x", input_source="keyboard", transcription_confidence=0.2).spoken_confidence is None`, and `0.2` for `input_source="voice"`;
  - `app.routers.chat.ChatMessageRequest is app.conversation_turns.LearnerMessageRequest`.

  The behavioural net for the move is the existing chat and corrections suites (`backend/tests/integration/routers/test_chat_*.py`, `test_helper.py`, `test_suggestions.py`, `backend/tests/integration/corrections/`), which must pass **unmodified** after T022.
- [X] T007 [P] Write catalogue unit tests `backend/tests/unit/podcasts/test_catalog.py` (data-model §1.1–§1.4, §1.6 P1–P5):
  - `list(PODCAST_FORMATS) == ["one_host", "panel", "listen"]`, with exactly the descriptor values in data-model §1.1 (`host_count`, `is_learner_speaking`, `has_jump_in`, `max_host_run`, `invite_deadline`);
  - `DEFAULT_PODCAST_FORMAT == "one_host"`;
  - lengths are `short` 10, `medium` 20, `long` 40, and `DEFAULT_EPISODE_LENGTH == "medium"`;
  - personalities are exactly the ten ids of data-model §1.3, each with a non-empty `label`, `description` and `speaking_style`;
  - there are eight shows (research R8), each with `learner_role` in `{"guest", "co_host", "caller"}`;
  - P1 unique ids per catalogue; P2 `len(PERSONALITIES) >= 8` and `len(SHOW_TEMPLATES) >= 6`; P3 every show's two default personalities exist and differ; P4 `host_count + is_learner_speaking <= MAX_PARTICIPANTS == 3`, `max_host_run is None` exactly when `host_count == 1`, `invite_deadline is None` exactly when `not is_learner_speaking`; P5 the defaults exist;
  - every descriptor is a frozen dataclass (assigning a field raises `FrozenInstanceError`) and every catalogue is a `MappingProxyType`.
- [X] T008 [P] Extend `backend/tests/unit/practice_languages/test_catalog.py` (data-model §1.5, P6–P7):
  - P6: for every practice language and every gender among its voices in `AVAILABLE_VOICES`, `host_names_for(code, gender)` has ≥ 8 names, all distinct;
  - `guest_labels_for(code)` is non-empty;
  - FR-030: every practice language has at least two voices in `AVAILABLE_VOICES` with different keys (today `es_ES-davefx-medium` and `es_AR-daniela-high` for Spanish, `de_DE-thorsten-medium` and `de_DE-kerstin-low` for German), so a new language cannot ship with one voice unnoticed;
  - P7: every `sample_line` contains exactly one `{name}`, and `voice_sample_line(code, "Lena")` contains "Lena";
  - `host_names_for("fr", "female")` raises `UnknownLanguage`;
  - extend the `__all__` assertion with `host_names_for`, `guest_labels_for` and `voice_sample_line`.
- [X] T009 [P] Write `backend/tests/contract/service_interfaces/test_podcast_storage_provider.py`: `PodcastStorage` is an ABC declaring `create_episode`, `get_episode`, `list_episodes`, `get_hosts`, `save_host_line`, `get_lines`, `mark_passed`, `mark_revealed`, `get_preferences` and `save_preferences`; the SQLite implementation implements every one.
- [X] T010 [P] Write `backend/tests/unit/podcasts/test_sqlite_storage.py` against an in-memory database (data-model §2.1–§2.4):
  - `create_episode(...)` creates the `conversations` row with `scenario_id == PODCAST_SCENARIO_ID == "podcast"`, `scenario_title` = the show title, the given `target_language`, plus the `podcast_episodes` row and one `podcast_hosts` row per participating host;
  - One host stores only the `lead` host (FR-003);
  - `UNIQUE(conversation_id, slot)` and `UNIQUE(conversation_id, name)` reject duplicates;
  - `save_host_line` stores a `messages` row with `role = "assistant"` and a `podcast_host_lines` row with its `host_id`, `intent`, `invites_learner` and `was_trimmed`;
  - `get_lines` returns messages in `created_at` order joined to host facts; a `role = "user"` message has no host row and reads as the learner;
  - `mark_passed` and `mark_revealed` set their flags; `mark_revealed` is idempotent;
  - `get_preferences()` creates the `id = 1` row with defaults on first read (`last_format = "one_host"`, `is_show_text_on = False`, `interests = []`, `learner_name = None`);
  - deleting the conversation cascades to all three episode tables.
- [X] T011 [P] Extend `backend/tests/unit/test_database.py`: after `init_db()` the four podcast tables exist with the columns and types of data-model §2.1–§2.4, and running `init_db()` twice is idempotent.
- [X] T012 [P] Extend `backend/tests/unit/services/conversation/test_session_values.py`: `SessionKind.PODCAST == "podcast"`, and `SessionKey(SessionKind.PODCAST, "57")` is hashable and distinct from the roleplay key for `"57"`.
- [X] T013 [P] Extend the TTS tests (contracts §11, research R7):
  - `backend/tests/contract/service_interfaces/test_tts_provider.py`: `MessageVoiceLookup` is an ABC with exactly one abstract method, `voice_for_message(message_id) -> str | None`;
  - `backend/tests/unit/services/test_speech_selection.py`: `provider_for_voice(language, voice_key, unavailable_message)` builds the provider for an installed voice of that language; raises `VoiceUnavailable(unavailable_message)` without calling the builder when the voice is not installed; raises `VoiceUnavailable` when the voice speaks another language; `provider_for` is unchanged.
- [X] T014 [P] Extend `backend/tests/integration/routers/test_audio_tts.py` with a fake `MessageVoiceLookup` override:
  - a message whose lookup returns `es_AR-daniela-high` is synthesised with that voice (`RecordingTtsBuilder.voice_keys`);
  - a lookup returning `None` keeps the conversation's language voice (every existing test in the file passes unchanged);
  - a host voice that is not installed returns 503 with the lookup's host message, and nothing is synthesised.
- [X] T015 [P] Write rule tests `backend/tests/unit/podcasts/test_turn_policy.py` (data-model §4, §5), one test per rule, with a seeded `random.Random`:
  - `turn()`: no lines → `hosts/opening`; last line learner → `hosts/reply`; last host line not inviting, or passed → `hosts/continue`; last host line inviting and not passed → `learner`; finished → `finished`;
  - intent: `open` (lead) with no lines; `greet` (second) after one host line in Panel and Listen; `sign_off` on an End request; `wrap_up` at ≥ target with no wrap-up yet; Listen `sign_off` after a `wrap_up`; otherwise `discuss`;
  - speaker, in priority order: run cap excludes a host with `max_host_run` in a row; a learner line naming a host (accent- and case-insensitive, whole word; the first named if both) picks that host; a gap of ≥ 2 lines picks the host with fewer; a host line naming the other host hands over; `open` and `sign_off` prefer the lead; otherwise 0.7/0.3, and 0.6 for the inviting host after a learner line;
  - invitation: One host always except `sign_off`; Panel hazard 0.25, 0.45, 0.6, then certain at `run == invite_deadline`, where `run` restarts after a learner line or a pass; `wrap_up` always; `sign_off` never; Listen never;
  - settle invite: an invitation whose two previous lines came from different hosts has `is_settle_invite`;
  - `is_after_pass` is set on the cue after a passed invitation.
- [X] T016 [P] Write property tests `backend/tests/unit/podcasts/test_turn_policy_properties.py` (data-model §5 guarantees), simulating ≥ 1,000 seeded episodes per format with random learner replies, passes, name mentions and End requests:
  - the invitation deadline is never exceeded (FR-014);
  - no host run exceeds `max_host_run` (FR-015);
  - each host has ≥ 25% of host lines in every episode with ≥ 8 host lines (FR-015, plan interpretation 2);
  - an addressed host always speaks next (FR-018);
  - the wrap-up comes within 2 host lines of the target (FR-019);
  - every Listen episode ends with `sign_off`.
- [X] T017 [P] Write `backend/tests/unit/podcasts/test_prompts.py` and `backend/tests/unit/podcasts/test_cues.py` (research R3, R5, R14):
  - the standing prompt contains the language rule with language **names** (never codes), the show title, premise and learner role, each participating host's name, personality description, speaking style and show role, the line rules of research R5, and the learner label ("our guest" when `learner_name` is None, FR-011);
  - the standing prompt tells the hosts that when the learner writes in English, the host answers in the practice language and invites the learner, in character, to use it (spec edge case "Learner writes in English");
  - the level rules are appended last via `with_partner_speech_rules()`; at Natural the prompt equals the unlevelled prompt;
  - the standing prompt for the longest show with two hosts is ≤ 700 tokens at 4 characters per token; every cue is ≤ 40 tokens;
  - `render_cue(cue, cast, learner_label)` names the speaking host, states the intent, says "End by asking …" only when `invites_learner`, and asks the learner to settle it when `is_settle_invite`; it begins with the producer-note marker;
  - the history builder maps host lines to `assistant` turns `p{message_id}`, learner lines to `user` turns `p{message_id}` rendered `"{learner label}: {text}"`, and puts a `user` cue `c{position}` before every host line;
  - re-rendering the history from the same stored facts is byte-for-byte identical, and a request built from it ends with a fresh cue at `c{len(lines)}` (so `TurnRequest` accepts it).
- [X] T018 [P] Write `backend/tests/unit/podcasts/test_sanitiser.py` (research R4, FR-012):
  - strips a leading own label (`Lucía:`, `**Lucía:**`, `[Lucía]`);
  - cuts at the first line or sentence starting with the other host's name, the learner's name, a role word (`Guest`, `Learner`, `User`, `You`) or one of the language's `guest_labels`;
  - drops bracketed and starred stage directions (`(laughs)`, `*risas*`);
  - reports `was_trimmed` exactly when text was removed after the own label;
  - an all-label line returns empty; a clean line is returned unchanged;
  - a mid-sentence mention of the other host ("como dice Marco") is kept.
- [X] T019 [P] Write `backend/tests/unit/podcasts/test_casting.py` (research R6, data-model §3), with a fake `VoiceInstallation`:
  - the lead takes the first installed voice for the language and the second a different one;
  - names come from `host_names_for(language, voice.gender)`, never the other host's name or the learner's (case-insensitive);
  - a ready-made show's default names are stable for the same `show_id`, slot and language across calls;
  - the two hosts always differ in personality;
  - with one installed voice both hosts share it; with none, casting still returns hosts (the voice notice is the catalogue's job);
  - `Cast` rejects a second host for a one-host format, equal names or equal personalities, and a name over 40 characters.
- [X] T020 [P] Write `backend/tests/unit/podcasts/test_episode_lock.py` (research R12): `EpisodeLocks.try_acquire(57)` succeeds once and fails while held; release frees it; different episodes do not block each other; the lock is released when the guarded block raises.
- [X] T021 [P] Write `backend/tests/unit/services/test_scripted_line_writer.py` for the new double `backend/tests/support/scripted_line_writer.py`: a `SessionCapableProvider` whose sessions return the next scripted line for each reply, record every `(standing_prompt, pending turns)` they receive, count `open_session` calls, and can be told to raise `LLMError` on the next reply.

### Implementation for the foundation

- [X] T022 Move the shared turn mechanics from `backend/app/routers/chat.py` into `backend/app/conversation_turns/` with **no behaviour changes** (research R11; passes T006 with the chat suites unmodified). The only edits inside moved bodies are the call sites of the renamed functions below:
  - `relay.py`: `sse` (was `_sse`), `SavedReply`, `EngineTurn`, `relay_engine_reply`, `start_warming` and `_warm_quietly`;
  - `learner.py`: `LearnerMessageRequest` (was `ChatMessageRequest`), `save_learner_message`, `_is_low_confidence`;
  - `corrections.py`: `Corrections`, `plan_learner_turn` (was `_plan_learner_turn`), `_plan_turn_failing_open`, `_persist_feedback`, `_feedback_frame`, `_turn_context`, `_last_character_line`, and a private `_languages_of`. `chat.py` keeps its own `_languages_of` (`chat.py:116`), because `_RoleplayContext` and the suggestion and helper endpoints still use it, so `corrections.py` gets a copy of the same one-line wrapper around `ConversationLanguages.of` instead of importing a private name;
  - `speech.py`: `schedule_speech` (was `_schedule_tts`) and `_tts_cache_dir`;
  - `__init__.py` exports exactly the T006 names via `__all__`.

  In `chat.py`, import them from `app.conversation_turns` and keep `ChatMessageRequest = LearnerMessageRequest`. `_RoleplayContext`, `_standing_roleplay_prompt` (imported by the benchmark and live tests) and `_RoleplayContext._speak` stay in `chat.py`, so the `app.routers.chat` logger that `test_chat_message.py` filters on is unchanged. Then run the full backend suite: every pre-existing test passes without edits.
- [X] T023 [P] Implement `backend/app/podcasts/catalog.py` (passes T007): frozen, slotted `PodcastFormat`, `EpisodeLength`, `Personality` and `ShowTemplate` dataclasses; `PODCAST_FORMATS`, `EPISODE_LENGTHS`, `PERSONALITIES` and `SHOW_TEMPLATES` as `MappingProxyType` in display order; `DEFAULT_PODCAST_FORMAT`, `DEFAULT_EPISODE_LENGTH`, `MAX_PARTICIPANTS = 3`; the eight shows of research R8 with English titles and premises; the ten personalities of data-model §1.3.
- [X] T024 [P] Add `host_names: Mapping[str, tuple[str, ...]]` (keyed by voice gender), `guest_labels: tuple[str, ...]` and `sample_line: str` to `PracticeLanguage` in `backend/app/practice_languages/catalog.py`, with ≥ 8 distinct names per gender for Spanish and German, the guest labels (e.g. German `("Gast", "Zuhörer", "Anrufer")`) and the sample lines of data-model §1.5. Add `host_names_for(code, gender)`, `guest_labels_for(code)` and `voice_sample_line(code, name)` (raising `UnknownLanguage` for an unknown code) and export them from `backend/app/practice_languages/__init__.py` (passes T008).
- [X] T025 Add the ORM models to `backend/app/podcasts/models.py` exactly as data-model §2.1–§2.4, and register the module in `init_db()`'s model imports in `backend/app/database.py` (passes T011 and T005):
  - `PodcastEpisode`: `conversation_id` INTEGER PK FK → `conversations.id` ON DELETE CASCADE; `show_source` VARCHAR(12) NOT NULL (`ready_made`, `generated` or `surprise`); `show_id` VARCHAR(100) NULL; `premise` TEXT NOT NULL; `topic` VARCHAR(200) NOT NULL; `learner_role` VARCHAR(12) NOT NULL; `format` VARCHAR(12) NOT NULL; `length` VARCHAR(8) NOT NULL; `learner_name` VARCHAR(40) NULL; `created_at` DATETIME NOT NULL;
  - `PodcastHost`: `id` INTEGER PK; `conversation_id` INTEGER NOT NULL FK → `podcast_episodes.conversation_id` ON DELETE CASCADE, indexed; `slot` VARCHAR(8) NOT NULL (`lead` or `second`); `name` VARCHAR(40) NOT NULL; `personality` VARCHAR(30) NOT NULL; `voice_key` VARCHAR(200) NOT NULL; `show_role` VARCHAR(20) NOT NULL (`host`, `co_host` or `guest_expert`); `angle` TEXT NULL; `UNIQUE(conversation_id, slot)` and `UNIQUE(conversation_id, name)`;
  - `PodcastHostLine`: `message_id` INTEGER PK FK → `messages.id` ON DELETE CASCADE; `conversation_id` INTEGER NOT NULL FK → `podcast_episodes.conversation_id` ON DELETE CASCADE, indexed; `host_id` INTEGER NOT NULL FK → `podcast_hosts.id`; `intent` VARCHAR(10) NOT NULL (`open`, `greet`, `discuss`, `wrap_up` or `sign_off`); `invites_learner`, `is_passed`, `is_revealed`, `was_trimmed` BOOLEAN NOT NULL DEFAULT FALSE;
  - `PodcastPreferences`: `id` INTEGER PK default 1; `last_format` VARCHAR(12) NOT NULL default `DEFAULT_PODCAST_FORMAT`; `is_show_text_on` BOOLEAN NOT NULL default FALSE; `interests` TEXT NOT NULL default `'[]'`; `learner_name` VARCHAR(40) NULL; `updated_at` DATETIME NOT NULL default now.
- [X] T026 Implement `backend/app/podcasts/services/storage.py`: the `PodcastStorage` ABC with the ten methods of T009, and frozen record dataclasses `EpisodeRecord`, `HostRecord`, `LineRecord` (message id, role, content, created_at, and host facts or `None` for the learner) and `PreferencesRecord`, plus `NewEpisode` and `NewHost` inputs so no method takes more than three arguments.
- [X] T027 Implement `backend/app/podcasts/services/sqlite_storage.py` (`SQLitePodcastStorage`, passes T009 and T010). `create_episode` writes the conversation, episode and hosts in one transaction. `PODCAST_SCENARIO_ID = "podcast"` lives in `backend/app/podcasts/catalog.py` and is re-exported from the package root.
- [X] T028 [P] Add `PODCAST = "podcast"` to `SessionKind` in `backend/app/services/conversation/session.py` (passes T012). No other change to the conversation package.
- [X] T029 [P] Add `class MessageVoiceLookup(ABC)` with the abstract `voice_for_message(self, message_id: int) -> str | None` to `backend/app/services/tts/base.py`, and `SpeechForLanguage.provider_for_voice(language, voice_key, unavailable_message)` (≈ 8 lines) to `backend/app/services/tts/selection.py`. It checks the voice's `language` via `AVAILABLE_VOICES` and installation before calling `build`, and never falls back (passes T013).
- [X] T030 Implement `PodcastMessageVoices(MessageVoiceLookup)` in `backend/app/podcasts/services/speaker_views.py`: it returns the host's `voice_key` for a host-line message and `None` otherwise, and exposes the host-specific unavailable message ("{name}'s voice isn't installed …", research R7). Export it from `backend/app/podcasts/__init__.py`. Add `get_podcast_storage(db)` and `get_message_voices(storage = Depends(get_podcast_storage))`, which returns `PodcastMessageVoices`, to `backend/app/services/factory.py`, extending `backend/tests/unit/services/test_factory.py` first (each returns its declared abstraction). Then change `backend/app/routers/audio.py` (plan § Function-length plan): `get_tts_audio` takes `voices: MessageVoiceLookup = Depends(get_message_voices)`; a new `_speech_provider(speech, voices, message, conversation)` picks `provider_for_voice` for a host line and `provider_for` otherwise; `_synthesize_and_cache` takes a provider. Both stay ≤ 20 lines (passes T014).
- [X] T031 [P] Implement `backend/app/podcasts/services/turn_policy.py` (passes T015 and T016): frozen `LineFacts`, `LineCue`, `EpisodeState` and `Turn` value objects (data-model §3, §4); `TurnPolicy(rng: random.Random)` with `turn(state)` and `next_cue(state, is_end_requested)`. One small function per rule (`_intent`, `_excluded_by_run`, `_addressed_host`, `_balancing_host`, `_handed_over_host`, `_preferred_for_intent`, `_random_host`, `_invites`, `_is_settle_invite`); hazard rates, the 0.7/0.3 and 0.6 weights are named constants. Name matching uses `unicodedata` normalisation and a whole-word regex.
- [X] T032 Implement `backend/app/podcasts/prompts.py` (`build_standing_prompt(show, cast, learner_label, languages, level)` and `render_cue(cue, cast, learner_label)`) and `backend/app/podcasts/services/cues.py` (`episode_history(lines, cast, learner_label) -> tuple[SavedTurn, ...]` and `next_turn_history(...)` ending with the fresh cue), passing T017. `prompts/templates.py` is not edited; the language rule is written here with language names from `ConversationLanguages`.
- [X] T033 [P] Implement `backend/app/podcasts/services/sanitiser.py`: `LineSanitiser(own_name, other_labels)` with `clean(text) -> SanitisedLine(text, was_trimmed)`, the labels built from the other host, the learner name, the role words and `guest_labels_for(language)` (passes T018).
- [X] T034 [P] Implement `backend/app/podcasts/services/casting.py`: `Host` and `Cast` value objects with the invariants of data-model §3, and `HostCaster(installation, rng)` with `cast_show(template_or_personalities, language, learner_name)` and the stable default-name hash of `show_id + slot` (passes T019). Voices come from `voices_for(language)` filtered by the installation.
- [X] T035 [P] Implement `backend/app/podcasts/services/episode_lock.py`: `EpisodeLocks` with a non-blocking `try_acquire(conversation_id)` returning a context manager, or `None` when a line is in progress (passes T020).
- [X] T036 Finish wiring the factory in `backend/app/services/factory.py` (`get_podcast_storage` and `get_message_voices` came with T030): `get_episode_locks()` (process-wide singleton) and `get_host_caster(installation = Depends(get_voice_installation))`. Extend `backend/tests/unit/services/test_factory.py` first: each returns its declared abstraction, and `get_episode_locks()` is the same object on every call.
- [X] T037 Create `backend/tests/support/scripted_line_writer.py` (passes T021), and `backend/tests/integration/podcasts/conftest.py` with a `podcast_client` fixture that installs the scripted writer via `install_session_provider`, `override_speech(...)` from `backend/tests/support/fake_speech.py`, and a helper `start_episode(client, format, length="short", learner_name=None)` that posts a ready-made draft from `GET /api/podcasts/catalog`.
- [X] T038 [P] Add the frontend podcast types to the new `frontend/src/services/podcastsApi.ts`: `PodcastFormatOption`, `EpisodeLengthOption`, `PersonalityOption`, `HostDraft`, `ShowDraft`, `PodcastCatalog`, `PodcastPreferences`, `EpisodeHost`, `EpisodeLine`, `Episode`, `EpisodeSummaryRow`, and the `Turn` union `'hosts' | 'learner' | 'finished'`, exactly as contracts §1, §2 and §6. Add `showDraftFixture`, `mockPodcastCatalog`, `mockPodcastPreferences`, `episodeFixture(format)`, `lineFrame(line, turn, awaiting)` and `makeLineSseBody(frames)` to `frontend/e2e/fixtures.ts` (contracts §13).
- [X] T039 Run the full backend suite, `ruff` and `black`. T005–T021 pass, and every pre-existing test passes **unedited**.

**Checkpoint**: The pure podcast core, storage and per-host speech exist and are proven. Nothing is
visible to the learner yet, and roleplay is unchanged.

---

## Phase 3: User Story 1 — Learner joins a podcast as a guest of one host (Priority: P1) 🎯 MVP

**Goal**: From Home, the learner opens Podcasts, picks a ready-made show, starts it in One host,
talks with a host in persona who speaks in their own voice, uses every learning tool, leaves and
resumes from Past Chats, and ends the episode with a sign-off.

**Independent Test**: Pick any ready-made show in One host, exchange five turns (typed and spoken)
and use each learning tool once. The host stays in persona and on topic, speaks the practice
language at the learner's level, and every line plays in the host's voice (spec US1).

### Tests for User Story 1 (write first, see them fail)

- [X] T040 [P] [US1] Write `backend/tests/contract/test_podcasts_catalog_api.py` (contracts §1): `GET /api/podcasts/catalog` returns `language` and `language_name` for the current practice language; formats, lengths and personalities in catalogue order with exactly the keys of contracts §1; ≥ 6 shows, each a `ShowDraft` with two hosts of different names and personalities and, with two installed voices, different voices; the draft's `language` is the current practice language; switching the practice language to German gives German names.
- [X] T041 [P] [US1] Write `backend/tests/contract/test_podcast_preferences_api.py` (contracts §2, the US1 fields): `GET` returns the defaults; `PUT {"learner_name": "Sam"}` stores it and `PUT {"learner_name": ""}` clears it; a name over 40 characters is 422; `last_format` in a PUT body is ignored (read-only); values persist across a new session factory.
- [X] T042 [P] [US1] Write `backend/tests/integration/podcasts/test_one_host_episode.py` (contracts §6, §7; US1-2, US1-3, US1-7):
  - `POST /api/podcasts/episodes` returns 201 with `format == "one_host"`, one host (the lead), `turn == "hosts"`, `awaiting == "opening"`; the conversation has `scenario_id == "podcast"` and the current `target_language`; `podcast_preferences.last_format` is written and `learner_name` saved when given;
  - 422 when the draft fails data-model §6 (unknown personality, a voice of another language, equal names, a host named like the learner, bad `learner_role`), naming the host and field; 422 "The practice language changed. Pick the show again." when `show.language` differs;
  - `/next` streams one `line` frame (`intent == "open"`, the lead, `invites_learner` true) and `done` with `turn == "learner"`; the line is stored before the frame;
  - `/next` at the learner's turn → 409 "It's your turn. Reply, pass or end the episode.";
  - `/message` streams `user_message_saved`, then the host's `line` and `done` with `turn == "learner"` (FR-016);
  - on a Short episode, the host line at or after the 10th is a `wrap_up` that invites the learner; after it, `/message` still gets a `discuss` host reply and the episode stays `active` until `/end` (spec edge case "very long episode", plan interpretation 4);
  - `/end` streams a `sign_off` line and `done` with `turn == "finished"`; the conversation is `completed`; a later `/next` or `/end` → 409 "This episode has finished.";
  - `/pass` in One host → 409 "You can pass only when it's your turn in a Panel.".
- [X] T043 [P] [US1] Write `backend/tests/integration/podcasts/test_episode_resume.py` (FR-009, FR-032, US1-6): `GET /api/podcasts/episodes/{id}` returns the same hosts, names and voices before and after a restart (new session factory and engine); `lines` are the conversation's messages in order, every host line has exactly one `host_id`; `GET /api/podcasts/episodes` lists it with `show_title`, `format_label`, `host_names`, `language_name` and `status`; 404 "Episode not found" for a roleplay conversation id.
- [X] T044 [P] [US1] Write `backend/tests/integration/podcasts/test_episode_sessions.py` (contracts §7, research R3), with `RecordingSessionProvider` and the scripted writer:
  - two consecutive lines reuse one session (one `open_session`);
  - a line the sanitiser trimmed ends the session, and the next line rebuilds it from storage with the stored (trimmed) text;
  - the rebuilt history re-renders every earlier cue byte-for-byte;
  - a conversation-level change between two lines rebuilds the session and the new standing prompt ends with that level's rules (FR-026);
  - `POST /api/podcasts/episodes/{id}/session` returns 202 `{"status": "warming" | "live"}` and uses `SessionKind.PODCAST`;
  - a practice-language change in Settings leaves the episode's language, hosts and prompt unchanged.
- [X] T045 [P] [US1] Write `backend/tests/integration/podcasts/test_episode_lines.py` (FR-012, research R4, R12):
  - a scripted line leaking "Marco: …" or "Invitado: …" is stored and streamed without it, with `was_trimmed` true;
  - an all-label line is regenerated once; a second empty result sends an `error` frame and stores nothing;
  - a provider `LLMError` sends `{"error": <user_message>}`, stores nothing, and the next `/next` retries the same line;
  - two concurrent `/next` requests produce exactly one line and one 409 "A line is already on its way.".
- [X] T046 [P] [US1] Write `backend/tests/integration/podcasts/test_episode_corrections.py`, reusing the fixtures of `backend/tests/integration/corrections/conftest.py`: in Gentle, `/message` streams a `feedback` frame as chat does; in Strict, a paused message sends `done` with `turn == "learner"` and no `line`; a low-confidence spoken message is gated as in chat.
- [X] T047 [P] [US1] Write `backend/tests/integration/podcasts/test_episode_speech_and_tools.py` (FR-027–FR-031):
  - each stored host line schedules synthesis in its host's voice (`RecordingTtsBuilder.voice_keys`), and `GET /api/audio/tts/{message_id}` uses that voice;
  - with the host's voice uninstalled, `GET /api/podcasts/episodes/{id}` has `is_voice_available: false` and that host's `voice_unavailable_message`, the line is still stored, and no other voice is used;
  - translation, alternative phrasing and word lookup on a host line's `message_id` work; saving a word stores it in the episode's language;
  - `POST /api/chat/helper` with the episode's `conversation_id` works;
  - `POST /api/podcasts/episodes/{id}/suggestions` at the learner's turn returns suggestions built over a transcript labelled with host names and the learner label.
- [X] T048 [P] [US1] Write Vitest tests (co-located `*.test.ts(x)`):
  - `frontend/src/services/podcastsApi.test.ts`: `getPodcastCatalog`, `getPodcastPreferences`, `updatePodcastPreferences`, `startEpisode`, `getEpisode`, `listEpisodes`, `warmEpisodeSession`, `getEpisodeSuggestions`, and the SSE actions `streamEpisodeNext`, `streamEpisodeMessage`, `streamEpisodeEnd` parse `line`, `feedback`, `user_message_saved`, `done` and `error` frames;
  - `frontend/src/hooks/podcasts/usePodcastCatalog.test.tsx`, `usePodcastPreferences.test.tsx`;
  - `frontend/src/hooks/podcasts/usePodcastEpisode.test.tsx`: loads the episode; calls `/next` automatically at `awaiting` `opening` or `reply`; waits at `continue`; after `/message` appends the learner line then the host line; `end()` appends the sign-off and sets `finished`; an `error` frame exposes the message and a `retry()` that calls `/next`; a second action while pending is ignored.
- [X] T049 [P] [US1] Write component tests in `frontend/src/components/podcasts/`: `ShowCard.test.tsx` (a button named by the title, showing topic, hosts and role); `FormatFieldset.test.tsx` and `LengthFieldset.test.tsx` (`fieldset`/`legend` radios, default selection from props); `HostCard.test.tsx` (name, personality label); `LearnerNameField.test.tsx` (labelled input, 40-character limit); `HostLine.test.tsx` (speaker name above a `MessageBubble`, full text); `EpisodeControls.test.tsx` (Continue as the primary button only when `awaiting == "continue"`, End episode secondary, both disabled while pending); `TurnBanner.test.tsx` (`role="status"`, "Your turn" / "Lucía is speaking" / "Episode finished"); `PodcastLabel.test.tsx` ("Podcast · One host · Lucía").
- [X] T050 [P] [US1] Write page tests: `frontend/src/pages/Podcasts.test.tsx` (show cards from the catalogue; choosing one navigates to `/podcasts/setup?show={id}`), `frontend/src/pages/PodcastSetup.test.tsx` (format starts on `last_format`, length on the default, learner name prefilled from preferences, **Start episode** posts the draft and navigates to `/podcasts/episodes/{id}`; an unknown `show` id returns to `/podcasts` with a plain message) and `frontend/src/pages/PodcastEpisode.test.tsx` (One host: input bar with `RecordButton`, suggestions and helper at the learner's turn; learning tools on host lines; a recording is transcribed with the episode's `language`, not the current practice-language setting, as `Chat.tsx` does with the conversation's language, FR-029). Extend `frontend/src/pages/Home.test.tsx` (a "Podcasts" nav pill linking to `/podcasts`) and `frontend/src/pages/History.test.tsx` (a podcast row shows `PodcastLabel` and links to `/podcasts/episodes/{id}`; roleplay rows unchanged).
- [X] T051 [P] [US1] Write E2E, with all API calls mocked via `page.route()`:
  - new `frontend/e2e/podcasts.spec.ts`: Home → Podcasts shows ≥ 6 cards with title, topic, hosts and role; choosing *Weekend Food Talk* opens setup on One host and Medium; Start episode lands on the episode;
  - new `frontend/e2e/podcast-episode.spec.ts`, One host: the opening line with the host's name, reply by typing, the host's reply, End episode shows the sign-off and "Episode finished"; a provider `error` frame shows the message and Retry produces the line; a host with `is_voice_available: false` shows the voice message and the line stays readable;
  - extend `frontend/e2e/home.spec.ts` (the Podcasts pill) and `frontend/e2e/history.spec.ts` (a podcast row reads "Podcast · One host · Lucía" and links to the episode).

### Implementation for User Story 1

- [X] T052 [US1] Implement `backend/app/podcasts/schemas.py`: `HostDraftModel`, `ShowDraftModel`, `CatalogResponse`, `PreferencesResponse`, `UpdatePreferencesRequest` (`learner_name` 1–40 characters after trimming or `""` to clear; `is_show_text_on`; `interests`), `StartEpisodeRequest` (`format` and `length` with patterns built from the catalogues), `EpisodeResponse`, `EpisodeLineModel`, `EpisodeSummaryRow`; the line-frame builder. Validation of the draft against data-model §6 is a `validate_draft(draft, language, installation)` function returning plain 422 messages that name the host and field.
- [X] T053 [US1] Implement the catalogue and preferences endpoints in `backend/app/podcasts/router.py` (`APIRouter(prefix="/api/podcasts")`): `GET /catalog` (casting each show with `HostCaster` for the current practice language; `voices` with `installed_count`, and the notices left `null` until US2's T071), `GET /preferences`, `PUT /preferences` (passes T040, T041).
- [X] T054 [US1] Implement `backend/app/podcasts/services/episode_turns.py`: `EpisodeTurns`, the service object the router delegates to (as `_RoleplayContext` does for chat). It loads the episode state, asks `TurnPolicy` for the cue, builds the `TurnRequest` (`SessionKey(SessionKind.PODCAST, str(id))`, standing prompt, history from `cues.py`), runs it through `relay_engine_reply`-style collection, sanitises, regenerates once when empty, stores the line through `PodcastStorage` **before** the frame, calls `engine.end(key)` when trimmed, schedules speech in the host's voice with `schedule_speech` and `provider_for_voice`, and completes the conversation after a `sign_off`. Every method ≤ 20 lines.
- [X] T055 [US1] Implement the episode endpoints in `backend/app/podcasts/router.py` (passes T042–T047): `POST /episodes` (create through storage, write `last_format` and `learner_name`), `GET /episodes`, `GET /episodes/{id}`, and the SSE actions `/next`, `/message` (using `save_learner_message`, `plan_learner_turn` and `Corrections` from `app.conversation_turns`), `/end`, plus `/session` (via `start_warming`) and `/suggestions` (the roleplay suggestion prompt over a host-labelled transcript, with `with_learner_text_rules`; 409 in Listen). Every action takes the episode lock and returns 409 with the contracts §7 details when the turn state forbids it.
- [X] T056 [US1] Include `app.podcasts.router` in `backend/app/main.py`. Run the US1 backend tests: T040–T047 pass.
- [X] T057 [P] [US1] Implement the API functions in `frontend/src/services/podcastsApi.ts` (passes T048's API tests), reusing the SSE reader pattern of `streamChatMessage` in `frontend/src/services/api.ts`.
- [X] T058 [US1] Implement `frontend/src/hooks/podcasts/usePodcastCatalog.ts`, `usePodcastPreferences.ts` and `usePodcastEpisode.ts` (TanStack Query for reads; the turn state machine in `usePodcastEpisode`, every function ≤ 20 lines, with helpers for frame handling) (passes T048's hook tests).
- [X] T059 [P] [US1] Implement the components in `frontend/src/components/podcasts/`: `ShowCard.tsx`, `FormatFieldset.tsx`, `LengthFieldset.tsx`, `HostCard.tsx` (display only), `LearnerNameField.tsx`, `HostLine.tsx` (wraps `MessageBubble`, which is not modified), `EpisodeControls.tsx` (Continue and End episode), `TurnBanner.tsx` and `PodcastLabel.tsx` (passes T049).
- [X] T060 [US1] Implement `frontend/src/pages/Podcasts.tsx`, `frontend/src/pages/PodcastSetup.tsx` and `frontend/src/pages/PodcastEpisode.tsx`, and add the routes `/podcasts`, `/podcasts/setup` and `/podcasts/episodes/:conversationId` to `frontend/src/App.tsx`. The episode page reuses `RecordButton`, `SuggestedResponsePanel`, `ExpressionHelperPanel`, `FeedbackNote`, `ConversationLevelControl` and `VoiceUnavailableNotice` as they are, and focuses Continue after a line arrives (passes T050's page tests).
- [X] T061 [US1] Add the "Podcasts" nav pill next to Past Chats in `frontend/src/pages/Home.tsx` (one `<Link className="nav-pill">`), and in `frontend/src/pages/History.tsx` fetch `listEpisodes()` through a new `frontend/src/hooks/podcasts/usePodcastEpisodeIndex.ts` and render `PodcastLabel` and the episode link for podcast rows (the two-line change recorded in plan.md Complexity Tracking; passes T050's Home and History tests).
- [X] T062 [US1] Run `npm run lint`, `npm run build`, `npm test` and `npm run test:e2e` from `frontend/`; T048–T051 pass with every existing spec.
- [X] T063 [P] [US1] Create the hand-run harness `backend/tests/integration/podcasts/podcast_harness.py` (real provider, real voices; drives `/next` and `/message` with scripted learner replies from a small per-language set) and the benchmarks `backend/tests/integration/podcasts/test_host_language_benchmark.py` (SC-005: ≥ 95% of host lines with no flagged foreign word, reusing `backend/tests/integration/practice_languages/text_purity.py`, both languages) and `backend/tests/integration/podcasts/test_host_level_benchmark.py` (SC-006: host lines vs roleplay replies at each level below Natural, reusing `backend/tests/integration/conversation_levels/text_metrics.py`), both `@pytest.mark.benchmark`.
- [ ] T064 [US1] Run T063 against `llama3.1:8b` (`backend/.venv/bin/pytest -m benchmark tests/integration/podcasts -k "language or level" -s`) **before building further on host-line quality** (plan § phase order). Record the printed tables for T127.
- [ ] T065 [US1] Run the full backend and frontend suites. Walk quickstart §4 steps 1, 2 and 4 by hand.

**Checkpoint**: One host works end to end and is resumable from Past Chats. This is the MVP.

---

## Phase 4: User Story 2 — Learner listens to two hosts and advances at their own pace (Priority: P1)

**Goal**: A Listen episode: two hosts with different personalities and voices talk to each other,
each line waits for Continue, lines are hidden until tapped or until Show text is on, and the
episode ends with a sign-off at the chosen length. When the language has fewer than two voices,
the setup screen says so before a two-host episode starts.

**Independent Test**: Start any ready-made show in Listen and press Continue to the sign-off. The
hosts alternate naturally, each line plays in its speaker's voice, the voices differ, and nothing
but Continue is ever asked of the learner (spec US2).

### Tests for User Story 2 (write first, see them fail)

- [X] T066 [P] [US2] Write `backend/tests/integration/podcasts/test_listen_episode.py` (FR-015, FR-016, FR-019, US2):
  - both hosts are stored; the opening is the lead's `open`, the second line the second host's `greet`;
  - every `done` frame has `turn == "hosts"` and `awaiting == "continue"` until the end; no line invites the learner;
  - on a Short episode, the wrap-up comes within 2 host lines of 10, the line after it is `sign_off`, and that finishes the episode (`turn == "finished"`, conversation `completed`);
  - no host speaks more than three lines in a row;
  - `/message` → 409 "This is a listening episode. Start the show in One host or Panel to speak."; `/pass` → 409; `/suggestions` → 409;
  - `/end` mid-episode gives a sign-off and finishes.
- [X] T067 [P] [US2] Write `backend/tests/integration/podcasts/test_reveal_and_show_text.py` (FR-043, contracts §2, §8): `POST /episodes/{id}/lines/{message_id}/reveal` returns 204, sets `is_revealed` in `GET /episodes/{id}`, and is idempotent; 404 for a learner message, another episode's line, or an unknown id; `PUT /preferences {"is_show_text_on": true}` persists across a new session factory. Extend `backend/tests/contract/test_podcasts_catalog_api.py` (contracts §1, spec edge case "fewer than two voices"): with a fake installation of one voice, `shared_voice_notice` is non-null and both hosts share the voice; with none, `unavailable_message` is non-null; with two, both are `null`. `GET /episodes/{id}` of a Listen episode whose hosts share one voice carries the same `shared_voice_notice`.
- [X] T068 [P] [US2] Write Vitest tests: extend `frontend/src/components/podcasts/HostLine.test.tsx` (Listen with `isTextShown` false: the words are hidden, the line is a button named "Show Lucía's line", replay works while hidden, tapping reveals and calls `onReveal`; translation and lookup appear only once revealed; a host with `is_voice_available: false` is shown in full, plan interpretation 5); new `frontend/src/components/podcasts/ShowTextSwitch.test.tsx` (a labelled switch reflecting and updating the preference); extend `frontend/src/hooks/podcasts/usePodcastEpisode.test.tsx` (`reveal(messageId)` updates the line; Listen never exposes `send`); extend `frontend/src/pages/PodcastEpisode.test.tsx` (Listen shows no input bar, shows the Show text switch, and Continue is the only primary action); extend `frontend/src/pages/PodcastSetup.test.tsx` (with the catalogue's `shared_voice_notice` set, the notice renders with `role="status"` when Panel or Listen is selected and not for One host; with `unavailable_message` set, that message renders).
- [X] T069 [P] [US2] Extend `frontend/e2e/podcast-episode.spec.ts`, Listen: lines appear with the speaker's name and hidden words; tapping one reveals it and posts the reveal; Continue plays the next line; turning on Show text shows every line and the PUT carries `is_show_text_on: true`; a new Listen episode with the mocked preference on starts with text shown; Continue through to the sign-off shows "Episode finished". Extend `frontend/e2e/podcasts.spec.ts`: with the mocked catalogue's `shared_voice_notice`, choosing Listen on the setup screen shows the notice before starting.

### Implementation for User Story 2

- [X] T070 [US2] Extend `EpisodeTurns` and `backend/app/podcasts/router.py` for Listen (passes T066): the Listen `sign_off` after `wrap_up` finishes the episode, and `/message`, `/pass` and `/suggestions` return the Listen 409s, driven by the format descriptor's `is_learner_speaking` and never by `format == "listen"`.
- [X] T071 [US2] Add `POST /api/podcasts/episodes/{id}/lines/{message_id}/reveal` to `backend/app/podcasts/router.py`, `is_show_text_on` handling to the preferences endpoints, and the `shared_voice_notice` and `unavailable_message` values to `GET /catalog` and `EpisodeResponse`, both derived from `installed_count` (passes T067).
- [X] T072 [US2] Add `revealLine` to `frontend/src/services/podcastsApi.ts`; implement the hidden and revealed states in `frontend/src/components/podcasts/HostLine.tsx`, the new `frontend/src/components/podcasts/ShowTextSwitch.tsx`, `reveal` in `usePodcastEpisode.ts`, the Listen layout of `frontend/src/pages/PodcastEpisode.tsx`, and the shared-voice and no-voice notices on `frontend/src/pages/PodcastSetup.tsx` (passes T068, T069).
- [X] T073 [P] [US2] Write the benchmarks `backend/tests/integration/podcasts/test_single_speaker_benchmark.py` (SC-003, Listen half: 10 Listen episodes, 0 stored lines with another participant's label or speech, the `was_trimmed` rate recorded) and `backend/tests/integration/podcasts/test_podcast_latency_benchmark.py` (SC-009 "starts playing": p90 from the `/next` request to the line's audio being ready, i.e. `GET /api/audio/tts/{message_id}` returning 200 with the WAV, ≤ 5 s over 50 presses; also prints the time to the `line` frame and the synthesis share separately, so a miss can be attributed to the model or to TTS; records `prompt_eval_count` on one Long episode, research R14), both `@pytest.mark.benchmark`, using `podcast_harness.py`.
- [ ] T074 [US2] Run T073 against `llama3.1:8b` and record the tables for T127. Run the full suites, and walk quickstart §4 step 5 and step 10 (the voice edge cases, whose setup notice ships in this story).

**Checkpoint**: One host and Listen both work independently.

---

## Phase 5: User Story 6 — Learner catches up with a summary of the conversation so far (Priority: P2)

**Goal**: A Summary button in the header of roleplay conversations and podcast episodes opens a
short, grounded summary of the lines so far, in the conversation's language or English, with the
choice remembered. Opening it changes nothing in the conversation.

**Independent Test**: In a roleplay conversation and a Panel (or One host) episode with at least
eight lines, open Summary: it covers the main points and nothing unsaid, in simple sentences;
English shows the same points; after two more lines the summary includes them (spec US6).

### Tests for User Story 6 (write first, see them fail)

- [ ] T075 [P] [US6] Write `backend/tests/unit/conversation_summary/test_parser.py`: a structured reply with 1–5 points, each with `conversation_language` and `english`, parses to `SummaryPoint`s; 0 points, more than 5, a missing version or malformed JSON raise the module's `SummaryUnavailable` (an `LLMError` subclass with a plain retry message, so it surfaces as 503).
- [ ] T076 [P] [US6] Write `backend/tests/unit/conversation_summary/test_fold.py` (research R13): a transcript under the chunk budget (a named constant, ≈ 6,000 characters) is one call; a longer one is folded in chunks, each call getting the previous step's English points plus the next chunk, and no prompt exceeds the budget; with a cached summary only the lines after `up_to_message_id` are folded in.
- [ ] T077 [P] [US6] Write `backend/tests/unit/conversation_summary/test_prompts.py`: the prompt holds only the labelled transcript and the rules (use only what was said; ≤ 5 points; end with where the conversation stands; name the host behind each point when names are given); the conversation-language instruction carries `with_learner_text_rules()` for the level plus the "short, simple sentences" rule, which is present at Natural too (FR-039); language names, never codes.
- [ ] T078 [P] [US6] Write `backend/tests/unit/conversation_summary/test_speaker_labels.py`: with `SpeakerNames.names_for(id)` returning `None`, lines are labelled "Learner" and "Partner"; with a mapping, host lines use the host's name and learner lines the learner label.
- [ ] T079 [P] [US6] Write `backend/tests/contract/service_interfaces/test_summary_storage_provider.py` (the `SummaryStorage` ABC: `get_latest(conversation_id)` and `save(summary)`, implemented by SQLite) and `backend/tests/contract/service_interfaces/test_speaker_names.py` (`SpeakerNames` is an ABC with exactly one abstract method, `names_for`; `get_speaker_names()` from the factory returns a `SpeakerNames` backed by the podcast names).
- [ ] T080 [P] [US6] Write `backend/tests/contract/test_conversation_summary_api.py` (contracts §9): the `ready` shape with exactly the keys of contracts §9 and 1–5 points each with both versions; `too_early` with the plain message when fewer than two lines exist, and no model call; 404 for an unknown conversation; 503 with the provider's message on `LLMError`; `conversation_language` is the conversation's, not the current setting.
- [ ] T081 [P] [US6] Write `backend/tests/integration/conversation_summary/test_summary_cache.py` (FR-042, data-model §2.5): a second request with no new line and the same level is a cache hit (no model call); a new line, or a level change, regenerates and replaces the row.
- [ ] T082 [P] [US6] Write `backend/tests/integration/conversation_summary/test_summary_isolation.py` (FR-041): reading a summary adds no message, leaves the conversation's session untouched (`engine.is_live` and the session provider's recorded calls unchanged), and a roleplay and a podcast episode both work, including a `completed` one opened from Past Chats; a podcast summary transcript uses the host names (via `PodcastSpeakerNames`); a summary requested while the episode's `EpisodeLocks` entry is held (a line in progress) returns 200 over the saved lines only, and the lock is still held afterwards (spec edge case "Summary while a line is being produced").
- [ ] T083 [P] [US6] Extend `backend/tests/integration/routers/test_settings.py` (contracts §10): `GET /api/settings` includes `summary_language: "conversation"` by default; `PUT {"summary_language": "native"}` persists; `"en"` or `"x"` → 422; every other field is unchanged. Extend `backend/tests/unit/services/test_sqlite_storage.py` (`AppSettingsRecord.summary_language` round-trips) and `backend/tests/unit/test_database.py` (the `summary_language` column and the `conversation_summaries` table exist after `init_db()`). Extend `backend/tests/integration/podcasts/test_upgrade_preserves_data.py` (T005): after the two `init_db()` runs, `conversation_summaries` exists, `app_settings.summary_language == "conversation"`, and every pre-007 `app_settings` column is unchanged.
- [ ] T084 [P] [US6] Write Vitest tests: `frontend/src/services/api.test.ts` (`getConversationSummary(id)` and `summary_language` on settings); `frontend/src/hooks/useConversationSummary.test.ts` (fetches only when opened, keyed by conversation and last message id, exposes `too_early`, error and retry); `frontend/src/components/chat/SummaryButton.test.tsx` (a secondary text button toggling a panel, `aria-expanded`); `frontend/src/components/chat/SummaryPanel.test.tsx` (a labelled region; a two-option radio group "{Language name}" / "English" starting on `summary_language`, switching shows the other version instantly and saves the setting; the too-early message; an error with Retry); extend `frontend/src/pages/Chat.test.tsx` (the header has a Summary button).
- [ ] T085 [P] [US6] Write E2E: new `frontend/e2e/conversation-summary.spec.ts` (a roleplay summary; a podcast summary naming hosts; the too-early message; switching to English and back; the English choice is remembered in another conversation via the mocked settings PUT; closing the panel leaves the transcript and turn state unchanged, with no extra requests to `/message` or `/next`), and extend `frontend/e2e/chat.spec.ts` (the Summary button is present and nothing else in Chat changes).

### Implementation for User Story 6

- [ ] T086 [US6] Add `summary_language` to `AppSettings` in `backend/app/models/app_settings.py` (`String(12)`, default `DEFAULT_SUMMARY_LANGUAGE = "conversation"`), the `_ADDITIVE_COLUMNS` entry `("app_settings", "summary_language VARCHAR(12) NOT NULL DEFAULT 'conversation'")` in `backend/app/database.py`, `summary_language: str = DEFAULT_SUMMARY_LANGUAGE` on `AppSettingsRecord` in `backend/app/services/storage/base.py`, the field in `_settings_to_record` in `backend/app/services/storage/sqlite.py` (14 → 15 lines), and in `backend/app/routers/settings.py` the response field in `_to_response` (14 → 15 lines) and `summary_language` with pattern `^(conversation|native)$` on `UpdateSettingsRequest` (passes T083).
- [ ] T087 [US6] Implement `backend/app/conversation_summary/models.py` (`conversation_summaries`: `conversation_id` INTEGER PK FK → `conversations.id` ON DELETE CASCADE; `up_to_message_id` INTEGER NOT NULL; `level` VARCHAR(12) NOT NULL; `points` TEXT NOT NULL, a JSON array of 1–5 `{conversation_language, english}` pairs; `created_at` DATETIME NOT NULL), register it in `init_db()`, and implement `services/storage.py` (the `SummaryStorage` ABC and `StoredSummary` record) and `services/sqlite_storage.py` (passes T079's storage half).
- [ ] T088 [US6] Run `backend/tests/integration/podcasts/test_upgrade_preserves_data.py`, `backend/tests/unit/test_database.py` and `backend/tests/integration/routers/test_settings.py`: T083 passes with T086 and T087, and every pre-existing settings test passes unchanged.
- [ ] T089 [US6] Implement `backend/app/conversation_summary/prompts.py` (the prompt and JSON schema) and `backend/app/conversation_summary/services/summariser.py` (`Summariser(structured_llm, storage, speaker_names)`: transcript labelling, fold, parse, cache check; `SummaryUnavailable`; the `SpeakerNames` ABC in `services/speaker_names.py`) (passes T075–T078).
- [ ] T090 [US6] Implement `PodcastSpeakerNames` in `backend/app/podcasts/services/speaker_views.py`, with `names_for(conversation_id) -> Mapping[int, str] | None` (host names by message id; `None` for a non-episode), and export it from `backend/app/podcasts/__init__.py`. It does **not** subclass `SpeakerNames`: `app.podcasts` and `app.conversation_summary` never import each other (plan.md Principle V row). `backend/app/services/factory.py` composes them with a three-line `_PodcastSpeakerNamesAdapter(SpeakerNames)` that delegates `names_for`. Passes T079's `SpeakerNames` half.
- [ ] T091 [US6] Implement `backend/app/conversation_summary/router.py` (`GET /api/conversations/{conversation_id}/summary`, using the conversation's language and the current level) and export `router` and `SpeakerNames` from `backend/app/conversation_summary/__init__.py`; add `get_summary_storage` and `get_speaker_names` to `backend/app/services/factory.py`; include the router in `backend/app/main.py` (passes T080–T082).
- [ ] T092 [US6] Implement the frontend: `getConversationSummary` and `summary_language` in `frontend/src/services/api.ts`; `frontend/src/hooks/useConversationSummary.ts`; `frontend/src/components/chat/SummaryButton.tsx` and `SummaryPanel.tsx` (non-modal, above the transcript); add `<SummaryButton conversationId={convId} />` to the header of `frontend/src/pages/Chat.tsx` (the single element recorded in plan.md Complexity Tracking) and to `frontend/src/pages/PodcastEpisode.tsx`. Add `summaryFixture` to `frontend/e2e/fixtures.ts` (passes T084, T085).
- [ ] T093 [P] [US6] Write `backend/tests/integration/conversation_summary/test_summary_benchmark.py` (SC-014: p90 ≤ 10 s over 20 summaries; prints rows for the review sheet) and create `specs/007-podcast-mode/summary-review-sheet.md` (SC-012, SC-013: 20 summaries, 10 roleplay and 10 podcast, both languages; columns for invented statements, main points covered, same points in both versions, level limits met).
- [ ] T094 [US6] Run T093 against `llama3.1:8b`, fill the review sheet, and record the results for T127. Run the full suites and walk quickstart §4 step 3.

**Checkpoint**: Summary works in roleplay and in every episode format built so far.

---

## Phase 6: User Story 3 — Learner joins a panel with two hosts (Priority: P2)

**Goal**: A Panel episode: two hosts and the learner. Hosts sometimes talk to each other, always
bring the learner back within four lines, answer when named, and let the learner Jump in or Pass.

**Independent Test**: Run a Panel episode for ten learner turns. The learner is invited within four
host lines every time, both hosts take part, and a learner message naming one host is answered by
that host (spec US3).

### Tests for User Story 3 (write first, see them fail)

- [ ] T095 [P] [US3] Write `backend/tests/integration/podcasts/test_panel_episode.py` (FR-013–FR-018, contracts §6–§7, data-model §4):
  - the opening is the lead's `open`, then the second host's `greet`;
  - with a scripted learner replying at every invitation, the learner is invited within four host lines every time, and `can_jump_in`/`can_pass` follow the turn state;
  - `/message` at `hosts/continue` (Jump in) is accepted, the learner line is stored, and a host responds straight away;
  - `/pass` at the learner's turn marks the invitation `is_passed`, produces the next host line, and the count to the next invitation restarts; `/pass` at the hosts' turn → 409;
  - a learner line naming the second host ("Marco, ¿y tú?") is answered by the second host;
  - an invitation after two lines from different hosts is rendered as a settle invite in the cue the scripted writer received;
  - on a Short episode, after the `wrap_up`, the learner can still reply and Continue still produces host lines; the episode stays `active` until `/end` (plan interpretation 4).
- [ ] T096 [P] [US3] Write Vitest tests: extend `frontend/src/components/podcasts/EpisodeControls.test.tsx` (Panel: Jump in at the hosts' turn, Pass at the learner's turn, both secondary; neither in One host or Listen); extend `frontend/src/hooks/podcasts/usePodcastEpisode.test.tsx` (`jumpIn()` switches the screen to the learner's turn without a request; `pass()` streams `/pass`); extend `frontend/src/pages/PodcastEpisode.test.tsx` (suggestions and the helper appear after Jump in, plan interpretation 9).
- [ ] T097 [P] [US3] Extend `frontend/e2e/podcast-episode.spec.ts`, Panel: Continue plays the next host line and the banner names the speaker; an inviting line switches the banner to "Your turn"; Pass sends `/pass` and the hosts carry on; Jump in while the hosts are talking opens the input and sending posts `/message`; a message naming a host is followed by that host's mocked line.

### Implementation for User Story 3

- [ ] T098 [US3] Add `POST /api/podcasts/episodes/{id}/pass` to `backend/app/podcasts/router.py` and `EpisodeTurns.pass_turn()`; accept `/message` at `hosts/continue` when the format `has_jump_in`; expose `can_jump_in` and `can_pass` in `EpisodeResponse` and the `done` frames (passes T095).
- [ ] T099 [US3] Add `streamEpisodePass` to `frontend/src/services/podcastsApi.ts`, `jumpIn` and `pass` to `usePodcastEpisode.ts`, Jump in and Pass to `EpisodeControls.tsx`, and the Panel layout to `PodcastEpisode.tsx` (passes T096, T097).
- [ ] T100 [P] [US3] Write `backend/tests/integration/podcasts/test_panel_turn_taking_benchmark.py` (SC-002: 10 Panel episodes × 10 learner turns; every `invites_learner` line addresses the learner, flagged lines printed for a human check; each host ≥ 25% of lines) and extend `test_single_speaker_benchmark.py` with the Panel half of SC-003 (10 Panel episodes), both `@pytest.mark.benchmark`.
- [ ] T101 [P] [US3] Extend `backend/tests/live/test_claude_code_live.py` with a `claude_live` podcast check (FR-033): a Panel opening, one Continue and one learner reply succeed on Claude, and the second `/next` reuses the live session (one `claude` process for the episode).
- [ ] T102 [US3] Run T100 against `llama3.1:8b` (and T101 if Claude is available) and record the results for T127. Run the full suites and walk quickstart §4 step 6 and step 9.

**Checkpoint**: All three formats work. US1, US2, US3 and US6 are independently testable.

---

## Phase 7: User Story 4 — Learner creates a podcast from an idea or asks for a surprise (Priority: P2)

**Goal**: The learner generates a show from an idea, asks for another version, or presses Surprise
me for a suggestion that leans towards their saved interests. Unsuitable or empty ideas are declined
in plain language with the offer of Surprise me.

**Independent Test**: Enter ten ideas and press Surprise me ten times. Each gives a complete,
playable show on the idea (or varied for Surprise me), with distinct hosts whose names suit the
practice language (spec US4).

### Tests for User Story 4 (write first, see them fail)

- [ ] T103 [P] [US4] Write `backend/tests/unit/podcasts/test_generator.py` (research R9), with a scripted `StructuredLLMProvider`:
  - a suitable reply becomes a `ShowDraft` with `source == "generated"`, `show_id is None`, the model's title, premise, topic, `learner_role` and per-host personality and `angle`, and names and voices cast by `HostCaster` whatever names the model wrote;
  - a duplicate personality is replaced by the catalogue's next one;
  - the prompt contains the idea, the learner's interests when present, and every `avoid_titles` entry;
  - `is_suitable: false` raises `ShowDeclined`; its `decline_reason` is logged and not in the exception's message;
  - malformed JSON or an unknown enum raises an `LLMError` subclass with a plain retry message.
- [ ] T104 [P] [US4] Write `backend/tests/unit/podcasts/test_surprise.py` (FR-022, FR-023, plan interpretation 7): with interests, ≥ 60% of 300 seeded draws take their topic from the interests; without, every topic is one of the 40 built-in topics; every angle is one of the 12 built-in angles; `RecentSurprises` never returns one of the last 10 (topic, angle) pairs; 20 consecutive draws give ≥ 15 distinct pairs (SC-008).
- [ ] T105 [P] [US4] Write `backend/tests/contract/test_podcast_generation_api.py` (contracts §3): `POST /shows/generate` with `"   "` or 201 characters → 422 "Type a few words about the show you'd like, or press Surprise me." with no model call; a declined idea → 422 with `detail` "That idea can't become a show here. Try a different topic, or press Surprise me." and `can_surprise: true`; a suitable idea → 200 `ShowDraft`; `POST /shows/surprise` → 200 with `source == "surprise"`; malformed model JSON → 503; nothing is written to any podcast table by either endpoint.
- [ ] T106 [P] [US4] Extend `backend/tests/contract/test_podcast_preferences_api.py` (contracts §2, FR-023): interests are trimmed and de-duplicated case-insensitively; 11 items → 422 naming the limit; an item over 40 characters → 422 naming it; an empty list clears them. Add `backend/tests/integration/podcasts/test_interests_not_inferred.py`: a roleplay conversation and a saved word leave the interests unchanged.
- [ ] T107 [P] [US4] Write Vitest tests: `frontend/src/components/podcasts/ShowGenerator.test.tsx` (a labelled idea input, Generate and Surprise me; a pending state; a 422 shows the detail with `role="alert"` and a Surprise me offer); `frontend/src/components/podcasts/InterestsEditor.test.tsx` (a "Your interests" disclosure; add, edit and clear; a 422 shows its message); `frontend/src/hooks/podcasts/useShowDraft.test.tsx` (generate, surprise, another version with `avoid_titles` of every previous title); extend `frontend/src/pages/PodcastSetup.test.tsx` (a draft in router state shows "Another version" only for `generated`; reload without a draft returns to `/podcasts` with a plain message).
- [ ] T108 [P] [US4] Extend `frontend/e2e/podcasts.spec.ts`: generate "living abroad as a nurse" → setup with the draft; Another version → a different mocked title and the request carries `avoid_titles`; a blank idea and a declined idea each show the message and Surprise me; add interests "football, cooking" and the PUT carries them; Surprise me → setup with the surprise draft.

### Implementation for User Story 4

- [ ] T109 [US4] Add the generator prompt and JSON schema to `backend/app/podcasts/prompts.py`, and implement `backend/app/podcasts/services/generator.py` (`ShowGenerator(structured_llm, caster)` with `generate(idea, interests, avoid_titles, language)`, `ShowDeclined`) (passes T103).
- [ ] T110 [US4] Implement `backend/app/podcasts/services/surprise.py` (`SurpriseTopics(rng)` with the 40 topics and 12 angles as named tuples, `RecentSurprises` with `SURPRISE_HISTORY_SIZE = 10`), and add `get_recent_surprises()` (a process-wide singleton) to `backend/app/services/factory.py` (passes T104).
- [ ] T111 [US4] Add `POST /api/podcasts/shows/generate` and `POST /api/podcasts/shows/surprise` to `backend/app/podcasts/router.py` (`IDEA_MAX_LENGTH = 200`), and the interests validation (`MAX_INTERESTS = 10`, `INTEREST_MAX_LENGTH = 40`) to `UpdatePreferencesRequest` in `backend/app/podcasts/schemas.py` (passes T105, T106).
- [ ] T112 [US4] Implement `generateShow`, `surpriseShow` and interests in `frontend/src/services/podcastsApi.ts`; `frontend/src/hooks/podcasts/useShowDraft.ts`; `frontend/src/components/podcasts/ShowGenerator.tsx` and `InterestsEditor.tsx`; add them to `Podcasts.tsx`; pass generated drafts to setup in router state and add Another version to `PodcastSetup.tsx` (passes T107, T108).
- [ ] T113 [P] [US4] Write `backend/tests/integration/podcasts/test_generator_benchmark.py` (SC-007: ≥ 18 of 20 ideas on topic and playable end to end with distinct, language-appropriate names; SC-008: 20 Surprise me presses give ≥ 15 distinct topics and distinct titles), `@pytest.mark.benchmark`.
- [ ] T114 [US4] Run T113 against `llama3.1:8b` and record the results for T127. Run the full suites and walk quickstart §4 step 7.

**Checkpoint**: Shows come from the catalogue, the generator and Surprise me alike.

---

## Phase 8: User Story 5 — Learner shapes the hosts before starting (Priority: P3)

**Goal**: On the setup screen the learner can shuffle a host, change a host's personality and hear
a sample of the host's voice. Two hosts never share a name, a voice (when two are installed) or a
personality. (The shared-voice notice ships earlier, with Listen in US2.)

**Independent Test**: On a Panel setup, shuffle each host three times and change one personality.
The hosts always differ in name, voice and personality, and the episode uses the final choices
(spec US5).

### Tests for User Story 5 (write first, see them fail)

- [ ] T115 [P] [US5] Extend `backend/tests/unit/podcasts/test_casting.py` with `HostCaster.recast(slot, hosts, learner_name)` (research R6, plan interpretation 6): the new host differs from the other host and from the replaced host in name and personality, never has the learner's name, keeps its voice when no third voice differs from the other host's, and three seeded shuffles in a row never clash.
- [ ] T116 [P] [US5] Write `backend/tests/contract/test_podcast_hosts_api.py` (contracts §4, §5): `POST /hosts/shuffle` returns a `HostDraft` for the slot satisfying T115's rules; `GET /voice-sample?voice_key=…&name=…` returns `audio/wav` spoken in that voice (`RecordingTtsBuilder`), with the language's `sample_line`, cached by `(voice_key, name)` so a second call does not synthesise; an uninstalled voice → 503; an unknown voice → 422.
- [ ] T117 [P] [US5] Extend `backend/tests/integration/podcasts/test_one_host_episode.py` (the voice notices are tested in US2's T067): an episode started with a changed personality stores it, and the standing prompt the scripted writer receives carries that personality's speaking style (US5-3).
- [ ] T118 [P] [US5] Write Vitest tests: extend `frontend/src/components/podcasts/HostCard.test.tsx` (Shuffle, a labelled personality `<select>` excluding the other host's personality, a ▶ sample button with an accessible name "Play Lucía's voice"); extend `frontend/src/pages/PodcastSetup.test.tsx` (shuffling replaces only that host; Start posts the final hosts).
- [ ] T119 [P] [US5] Extend `frontend/e2e/podcasts.spec.ts`: on a Panel setup, shuffle each host and change one personality, then Start posts those hosts.

### Implementation for User Story 5

- [ ] T120 [US5] Add `HostCaster.recast` to `backend/app/podcasts/services/casting.py` (passes T115).
- [ ] T121 [US5] Add `POST /api/podcasts/hosts/shuffle` and `GET /api/podcasts/voice-sample` (synthesis through `provider_for_voice` and `voice_sample_line`, cached under the TTS cache directory by `(voice_key, name)`) to `backend/app/podcasts/router.py` (passes T116, T117).
- [ ] T122 [US5] Add `shuffleHost` and `voiceSampleUrl` to `frontend/src/services/podcastsApi.ts`, the controls to `frontend/src/components/podcasts/HostCard.tsx`, and the host state to `frontend/src/pages/PodcastSetup.tsx` (passes T118, T119).
- [ ] T123 [US5] Create `specs/007-podcast-mode/speaker-review-sheet.md` (SC-004: 10 Panel or Listen episodes with name labels stripped; a column per line for the reviewer's guess and the true speaker; the bar is ≥ 80% correct), fill it from a benchmark-harness run, and record the result for T127.
- [ ] T124 [US5] Run the full suites and walk quickstart §4 step 8.

**Checkpoint**: All six stories work independently.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Guards, documentation, accessibility and end-to-end validation across all stories.

- [ ] T125 [P] Write `backend/tests/unit/test_module_boundaries.py` (Principle V, standing rules): scan `backend/app/**/*.py` imports and fail on any import of `app.podcasts.<submodule>` or `app.conversation_summary.<submodule>` from outside that package other than from `backend/app/services/factory.py` (the composition root, standing rules), on `app.podcasts` importing `app.conversation_summary` or the reverse, on `app/routers/audio.py` importing `app.podcasts`, and on `PodcastMessageVoices(` or `PodcastSpeakerNames(` constructed outside `backend/app/services/factory.py`.
- [ ] T126 [P] Enforce the 20-line limit (Constitution I) on everything this feature adds or modifies:
  - write `backend/tests/unit/test_function_length.py`, measured with `ast` as `end_lineno - lineno + 1`, the inclusive count plan.md's Function-length plan uses. **Whole files**: `backend/app/podcasts/`, `backend/app/conversation_summary/`, `backend/app/conversation_turns/`, `backend/app/routers/audio.py`, `backend/app/routers/chat.py`, `backend/app/routers/settings.py`, `backend/app/services/tts/selection.py`, `backend/app/services/tts/base.py`, `backend/app/services/factory.py`, `backend/app/services/conversation/session.py`, `backend/app/practice_languages/` and `backend/app/models/app_settings.py`. **Named functions only** in `backend/app/database.py` (`init_db`) and `backend/app/services/storage/sqlite.py` (`_settings_to_record`), because those files hold pre-existing long functions this feature does not touch (`create_conversation`, `save_message`, `get_or_create_learning_result`, `save_vocabulary_item`). If a whole-file entry turns out to contain a pre-existing long function, move that file to the named list rather than fixing unrelated code here;
  - add an `overrides` entry to `frontend/.eslintrc.json` applying `"max-lines-per-function": ["error", {"max": 20, "skipBlankLines": true, "skipComments": true}]` to the new frontend files only: `src/pages/Podcast*.tsx`, `src/components/podcasts/**`, `src/hooks/podcasts/**`, `src/hooks/useConversationSummary.ts`, `src/components/chat/Summary*.tsx` and `src/services/podcastsApi.ts`, with `*.test.ts(x)` excluded. `npm run lint` must pass.

  Run this task as early as the files exist (after T022 for the backend, after T060 for the frontend), not only at the end, so over-long functions are split while they are written.
- [ ] T127 [P] Update `docs/architecture.md`: a "Podcasts" section (an episode is a conversation, the turn policy vs the model, cues as user turns, the sanitiser, casting, per-host voices through `MessageVoiceLookup`), a "Conversation summary" section (both languages in one call, folding, caching, isolation), the `conversation_turns` package, and § "Open items" for every benchmark or review result below its bar (T064, T074, T094, T102, T114, T123) and the R14 context measurement.
- [ ] T128 [P] Update `README.md` with a Podcasts section (formats, lengths, generator and Surprise me, Summary) and a note that no new voice download is needed.
- [ ] T129 [P] Update `CLAUDE.md`: a "007-podcast-mode" entry in Recent Changes; `backend/app/podcasts/`, `backend/app/conversation_summary/` and `backend/app/conversation_turns/` in "Domain modules"; the feature list in the Project Overview; point "read the current plan" at `specs/007-podcast-mode/plan.md`.
- [ ] T130 Run the manual accessibility check (quickstart §6) on the Podcasts, setup and episode screens and the Summary panel, in light and dark mode: keyboard order and Continue focus after a line; the turn banner and hidden-line names announced; contrast of host labels and hidden-line placeholders ≥ 4.5:1 with tokens only; touch targets ≥ 44 px at 360 px width. Record the result in the PR description.
- [ ] T131 Run quickstart.md §2–§5 end to end, once with Ollama and once with Claude selected (FR-033): the API smoke check, the full walkthrough with the SC-001 stopwatch, the offline Panel run (SC-010), and the SC-011 comparison against the T003 backup. Record each SC's result in the PR description.
- [ ] T132 Final gate. From `backend/`: `backend/.venv/bin/pytest` (≥ 90% coverage, zero skips), `backend/.venv/bin/ruff check .` and `backend/.venv/bin/black --check .`. From `frontend/`: `npm run lint`, `npm run build`, `npm test` and `npm run test:e2e`. All must pass with zero failures.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T003 must run before any 007 code starts the app. T004
  must finish before T005 can fail for the right reason.
- **Foundational (Phase 2)**: depends on Setup. **It blocks every story.**
- **US1 (Phase 3)**: depends on Foundational. It is the MVP and the base for the episode page.
- **US2 (Phase 4)**: depends on Foundational and on US1's episode endpoints (T055), hooks (T058)
  and episode page (T060). Its backend (T066, T067, T070, T071) can start once T055 is in.
- **US6 (Phase 5)**: depends on Foundational only for roleplay. Its podcast half (the header
  button on `PodcastEpisode.tsx`, `PodcastSpeakerNames`) needs US1's T060. It can run in parallel
  with US2 and US3.
- **US3 (Phase 6)**: depends on US1 (T055, T058, T060). It is independent of US2 and US6.
- **US4 (Phase 7)**: depends on US1's setup page (T060) and catalogue endpoint (T053). It is
  independent of US2, US3 and US6.
- **US5 (Phase 8)**: depends on US1's setup page and catalogue. It is independent of US2–US4, but
  US2's T072, US4's T112 and US5's T122 all edit `PodcastSetup.tsx`, so run them one after
  another.
- **Polish (Phase 9)**: depends on every story. T127 needs the benchmark and review results.

### Within the Foundational phase

- The tests T005–T021 run in parallel, and all fail first (T006's `ChatMessageRequest` identity
  fails until T022).
- T022 (the move) comes first and alone: it touches `chat.py`, and the whole suite must be green
  and unedited before anything else is built on it.
- Catalogue chain: T023 and T024 in parallel; T034 (casting) needs both; T033 (sanitiser) needs
  T024.
- Storage chain: T025 → T026 → T027. T030 needs T027 and T029.
- Core: T031 needs T023; T032 needs T023 and T031.
- T036 needs T027, T030, T034 and T035. T037 needs T036. T038 is independent.

### Within each story

- Test tasks first; confirm they fail.
- Backend before the frontend that calls it (e.g. T057 after T055; T092 after T091).
- Components before pages (T059 before T060).
- Each story ends with a full-suite run and its quickstart steps (T065, T074, T094, T102, T114,
  T124).
- `backend/app/podcasts/router.py` is edited by T053, T055, T070, T071, T098, T111 and T121:
  never run two of these at the same time.

### Parallel Opportunities

- Setup: T001 alongside T002; T004 at any time before T005.
- Foundational: all 17 test tasks (T005–T021) together; after T022, T023, T024, T028, T029, T031,
  T033, T034 and T035 together; T038 at any time.
- US1: the tests T040–T051 together; T057 and T059 alongside the backend T052–T056; the
  benchmarks T063 at any time after T056.
- US2: T066–T069 together.
- US6: T075–T085 together; the backend T086–T091 alongside the frontend tests.
- US3: T095–T097 together; T100 and T101 together.
- US4: T103–T108 together; T109 and T110 together.
- US5: T115–T119 together.
- After US1, the stories US2, US6, US3, US4 and US5 can proceed in parallel if staffed, observing
  the `router.py` and `PodcastSetup.tsx` ordering above.
- Polish: T125–T129 together.

---

## Parallel Example: Foundational tests

```bash
# All foundation tests together (each must fail first):
Task: "T005 upgrade preserves data — backend/tests/integration/podcasts/test_upgrade_preserves_data.py"
Task: "T007 podcast catalogues — backend/tests/unit/podcasts/test_catalog.py"
Task: "T015 turn policy rules — backend/tests/unit/podcasts/test_turn_policy.py"
Task: "T016 turn policy properties — backend/tests/unit/podcasts/test_turn_policy_properties.py"
Task: "T017 prompts and cues — backend/tests/unit/podcasts/test_prompts.py, test_cues.py"
Task: "T018 sanitiser — backend/tests/unit/podcasts/test_sanitiser.py"
Task: "T019 casting — backend/tests/unit/podcasts/test_casting.py"
```

## Parallel Example: User Story 1

```bash
# All US1 tests together (each must fail first):
Task: "T040 catalogue contract — backend/tests/contract/test_podcasts_catalog_api.py"
Task: "T042 One host lifecycle — backend/tests/integration/podcasts/test_one_host_episode.py"
Task: "T044 sessions and rebuilds — backend/tests/integration/podcasts/test_episode_sessions.py"
Task: "T045 sanitising, errors, locks — backend/tests/integration/podcasts/test_episode_lines.py"
Task: "T048 API client and hooks — frontend/src/services/podcastsApi.test.ts, frontend/src/hooks/podcasts/"
Task: "T051 E2E — frontend/e2e/podcasts.spec.ts, podcast-episode.spec.ts"

# Independent implementation files together:
Task: "T057 podcastsApi.ts"
Task: "T059 components/podcasts/*"
Task: "T063 host language and level benchmarks"
```

## Parallel Example: User Story 6

```bash
Task: "T075 summary parser — backend/tests/unit/conversation_summary/test_parser.py"
Task: "T076 fold — backend/tests/unit/conversation_summary/test_fold.py"
Task: "T081 cache — backend/tests/integration/conversation_summary/test_summary_cache.py"
Task: "T082 isolation — backend/tests/integration/conversation_summary/test_summary_isolation.py"
Task: "T084 summary hook and panel — frontend/src/hooks/useConversationSummary.test.ts, frontend/src/components/chat/Summary*.test.tsx"
Task: "T085 summary E2E — frontend/e2e/conversation-summary.spec.ts"
```

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup, including the database backup (T003) and the frozen schema (T004).
2. Phase 2 Foundational. At its checkpoint nothing visible has changed, and the chat suite is
   green and unedited after the move.
3. Phase 3 US1, **including the SC-005 and SC-006 benchmarks (T063–T064)**, run before building
   further on host-line quality.
4. **Stop and validate**: quickstart §4 steps 1, 2 and 4.

### Incremental delivery

1. Foundation → US1 (One host) → demo.
2. + US2: Listen, the first two-voice format.
3. + US6: Summary, in roleplay and episodes.
4. + US3: Panel, the three-person format.
5. + US4: the generator and Surprise me.
6. + US5: shaping hosts.
7. Polish: guards, docs, accessibility and full quickstart validation.

---

## Notes

- **[P]** means a different file with no dependency on an incomplete task. Two [P] tasks never edit
  the same file.
- Every test must be seen failing before its implementation (Red → Green → Refactor), except the
  T022 move, whose net is the existing, unedited chat suite.
- Benchmarks are **deselected** by the existing `-m 'not benchmark and not claude_live'` addopts,
  not skipped. Results below a bar go to `docs/architecture.md` § "Open items" (spec Assumptions:
  "Quality limits carry over").
- Commit after each task or logical group, ending commit messages with the attribution line required
  by the session.
