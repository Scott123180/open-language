---

description: "Task list for 004 LLM Provider Selection and Conversation Sessions"
---

# Tasks: LLM Provider Selection and Conversation Sessions

**Input**: Design documents from `specs/004-llm-provider-selection/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: MANDATORY (constitution Principle III). Every implementation task has a test task
before it that must be written first and seen to FAIL. Unit and contract tests use fakes only: the
default suite needs neither `claude` nor Ollama.

**Organization**: Tasks are grouped by user story. Story phases follow spec priority, with one
deliberate reordering taken from the plan: US5 (sessions, P2) is built on Ollama **before** the Claude
work in US3/US2 (also P2). That way the conversation path is restructured while every existing test
still guards it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: The user story the task belongs to (US1–US6)
- Paths are repo-relative. Backend: `backend/app/`, `backend/tests/`. Frontend: `frontend/src/`,
  `frontend/e2e/`

## Rules that apply to every task

- **20-line function limit** on every new or modified function (constitution v1.2.0). A task that
  touches an existing long function also brings it under 20 lines.
- **No magic strings/numbers**: flags, effort levels, timeouts, pool limits, env prefixes, and user
  messages are named constants.
- **Provider ids** (`"ollama"`, `"claude"`) appear only in `services/llm/catalog.py` and
  `services/llm/registry.py` (Principle VI). Feature code and routers never import a concrete
  provider.
- **Compartmentalization**: `services/conversation/` imports nothing from `services/llm/claude_code/`
  or `services/llm/ollama*.py`. It depends on `services/llm/base.py` only.
- Backend commands run through the venv: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff check
  backend`, `backend/.venv/bin/black --check backend`. Frontend tasks finish with
  `npm test -- --run`, `npm run lint`, and `npm run test:e2e` in `frontend/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration, test markers, and test-support scaffolding used by several stories.

- [X] T001 Write failing tests in `backend/tests/unit/test_config.py` asserting the new `Settings` defaults and env overrides: `claude_executable == "claude"`, `claude_workdir == Path.home() / ".open-language" / "claude-workdir"` and `claude_log_dir == Path.home() / ".open-language" / "claude-logs"` (both expanded like `db_path`, and different directories), `claude_request_timeout_seconds == 120.0`, `session_max_live == 3`, `session_idle_ttl_minutes == 30`, and that `OPEN_LANGUAGE_CLAUDE_EXECUTABLE=/nonexistent` overrides the executable
- [X] T002 Add those six fields to `Settings` in `backend/app/config.py`. Add `claude_workdir` and `claude_log_dir` to the existing `expand_user` validator. Make T001 pass
- [X] T003 [P] Register a `claude_live` marker in `backend/pyproject.toml` (description: "makes real `claude -p` calls against the learner's plan; run by hand") and change `addopts` to `-m 'not benchmark and not claude_live'`. Create `backend/tests/live/__init__.py`
- [X] T004 [P] Create `backend/tests/fixtures/claude_code/` with NDJSON fixtures that reproduce the recorded event shapes from research R-4/R-7/R-14, trimmed to the parsed fields (`type`, `event.delta.type`, `event.delta.text`, `message.error`, `rate_limit_info.status`, `is_error`, `result`, `structured_output`, `api_error_status`): `stream_ok.ndjson` (init, 3 `text_delta` stream_events, `rate_limit_event` status `allowed`, success `result`), `json_ok.ndjson` (single result object), `schema_ok.ndjson` (result with `structured_output` holding a 2-item correction array), `auth_failed.ndjson` (assistant `error: "authentication_failed"`, result `is_error: true`, `result: "Not logged in · Please run /login"`), `model_404.ndjson` (result `is_error: true`, `api_error_status: 404`), `rate_limit_rejected.ndjson` (`rate_limit_event` with `rate_limit_info.status: "rejected"`), `garbage.ndjson` (non-JSON lines, no result), `session_three_turns.ndjson` (three turns each ending in its own `result` line), `auth_status_signed_in.json` (`loggedIn: true`, `authMethod: "claude.ai"`, plus decoy `email`/`orgName` fields), `auth_status_api_key.json` (`loggedIn: true`, `authMethod: "api_key"`), `auth_status_signed_out.json` (`loggedIn: false`)
- [X] T005 [P] Create `backend/tests/support/__init__.py` and `backend/tests/support/claude_fixtures.py` with `load_fixture_lines(name) -> list[str]`, which reads a file from `backend/tests/fixtures/claude_code/`

**Checkpoint**: `backend/.venv/bin/pytest` is green. The `claude_live` marker is deselected.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared contracts that US1, US5, US2, and US4 all build on: the extended
`LLMError`, the conversation-session ABCs and value objects, and the provider catalogue.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests (write first, must FAIL)

- [X] T006 [P] Write failing tests in `backend/tests/unit/services/llm/test_llm_error.py`: `LLMError("x").user_message == "The AI is not responding. Please try again."` (the class constant `DEFAULT_USER_MESSAGE`); `LLMError("x", user_message="Custom")` returns `"Custom"`; `str(LLMError("detail"))` still contains `"detail"`; `LLMError("x").can_retry is True` by default and `LLMError("x", can_retry=False).can_retry is False`. Create `backend/tests/unit/services/llm/__init__.py`
- [X] T007 [P] Write failing tests in `backend/tests/unit/services/conversation/test_session_values.py` (create the package `__init__.py`): `SessionKey(kind=SessionKind.ROLEPLAY, identifier="7")` is frozen and hashable, and `SessionKind` has exactly `roleplay` and `helper`; `SavedTurn` rejects a `role` other than `user`/`assistant`; `SessionFingerprint` instances compare equal only when `selection`, `effort`, and `standing_prompt_digest` all match; `SessionFingerprint.digest_prompt(text)` returns the SHA-256 hex of the text; `TurnRequest` enforces its invariant (either `opening_instruction` is set and `history` has no `user` turns, or the last turn in `history` is a `user` turn) and raises `ValueError` otherwise
- [X] T008 [P] Write failing tests in `backend/tests/unit/services/llm/test_catalog.py`: `PROVIDER_CATALOG` keys are exactly `("ollama", "claude")` in that order; Ollama: `display_name == "Ollama (local)"`, models `llama3.1:8b`, `llama3.2`, `mistral` (label equals id), `default_model == Settings.ollama_model`, `is_local is True`, no effort levels, `default_effort is None`; Claude: `display_name == "Claude (via Claude Code)"`, models `sonnet` "Claude Sonnet", `haiku` "Claude Haiku (fastest)", `opus` "Claude Opus (most capable, uses more of your plan)", `default_model == "sonnet"`, `is_local is False`, effort levels `low` "Low — fastest replies", `medium` "Medium", `high` "High — deeper, slower replies", `default_effort == "low"`; `CLAUDE_MODEL_IDS == frozenset({"sonnet", "haiku", "opus"})`; every descriptor, `ModelOption`, and `EffortOption` is frozen

### Implementation

- [X] T009 [P] Extend `LLMError` in `backend/app/services/llm/base.py`: `DEFAULT_USER_MESSAGE` constant, constructor `LLMError(detail: str, user_message: str = DEFAULT_USER_MESSAGE, can_retry: bool = True)`, read-only `user_message` and `can_retry` properties. Every existing `raise LLMError(str(e))` keeps working unchanged. `can_retry` is how the session pool learns whether a fresh session could fix a failure without importing a concrete provider (FR-S11). Make T006 pass
- [X] T010 [P] Create `backend/app/services/llm/selection_types.py` with the frozen dataclass `LLMSelection(provider_id: str, model: str)` and the effort constants `EFFORT_LOW = "low"`, `EFFORT_MEDIUM = "medium"`, `EFFORT_HIGH = "high"`, `EFFORT_LEVELS = (EFFORT_LOW, EFFORT_MEDIUM, EFFORT_HIGH)`, `DEFAULT_EFFORT = EFFORT_LOW`. This is a leaf module with no app imports, so `conversation/` and `llm/` can both depend on it
- [X] T011 Create `backend/app/services/conversation/session.py`: `SessionKind` (StrEnum `roleplay`, `helper`); frozen dataclasses `SessionKey(kind, identifier)`, `SavedTurn(turn_id, role, content)` (`turn_id` is `"m<message id>"` for roleplay, `"h<index>"` for helper), `SessionFingerprint(selection: LLMSelection, effort: str, standing_prompt_digest: str)` with the `digest_prompt` staticmethod, and `TurnRequest(key, standing_prompt, history: tuple[SavedTurn, ...], guidance: str | None, opening_instruction: str | None)` with its invariant checked in `__post_init__`; and the ABCs `ConversationSession` (`fingerprint`, `synced_turn_ids`, `warm()`, `reply(pending, guidance) -> Iterator[str]`, `reply_to_opening(instruction) -> Iterator[str]`, `acknowledge(turn_id)`, `close()`) and `SessionCapableProvider` (`session_fingerprint(standing_prompt)`, `open_session(standing_prompt, history)`), with signatures exactly as in contracts/api.md §2.6. Create `backend/app/services/conversation/__init__.py` exporting `SessionKey`, `SessionKind`, `SavedTurn`, `TurnRequest`, `SessionFingerprint`, `ConversationSession`, and `SessionCapableProvider`. Make T007 pass (depends on T010)
- [X] T012 Create `backend/app/services/llm/catalog.py`: frozen dataclasses `ModelOption(model_id, label)`, `EffortOption(effort_id, label)`, `ProviderDescriptor(provider_id, display_name, models, default_model, is_local, effort_levels, default_effort)`; the constants `OLLAMA_PROVIDER_ID = "ollama"`, `CLAUDE_PROVIDER_ID = "claude"`, `DEFAULT_PROVIDER_ID = OLLAMA_PROVIDER_ID`, `CLAUDE_MODEL_IDS`; and `PROVIDER_CATALOG: Mapping[str, ProviderDescriptor]` (a `MappingProxyType`, catalogue order Ollama then Claude) with the values from data-model.md §2 and contracts/api.md §1.1. The Ollama default model is read from `get_settings().ollama_model`. Make T008 pass (depends on T010)

**Checkpoint**: The foundation compiles and its tests pass. Nothing uses it yet, so behaviour is unchanged.

---

## Phase 3: User Story 1 — Everything keeps working through the provider layer (Priority: P1) 🎯 MVP

**Goal**: Every language-model request goes through `build_llm_provider()`, driven by the saved
`llm_provider`. The Ollama host setting takes effect. Pre-004 databases come up as Ollama with their
saved model. JSON endpoints report provider failures as 503 with a plain-language message.

**Independent Test**: With no new configuration, the full backend and frontend suites pass. Setting
`OPEN_LANGUAGE_OLLAMA_URL=http://127.0.0.1:9` makes a learning-tool request fail with 503 "The AI is
not responding. Please try again." (quickstart §2).

### Tests for User Story 1 (write first, must FAIL)

- [X] T013 [P] [US1] Write failing tests in `backend/tests/unit/services/test_ollama_llm.py` (rewrite its module-patching tests to inject a fake `ollama.Client`, keeping every existing behavioural assertion): `chat`, `chat_stream`, and `chat_json` call `client.chat` with the same `model`/`messages`/`stream`/`format` arguments as today; a client exception becomes `LLMError` with the default `user_message`; no test patches the `ollama` module
- [X] T014 [P] [US1] Write the shared one-shot provider contract suite in `backend/tests/contract/service_interfaces/test_llm_provider_implementations.py`, parametrised over a `provider_factory` fixture with one id, `ollama` (the `OllamaLLMProvider` over a scripted fake client). Cover contracts/api.md §2.1: (1) `chat(msgs) == "".join(chat_stream(msgs))` for the same scripted output; (2) `chat_stream` yields only non-empty `str`; (3) `json.loads(chat_json(msgs, schema))` succeeds; (4) a backend failure in each of the three methods raises `LLMError` with a non-empty `user_message`; (5) `model_name` returns the model the provider was built with. Structure the parametrisation so US2 adds the `claude` id without editing test bodies
- [X] T015 [P] [US1] Write failing tests in `backend/tests/unit/services/llm/test_registry.py`: `build_llm_provider(LLMSelection("ollama", "llama3.2"), settings)` returns an object that is an `LLMProvider`, a `StructuredLLMProvider`, and a `SessionCapableProvider`, with `model_name == "llama3.2"`; the Ollama client it builds targets `settings.ollama_url` (assert via an injected client-factory seam, not a network call); an unknown `provider_id` raises `UnknownProviderError`, a subclass of `LLMError`
- [X] T016 [P] [US1] Add failing tests to `backend/tests/unit/test_database.py`: `test_pre_004_database_defaults_to_ollama_and_keeps_model` (create an `app_settings` table without the two new columns, insert a row with `llm_model='llama3.1'`, run `_migrate_db`, then read back `llm_provider == 'ollama'`, `llm_effort == 'low'`, and `llm_model == 'llama3.1'`); a fresh database gets `llm_provider` `VARCHAR(20) NOT NULL DEFAULT 'ollama'` and `llm_effort` `VARCHAR(10) NOT NULL DEFAULT 'low'`; `test_migrate_db_applies_every_additive_column` (every `(table, definition)` pair in `_ADDITIVE_COLUMNS` exists after `_migrate_db` on a database created before any of them, which keeps the existing columns covered once the function becomes a loop)
- [X] T017 [P] [US1] Add failing tests to `backend/tests/unit/services/test_sqlite_storage.py`: `get_settings()` on a fresh store returns `AppSettingsRecord` with `llm_provider == "ollama"` and `llm_effort == "low"`; `update_settings(llm_provider="claude", llm_model="sonnet", llm_effort="medium")` persists and returns all three
- [X] T018 [P] [US1] Add failing tests to `backend/tests/integration/routers/test_settings.py`: `GET /api/settings` includes `llm_provider: "ollama"` and `llm_effort: "low"` on a fresh DB, and every existing field is unchanged
- [X] T019 [P] [US1] Write the failing JSON half of `backend/tests/integration/test_llm_error_surface.py`: with `get_llm` overridden by a provider that raises `LLMError("boom")`, `POST /api/learning/grammar`, `POST /api/chat/{id}/suggestions`, and `GET /api/flashcards/words/{id}/info/meanings` (no cache entry) each return **503** `{"detail": "The AI is not responding. Please try again."}`; a provider raising `LLMError("boom", user_message="Custom next step")` yields `{"detail": "Custom next step"}` on all three; a non-LLM exception still yields the existing 500 body. Also update the flashcard tests for the new behaviour (contracts/api.md §1.4): in `backend/tests/integration/flashcards/test_word_library_endpoints.py`, `test_returns_503_when_llm_unavailable_and_no_cache` asserts `detail == LLMError.DEFAULT_USER_MESSAGE` in place of the "unavailable" substring; in `backend/tests/unit/flashcards/test_llm_cache.py`, `get_or_generate`'s `test_returns_none_on_llm_error` becomes `test_propagates_llm_error_and_writes_no_cache`, `get_fill_blank_sentence` still returns `None` on `LLMError` (fail-soft, spec edge case) and logs a warning, and a non-LLM exception from the fill-blank generator now propagates
- [X] T020 [P] [US1] Add a failing test to `backend/tests/unit/services/test_factory.py` (new file): `get_llm`, `get_structured_llm`, and `get_session_provider` each delegate to `build_llm_provider` with the `LLMSelection(provider_id, model)` and `llm_effort` read from `AppSettingsRecord`. Assert this by monkeypatching the registry function, not by type-checking a concrete class

### Implementation for User Story 1

- [X] T021 [US1] Change `OllamaLLMProvider.__init__` in `backend/app/services/llm/ollama.py` to `(client: ollama.Client, model: str, keep_alive_minutes: int)` and replace every `ollama.chat(...)` with `self._client.chat(...)`. `keep_alive_minutes` is stored for US5 and not yet used. Make T013 pass
- [X] T022 [US1] Create `backend/app/services/llm/registry.py`: a `ConfiguredLLMProvider` Protocol (LLMProvider + StructuredLLMProvider + SessionCapableProvider), `UnknownProviderError(LLMError)`, and `build_llm_provider(selection: LLMSelection, settings: Settings, effort: str = DEFAULT_EFFORT) -> ConfiguredLLMProvider`, dispatching on `selection.provider_id` through a private builder table. The Ollama builder creates `ollama.Client(host=settings.ollama_url)` (FR-008) and passes `settings.session_idle_ttl_minutes`. Only the `ollama` builder exists in this phase. `effort` is added beyond contracts/api.md §2.3 because the Claude builder needs the learner's level, and `LLMSelection` stays `(provider_id, model)` as the fingerprint expects. Make T015 pass. Temporarily make `OllamaLLMProvider` satisfy `SessionCapableProvider` with `NotImplementedError` bodies, which T041 replaces
- [X] T023 [P] [US1] Make `_migrate_db()` in `backend/app/database.py` data-driven, so it stays ≤ 20 lines under the function-length gate (plan.md post-design re-check): move every existing call's arguments into a module-level `_ADDITIVE_COLUMNS: tuple[tuple[str, str], ...]` in their current order, and loop over it calling `_add_column_if_missing(conn, table, definition)`. Append `("app_settings", "llm_provider VARCHAR(20) NOT NULL DEFAULT 'ollama'")` and `("app_settings", "llm_effort VARCHAR(10) NOT NULL DEFAULT 'low'")`. Add `llm_provider: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_PROVIDER_ID)` and `llm_effort: Mapped[str] = mapped_column(String(10), nullable=False, default=DEFAULT_EFFORT)` to `backend/app/models/app_settings.py`. Make T016 pass
- [X] T024 [US1] Add `llm_provider: str` and `llm_effort: str` to `AppSettingsRecord` in `backend/app/services/storage/base.py`, and map them in `_settings_to_record` and `get_settings` in `backend/app/services/storage/sqlite.py`. Make T017 pass (depends on T023)
- [X] T025 [US1] Add `llm_provider` and `llm_effort` to `SettingsResponse` and `_to_response` in `backend/app/routers/settings.py`. Make T018 pass (depends on T024)
- [X] T026 [US1] Rewrite `get_llm` and `get_structured_llm` in `backend/app/services/factory.py` to delegate to `build_llm_provider(LLMSelection(app_settings.llm_provider, app_settings.llm_model), get_settings(), app_settings.llm_effort)`, and add `get_session_provider` with the same delegation, returning `SessionCapableProvider`. Remove the local `OllamaLLMProvider` imports: factory imports no concrete LLM provider. Make T020 pass (depends on T022, T024)
- [X] T027 [US1] Register `@app.exception_handler(LLMError)` in `backend/app/main.py`, returning `JSONResponse(status_code=503, content={"detail": exc.user_message})` and logging `exc` at warning level (its `detail`, never a credential). In `backend/app/flashcards/services/llm_cache.py`, remove the `try/except Exception` from `get_or_generate` so `LLMError` reaches the handler, and narrow `get_fill_blank_sentence`'s `except Exception` to `except LLMError` with a `logger.warning`. In `get_word_info` in `backend/app/flashcards/router.py`, delete the `content is None` → 503 branch, which is now dead code. Make T019 pass
- [X] T028 [US1] Run the full backend suite and `ruff`/`black`. Fix any existing test that constructed `OllamaLLMProvider(model=...)` directly, changing only its construction and keeping its assertions. Confirm the shared contract suite (T014) passes for `ollama`

**Checkpoint**: US1 is complete. The seam is real, the host is honoured, and behaviour is identical.
Merge-safe on its own.

---

## Phase 4: User Story 5 — The conversation partner stays warm and in context (Priority: P2, Ollama)

**Goal**: Roleplay and the expression helper go through `ConversationEngine` and a bounded,
expiring session pool. Saved history stays the source of truth, Ollama stays loaded
mid-conversation, and opening an existing conversation warms its session. This phase is built and
proven on Ollama alone. The Claude session arrives in Phase 6 (T063, T079).

**Independent Test**: Every 001/003 integration test passes with only its dependency-override wiring
changed (assertions untouched). `test_chat_sessions.py` proves reuse across turns, rebuild after a
pool reset, the Strict pause merge, the warm endpoint, and that completing a conversation closes its
session. By hand, quickstart §4a steps 1–8 with Ollama.

### Tests for User Story 5 (write first, must FAIL)

- [X] T029 [P] [US5] Write failing tests in `backend/tests/unit/services/conversation/test_sync.py` for the pure function `plan_session_use(live: SessionState | None, expected: SessionFingerprint, history: Sequence[SavedTurn]) -> SessionPlan`, covering the research R-15 table: no live session → `Rebuild`; fingerprint differs in selection, in effort, or in prompt digest → `Rebuild`; `synced_turn_ids` a prefix of the history ids and every remaining turn `user` → `Reuse(pending=<remaining turns>)`; two pending learner turns (the Strict pause plus the retry) → `Reuse` with both, in order; a remaining `assistant` turn the session didn't produce → `Rebuild`; a synced id missing from history (deleted) → `Rebuild`; reordered ids → `Rebuild`; two identical learner texts ("Sí.") with different ids aren't confused; a broken session → `Rebuild`. On `Rebuild`, the plan carries `synced=history[:-len(pending)]` and `pending=` the trailing learner turns
- [X] T030 [P] [US5] Write the shared session contract suite in `backend/tests/contract/service_interfaces/test_conversation_session_implementations.py`, parametrised over a `session_factory` fixture with one id, `ollama` (an `OllamaSession` over a recording fake `ollama.Client`). Cover contracts/api.md §2.6 items 1–7: (1) a fresh session opened on history H, then `reply(pending)`, makes exactly one generation request containing all of H and the pending turns; (2) after `acknowledge(id)`, `synced_turn_ids` ends with the pending ids followed by `id`; (3) a second `reply` regenerates no earlier turn; (4) `guidance` appears in exactly that turn's request and not in the next turn's standing instructions; (5) `warm()` produces no reply; (6) `close()` is idempotent, and afterwards `reply` raises `LLMError`; (7) a mid-turn failure marks the session broken and raises `LLMError` with a non-empty `user_message`. Structure it so US2 adds the `claude` id without editing test bodies
- [X] T031 [P] [US5] Write failing tests in `backend/tests/unit/services/llm/test_ollama_session.py` for Ollama-specific behaviour (research R-13): every `client.chat` call passes `keep_alive=f"{ttl}m"`, where `ttl` is the configured idle TTL (FR-S08); `warm()` calls `client.generate(model=..., prompt="", keep_alive=...)` and never `chat`; `guidance` is appended to the system message for that call only, so the request is byte-identical to today's `system_prompt + reply_prompt_suffix`; two pending learner turns are sent as two consecutive `user` messages; `reply_to_opening(instruction)` sends `[system, user(instruction)]` when history is empty, and the instruction is not recorded in `synced_turn_ids`; `session_fingerprint(prompt).effort == ""`
- [X] T032 [P] [US5] Write failing tests in `backend/tests/unit/services/conversation/test_pool.py` for `ConversationSessionPool` with a fake `SessionCapableProvider` that records opens and closes and uses an injectable clock: reuse on a matching fingerprint and synced prefix; rebuild (close the old session, open a new one) on fingerprint change; LRU bound `max_live=3`, where opening a 4th closes the least-recently-used; idle expiry after the TTL closes the session on next access; `evict_idle()` closes every session idle past the TTL **with no other access** and leaves fresher ones live (FR-S06), and never closes a session whose per-key lock is held by a running turn; the per-key lock serialises two threads on the same key in arrival order (FR-S10); two different keys proceed concurrently (neither blocks on the other's lock); a session-level `LLMError` (`can_retry=True`) mid-turn closes, rebuilds, and retries **once**, then a second failure propagates; an `LLMError(can_retry=False)` propagates immediately with no rebuild (FR-S11); an early-closed token iterator (`GeneratorExit` before completion) closes and discards the session; `close_all()` closes every session; a rebuild logs `session rebuilt key=<kind>:<id> turns=<n> generations=1` at INFO
- [X] T033 [P] [US5] Write failing tests in `backend/tests/unit/services/conversation/test_engine.py` for `ConversationEngine(pool)`: `stream_turn` with `opening_instruction` calls `reply_to_opening`; with pending learner turns it calls `reply(pending, guidance)`; `acknowledge(key, turn_id)` reaches the live session; `warm(provider, key, standing_prompt, history)` opens the session and calls `session.warm()` without generating; `is_live(key)` is a pure query; `end(key)` closes that session only; `evict_idle()` delegates to the pool; `close()` closes all. `test_rebuild_of_long_history_generates_exactly_once`: a 20-turn saved history with no live session yields exactly one generation (FR-S05, SC-004c)
- [X] T034 [P] [US5] Create `backend/tests/support/stateless_session_provider.py`: `StatelessSessionProvider(llm: LLMProvider)`, a test-only `SessionCapableProvider` whose sessions rebuild the full message list and call `llm.chat_stream` on every turn, with guidance appended to the system message. This is exactly today's router behaviour, so existing `StubLLMProvider` assertions on the messages they receive stay valid. Also create `backend/tests/support/engine_overrides.py` with `override_conversation_engine(app, llm) -> ConversationEngine`, which installs overrides for `get_session_provider` (serving `StatelessSessionProvider(llm)`) and for `get_conversation_engine` (a fresh engine with its own pool, so tests share no state)
- [X] T035 [US5] Update only the dependency-override wiring of the existing chat tests to call `override_conversation_engine(app, stub_llm)` next to their `get_llm` override: `backend/tests/integration/routers/test_chat_open.py`, `backend/tests/integration/routers/test_chat_message.py`, `backend/tests/integration/routers/test_helper.py`, and `backend/tests/integration/corrections/conftest.py`. Change no assertion. These tests are now the regression guard for T046–T048 (depends on T034)
- [X] T036 [P] [US5] Write failing tests in `backend/tests/integration/routers/test_chat_sessions.py` using a counting fake `SessionCapableProvider`: two consecutive `/message` turns open one session and reuse it (one open, two replies, and the second reply carries only the new learner turn); after the engine's pool is cleared, the next turn rebuilds from saved history with exactly one generation; `test_strict_pause_then_retry_reuses_session_with_merged_pending_turns` (Strict mode pauses turn A, retry B → one `reply` with pending `[A, B]` and no rebuild); Gentle mode's `reply_prompt_suffix` arrives as `guidance` for that turn only; `POST /api/chat/{id}/session` returns 202 `{"status": "warming"}` and calls `warm` once, and a second call returns 202 `{"status": "live"}`; 404 `{"detail": "Conversation not found"}` for an unknown id; 409 `{"detail": "This conversation has ended."}` for a completed one; `PATCH /api/conversations/{id}` with `{"status": "completed"}` closes that conversation's session (FR-S12); helper turns use `SessionKey(helper, <helper_session_id>)`, where the first question is `h0`, its reply is acknowledged as `h1`, and the second question arrives as pending `h2` on the reused session; the helper is never warmed in advance (spec US5)
- [X] T037 [P] [US5] Write the failing SSE half of `backend/tests/integration/test_llm_error_surface.py`: when the session provider raises `LLMError("boom", user_message="Custom next step")`, each of `/api/chat/{id}/open`, `/api/chat/{id}/message`, and `/api/chat/helper` emits `data: {"error": "Custom next step"}`; with the default `LLMError("boom")` the text is exactly "The AI is not responding. Please try again." (unchanged for Ollama); the frame order before the error is unchanged (`user_message_saved`, optional `feedback`)
- [X] T038 [P] [US5] Write failing tests for the idle-session reaper (FR-S06, research R-16). In `backend/tests/unit/services/conversation/test_reaper.py`: `run_session_reaper(engine, interval_seconds)` calls `engine.evict_idle()` once per interval (run with `interval_seconds=0.01` against a fake engine); an exception from `evict_idle` is logged and does not stop the loop; cancelling the task ends it cleanly. In `backend/tests/integration/test_lifespan.py`: entering the `TestClient` context starts exactly one reaper task using `SESSION_REAPER_INTERVAL_SECONDS == 60`; leaving it cancels that task and then calls `ConversationEngine.close()` exactly once
- [X] T039 [P] [US5] Write failing Vitest tests in `frontend/src/services/api.test.ts` for `warmSession(conversationId)`: it POSTs `/api/chat/{id}/session` and resolves without throwing on 202, 404, 409, or a network error
- [X] T040 [P] [US5] Write failing Playwright tests in `frontend/e2e/chat.spec.ts`: opening an existing conversation from History sends exactly one `POST /api/chat/{id}/session` before any message is sent; opening a new conversation (no messages) sends none and calls `/open` as before; a 500 from the warm endpoint shows no error to the learner. Add a `mockWarmSession(page)` helper to `frontend/e2e/fixtures.ts` that records calls

### Implementation for User Story 5

- [X] T041 [US5] Create `backend/app/services/llm/ollama_session.py` with `OllamaSession(ConversationSession)`: in-memory `(role, content)` turns plus `synced_turn_ids`; `reply` sends `[system(standing + guidance), *turns, *pending]` through `client.chat(stream=True, keep_alive=...)`; `reply_to_opening`; `warm` as an empty-prompt `client.generate`; `acknowledge` appends the reply under the saved id; `close` makes later calls raise `LLMError`; any client exception sets `is_broken` and raises `LLMError` (`can_retry=True`). Implement `session_fingerprint` and `open_session` on `OllamaLLMProvider` in `backend/app/services/llm/ollama.py`, replacing the T022 placeholders. Make T030 and T031 pass
- [X] T042 [US5] Create `backend/app/services/conversation/sync.py` with `SessionState` (fingerprint, synced ids, `is_broken`), the `SessionPlan` variants `Reuse(pending)` and `Rebuild(synced, pending)`, and the pure `plan_session_use`. No I/O, no provider imports. Make T029 pass
- [X] T043 [US5] Create `backend/app/services/conversation/pool.py` with `ConversationSessionPool(max_live: int, idle_ttl: timedelta, clock: Callable[[], datetime])`: an `OrderedDict[SessionKey, _Entry]` LRU; a per-key `threading.Lock` held for the whole turn, stored in a dict guarded by a pool lock; expiry checked on access (the same semantics as `HelperSessionStore`), calling `close()` on every evicted or expired session; `evict_idle()`, which runs the same expiry sweep without touching any entry and skips keys whose lock is held; `run_turn(provider, request) -> Iterator[str]`, which uses `plan_session_use`, rebuilds by `provider.open_session(standing_prompt, synced)`, retries once on `LLMError.can_retry`, and on `GeneratorExit` closes and discards the session; `warm`, `acknowledge`, `end`, `is_live`, and `close_all`. The rebuild log line is exactly as in T032. Keep every method ≤ 20 lines by extracting private helpers. Make T032 pass (depends on T042)
- [X] T044 [US5] Create `backend/app/services/conversation/engine.py` with `ConversationEngine(pool)` exposing `stream_turn`, `acknowledge`, `warm`, `is_live`, `end`, `evict_idle`, and `close` as in contracts/api.md §2.7. Export `ConversationEngine` from `backend/app/services/conversation/__init__.py`. Make T033 pass (depends on T043)
- [X] T045 [US5] Add `get_conversation_engine()` to `backend/app/services/factory.py`, lru-cached (one per process) and built with a `ConversationSessionPool(settings.session_max_live, timedelta(minutes=settings.session_idle_ttl_minutes), clock=lambda: datetime.now(UTC))`. Create `backend/app/services/conversation/reaper.py` with `SESSION_REAPER_INTERVAL_SECONDS = 60` and `async def run_session_reaper(engine, interval_seconds)` (loop: `await asyncio.sleep`, then `await loop.run_in_executor(None, engine.evict_idle)`, logging and continuing on exceptions), exported from `backend/app/services/conversation/__init__.py`. In `backend/app/main.py`'s `lifespan`: after `init_db()`, start `asyncio.create_task(run_session_reaper(get_conversation_engine(), SESSION_REAPER_INTERVAL_SECONDS))`; after `yield`, cancel and await the task, then call `get_conversation_engine().close()`. `lifespan` stays ≤ 20 lines. Make T038 pass
- [X] T046 [US5] Rewrite `open_chat` in `backend/app/routers/chat.py` to build a `TurnRequest` (key `SessionKey(roleplay, str(conversation_id))`, the standing roleplay prompt, the saved history as `SavedTurn`s with ids `m<id>`, and `opening_instruction=build_open_chat_user_prompt(...)`), run `engine.stream_turn` in the executor, relay the tokens, save the assistant message, call `engine.acknowledge(key, f"m{msg.id}")`, and schedule TTS. It depends on `get_session_provider` and `get_conversation_engine`, not `get_llm`. Extract shared private helpers (`_standing_roleplay_prompt`, `_saved_turns`, `_sse`, `_relay_engine_reply`), with the error frame using `exc.user_message`. `open_chat` must be ≤ 20 lines. The T035 regression tests and the T036/T037 open cases must pass
- [X] T047 [US5] Rewrite `send_message` in `backend/app/routers/chat.py` onto the engine: after the correction plan, build a `TurnRequest` from the full saved history (so a Strict-paused message and its retry are both pending) with `guidance=plan.reply_prompt_suffix`. Reuse the T046 helpers. Delete `_stream_reply` (the engine replaces it). `send_message` must be ≤ 20 lines, and the SSE frame sequence is unchanged (contracts/api.md §1.4). The T035 and T036/T037 message cases must pass
- [X] T048 [US5] Rewrite `chat_helper` in `backend/app/routers/chat.py` onto the engine: key `SessionKey(helper, req.helper_session_id)`, history from `HelperSessionStore.get_history` (k stored turns) mapped to `SavedTurn`s with positional ids `h0 … h(k−1)`, plus the new learner turn `hk`, and `standing_prompt=build_helper_system_prompt(...)`. After `append_exchange` stores the pair at positions k and k+1, call `engine.acknowledge(key, f"h{k + 1}")`. With k = 0 the learner turn is `h0` and the reply `h1`. `chat_helper` must be ≤ 20 lines. The T035 helper tests and the T036/T037 helper cases must pass
- [X] T049 [US5] Add `POST /chat/{conversation_id}/session` to `backend/app/routers/chat.py` (contracts/api.md §1.5): 404/409 as specified; if `engine.is_live(key)` return 202 `{"status": "live"}`; otherwise schedule `engine.warm(...)` with `loop.run_in_executor`, log (never raise) a warm-up failure, and return 202 `{"status": "warming"}`. It never returns a provider error. ≤ 20 lines. Make the T036 warm cases pass
- [X] T050 [US5] In `patch_conversation` in `backend/app/routers/conversations.py`, call `engine.end(SessionKey(SessionKind.ROLEPLAY, str(conversation_id)))` when `status == "completed"`, importing only from `app.services.conversation` and `app.services.factory`. Make the T036 complete case pass
- [X] T051 [P] [US5] Add `warmSession(conversationId: number): Promise<void>` to `frontend/src/services/api.ts`. It is fire-and-forget and swallows every failure, since the warm-up is invisible (Principle IV). Make T039 pass
- [X] T052 [US5] In `frontend/src/pages/Chat.tsx` `restoreTranscript` path (existing conversation), call `void api.warmSession(convId)`. Don't call it on the `streamOpening` path. Add only this line: the `Chat` component is over 20 lines and is recorded in plan.md Complexity Tracking on condition that this feature does not grow it. Make T040 pass, then run `npm test -- --run`, `npm run lint`, and `npm run test:e2e`
- [X] T053 [US5] Run the full backend suite. Confirm every 001/003 test passes (`test_chat_correction_modes.py` is the Gentle-suffix regression guard), the session contract suite passes for `ollama`, and `open_chat`, `send_message`, and `chat_helper` are each ≤ 20 lines (count with an AST line count, not by eye)

**Checkpoint**: Sessions work on Ollama. The model stays loaded mid-conversation, resumed
conversations warm in the background, and every existing test passes.

---

## Phase 5: User Story 3 — Claude acts only as a conversation partner (Priority: P2)

**Goal**: Every `claude` invocation, one-shot or session, is stripped to a text-only chat model with
no tools, no personal or project configuration, no saved sessions, a replaced system prompt, an
empty app-owned working directory, and a scrubbed environment. The isolation invariants are the
first Claude tests written (plan Phase 3).

**Independent Test**: The unit invariants below pass. By hand and live (Phase 9): quickstart §5,
covering no actions taken, no PINEAPPLE, no new `~/.claude/projects/` entries, and no learner text in
`ps`.

### Tests for User Story 3 (write first, must FAIL)

- [X] T054 [P] [US3] Write failing tests in `backend/tests/unit/services/llm/claude_code/test_command.py` (create the package `__init__.py`) for the pure `build_claude_argv(request: ClaudeRequest)` and `build_session_argv(request: ClaudeSessionRequest)`, each run over every output mode (stream, json, schema) and over session argv: `test_argv_never_contains_bare`; `--tools` is always immediately followed by `""`; `--safe-mode`, `--disable-slash-commands`, and `--no-session-persistence` are always present; `--system-prompt` is always present with non-empty text; the prompt text never appears in argv; `--model <alias>` and `--effort <level>` match the request; stream mode adds `--output-format stream-json --verbose --include-partial-messages`; json mode adds `--output-format json`; schema mode adds `--output-format json --json-schema <compact JSON>` (`separators=(",", ":")`); session argv adds `--input-format stream-json --output-format stream-json --verbose --include-partial-messages`; `argv[0]` is the configured executable followed by `-p`
- [X] T055 [P] [US3] Write failing tests in `backend/tests/unit/services/llm/claude_code/test_runner.py` for `scrubbed_environment(environ: Mapping[str, str]) -> dict[str, str]` and `SubprocessClaudeCodeRunner`: `test_environment_scrubs_anthropic_and_claude_code_variables` (removes every `ANTHROPIC_*` and `CLAUDE_CODE_*` key plus `CLAUDECODE`, `CLAUDE_PID`, and `CLAUDE_EFFORT`, and keeps `CLAUDE_CONFIG_DIR`, `PATH`, `HOME`, and proxy variables); `stream_lines(argv, stdin_text, timeout_seconds)` spawns with `cwd=<claude_workdir>`, creating it if missing and writing nothing into it, with the scrubbed env, and with the prompt written to stdin then closed; a missing executable raises `ClaudeCodeFailure(kind=not_installed)`; exceeding the **per-call** `timeout_seconds` kills the process and raises `ClaudeCodeFailure(kind=unreachable)`, and two calls with different timeouts (0.2 s and 5 s against a script that sleeps 1 s) time out and succeed respectively (research R-9 correction deadline); closing the generator early (`GeneratorExit`) kills the process; a non-zero exit code does **not** raise by itself (the caller classifies from the lines). Use a tiny Python script as the stand-in executable (`sys.executable` + a temp script) so no `claude` is needed
- [X] T056 [P] [US3] Write failing tests in `backend/tests/unit/services/llm/claude_code/test_interactive_process.py` for `SubprocessClaudeCodeRunner.spawn_interactive(argv, log_path)`: stderr goes to `log_path` (truncated on spawn, parent directory created if missing), not a pipe, and nothing is written to the working directory; `send_line` writes one line and flushes; `read_lines_until_result(timeout)` yields lines up to and including the next `"type": "result"` line and stops; the timeout kills the process and raises `ClaudeCodeFailure(unreachable)`; `is_alive` reflects the process state; `close()` terminates, then kills after a grace period, and is idempotent. Use the same stand-in executable approach, with an echo script that emits a result line per input line. Also write `backend/tests/unit/services/llm/claude_code/test_failures.py`: `FailureKind` has exactly seven members; each one's `user_message` is exactly the research R-7 text; `can_retry` is `False` for `not_installed`, `not_signed_in`, `not_on_plan`, `usage_limit`, and `model_unavailable`, and `True` for `unreachable` and `unexpected_response`; `ClaudeCodeFailure` is an `LLMError`; `failure_for_availability(reason)` maps each `AvailabilityReason` value (`not_installed`, `not_signed_in`, `not_on_plan`) to the `ClaudeCodeFailure` of the same kind

### Implementation for User Story 3

- [X] T057 [US3] Create `backend/app/services/llm/claude_code/failures.py` with `FailureKind` (StrEnum: `not_installed`, `not_signed_in`, `not_on_plan`, `usage_limit`, `model_unavailable`, `unreachable`, `unexpected_response`), the `USER_MESSAGES` mapping with the exact texts from research R-7, `ACCOUNT_LEVEL_KINDS = {not_installed, not_signed_in, not_on_plan, usage_limit, model_unavailable}`, `ClaudeCodeFailure(LLMError)` built as `ClaudeCodeFailure(kind, detail)` (with `user_message` from the mapping and `can_retry = kind not in ACCOUNT_LEVEL_KINDS`), and `failure_for_availability(reason: str) -> ClaudeCodeFailure`, which takes the reason's string value so this module doesn't import `llm/availability.py`. Make `test_failures.py` (T056) pass. Needed by T059
- [X] T058 [US3] Create `backend/app/services/llm/claude_code/command.py`: flag constants, frozen `ClaudeRequest(executable, model, effort, system_prompt, output_mode, json_schema)` and `ClaudeSessionRequest(executable, model, effort, system_prompt)`, `OutputMode` (StrEnum `stream`, `json`, `schema`), and the pure `build_claude_argv` / `build_session_argv` sharing one `_isolation_flags()` helper. `DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant inside a language-learning app. Reply with text only."` is used when the given prompt is blank. Make T054 pass
- [X] T059 [US3] Create `backend/app/services/llm/claude_code/runner.py`: the ABCs `ClaudeCodeRunner` (`stream_lines(argv, stdin_text, timeout_seconds) -> Iterator[str]`, `spawn_interactive(argv, log_path) -> InteractiveProcess`) and `InteractiveProcess` (`send_line`, `read_lines_until_result`, `is_alive`, `close`), exactly as in contracts/api.md §2.5; `scrubbed_environment()` with the prefix constants `SCRUBBED_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_")` and `SCRUBBED_KEYS = frozenset({"CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT"})`; and `SubprocessClaudeCodeRunner(executable, workdir, environ)` plus `_SubprocessInteractiveProcess`, using a watchdog `threading.Timer` for the timeout and `finally: process.kill()` for early close. Make T055 and T056 pass (depends on T057)

**Checkpoint**: Isolation invariants are pinned by unit tests. Nothing calls Claude yet.

---

## Phase 6: User Story 2 — Learner switches the conversation partner to Claude (Priority: P2)

**Goal**: Claude serves every language-model feature (one-shot, structured, and sessions) once
selected in Settings, with a chosen model and effort, and switching needs no restart.

**Independent Test**: With a scripted runner, the shared one-shot and session contract suites pass
for `claude`. `PUT /api/settings` switching to Claude (when available) makes the next request reach
`ClaudeCodeLLMProvider`. Playwright covers switching provider, the model resetting to the provider
default, and effort appearing only for Claude. By hand, quickstart §4.

### Tests for User Story 2 (write first, must FAIL)

- [X] T060 [P] [US2] Write failing tests in `backend/tests/unit/services/llm/claude_code/test_transcript.py` for the pure `render_prompt(messages) -> RenderedPrompt` (research R-5): every `system` message, in order and joined by a blank line, becomes `system_prompt`; no system message → `DEFAULT_SYSTEM_PROMPT`; exactly one remaining `user` message → its content verbatim as `prompt`; otherwise a `<conversation>` transcript with `<turn role="…">` elements in order, followed by the line "Write the assistant's next turn only: the words themselves, with no tag, label, or quotation marks."; a history opening with an `assistant` turn renders with no special case. Also test `render_rebuild_turn(history, pending, guidance) -> str` (one user message holding the transcript of history plus pending, with the guidance block when given) and `render_guidance_block(guidance) -> str` (`<turn_guidance>…</turn_guidance>`)
- [X] T061 [P] [US2] Write failing tests in `backend/tests/unit/services/llm/claude_code/test_events.py` for event parsing and classification against the T004 fixtures: `iter_text_deltas(lines)` yields the three `text_delta` texts from `stream_ok` and ignores unknown event types; `parse_result(lines)` returns `result` from `json_ok` and `json.dumps(structured_output)` from `schema_ok`; `auth_failed` → `ClaudeCodeFailure(not_signed_in)`; `rate_limit_rejected`, or an assistant `error == "rate_limit"` → `usage_limit`; `model_404` → `model_unavailable`; any other `is_error: true` → `unreachable`; `garbage`, or no result line → `unexpected_response`; a `rate_limit_event` with status `allowed` is not an error
- [X] T062 [P] [US2] Write failing tests in `backend/tests/unit/services/llm/claude_code/test_provider.py` for `ClaudeCodeLLMProvider(runner, availability, settings, model, effort)` with a `ScriptedClaudeCodeRunner` (in `backend/tests/support/scripted_claude_runner.py`, which scripts both `stream_lines` and `spawn_interactive`) that records argv, stdin, and `timeout_seconds` and replays fixture lines, and a fake `ProviderAvailabilityChecker`: `chat_stream` uses stream mode at `ONE_SHOT_EFFORT == "low"` and yields the deltas; `chat` uses json mode at `"low"`; `chat_json` uses schema mode at `STRUCTURED_EFFORT == "medium"` and returns JSON text that the 003 correction parser accepts (FR-017); `chat` and `chat_stream` pass `timeout_seconds == settings.claude_request_timeout_seconds`, while `chat_json` passes `timeout_seconds == settings.correction_timeout_seconds`, so a correction past its budget has its process killed (FR-019, research R-9); **pre-flight** (FR-010a): each of the three methods calls `availability.check()` exactly once before the runner, and when it reports `not_on_plan`, `not_signed_in`, or `not_installed`, the method raises the matching `ClaudeCodeFailure` and the runner is never called, so no prompt is sent; the rendered prompt goes to stdin and the rendered system prompt to `--system-prompt`; the learner's `effort` is **not** used for one-shot calls (FR-019a); `model_name` returns the alias; each failure fixture raises the matching `ClaudeCodeFailure`
- [X] T063 [P] [US2] Write failing tests in `backend/tests/unit/services/llm/claude_code/test_session.py` for `ClaudeCodeSession` with a scripted `InteractiveProcess` fake (in `backend/tests/support/scripted_claude_runner.py`) (research R-14): `warm()` spawns the process and writes nothing to stdin; a history with no learner turns seeds each assistant line natively (one `{"type":"assistant",…}` line each), then sends the new turn natively; a history with learner turns sends one user line holding `render_rebuild_turn(...)` for the first turn and native single-turn lines afterwards (`test_rebuild_of_long_history_generates_exactly_once` at the provider level: exactly one `result` is awaited); several pending learner turns are merged into one user line; guidance travels as a `<turn_guidance>` block inside that turn's user line; the standing system prompt passed at spawn ends with the provider's turn-guidance paragraph (a named constant saying to follow such blocks for that reply only and never mention them); the session argv uses the **learner's** effort; stderr goes to `<claude_log_dir>/session-<kind>-<identifier>.log`, never to the working directory; the pre-flight `availability.check()` runs once when the process is spawned (by `warm()` or by the first `reply`) and not on later turns, and a failing check raises the mapped `ClaudeCodeFailure` (`can_retry=False`) without spawning; a dead process mid-turn sets `is_broken` and raises `ClaudeCodeFailure(unreachable)` with `can_retry=True`; an `auth_failed` result mid-session raises `can_retry=False`; `session_fingerprint(prompt).effort` equals the learner's effort
- [X] T064 [P] [US2] Add the `claude` id to the shared one-shot suite in `backend/tests/contract/service_interfaces/test_llm_provider_implementations.py` (`ClaudeCodeLLMProvider` over `ScriptedClaudeCodeRunner`) and to the session suite in `backend/tests/contract/service_interfaces/test_conversation_session_implementations.py` (`ClaudeCodeSession` over the scripted `InteractiveProcess`). Change only the parametrisation. Both ids must appear in the pytest output
- [X] T065 [P] [US2] Write failing tests in `backend/tests/contract/service_interfaces/test_provider_availability_checker.py` and `backend/tests/unit/services/llm/claude_code/test_availability.py`: `AlwaysAvailable().check() == ProviderAvailability(is_available=True, reason=None, message=None)`; `ClaudeCodeAvailability(runner, executable)` runs `claude auth status --json` through the runner (scrubbed env, no prompt); `auth_status_signed_in` → available; `auth_status_signed_out` → `not_signed_in`; `auth_status_api_key` → `not_on_plan`; a missing executable → `not_installed`; the messages are exactly those in data-model.md §2; no field of the result, and no log line, contains the decoy email or org values (FR-011)
- [X] T066 [P] [US2] Write failing tests in `backend/tests/unit/services/llm/test_selection.py` for the pure `resolve_llm_selection(current: AppSettingsRecord, requested_provider: str | None, requested_model: str | None, claude_availability: Callable[[], ProviderAvailability]) -> LLMSelection`, covering the data-model.md §1 partial-update table: neither field → unchanged; provider only and different → the new provider's default model (FR-024); provider only and the same → unchanged; model only → validated against the current provider; both → validated against the given provider. Rejections raise `SelectionRejected(message)` with the verbatim texts: Claude with a non-Claude model → "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus."; Ollama with an empty or whitespace-only model → "Choose a local model."; Ollama with a Claude id → "That model belongs to Claude. Choose a local model, or switch the provider to Claude."; Claude unavailable → its availability `message`. The availability callable is invoked only when the resulting provider is `claude` and the request contains `llm_provider` or `llm_model`, and never for Ollama. An Ollama model outside the catalogue (e.g. `llama3.1`) is accepted
- [X] T067 [P] [US2] Add failing tests to `backend/tests/unit/services/llm/test_registry.py`: `build_llm_provider(LLMSelection("claude", "haiku"), settings, "medium")` returns a `ClaudeCodeLLMProvider` whose runner is a `SubprocessClaudeCodeRunner` configured from `settings.claude_executable`, `claude_workdir`, and `os.environ`, whose pre-flight checker is a `ClaudeCodeAvailability` sharing that runner, and whose sessions use the effort `"medium"`
- [X] T068 [P] [US2] Add failing tests to `backend/tests/integration/routers/test_settings.py` (override `get_availability_checkers`): `GET /api/settings/llm-providers` returns the contracts/api.md §1.1 body in catalogue order, with Ollama `effort_levels: []` and `default_effort: null`, and with no `email`/`org`/subscription keys anywhere; `PUT {llm_provider: "claude"}` with Claude available → 200, `llm_model: "sonnet"`, and `llm_effort` unchanged; `PUT {llm_provider: "claude", llm_model: "llama3.2"}` → 422 with the exact mismatch detail; `PUT {llm_provider: "ollama", llm_model: "sonnet"}` → 422; `PUT {llm_provider: "claude"}` with Claude unavailable → 422 with the availability message; `PUT {llm_provider: "gpt"}` → 422 (pattern); `PUT {llm_effort: "max"}` → 422 (pattern); `PUT {llm_effort: "high"}` → 200; after every 422, `GET /api/settings` is unchanged (FR-027); switching `claude` → `ollama` resets the model to `llama3.1:8b` and keeps `llm_effort`
- [X] T069 [P] [US2] Add failing tests to `backend/tests/integration/routers/test_chat_sessions.py`: with the settings switched from Ollama to Claude between two turns (using fake providers per id from an overridden `get_session_provider`), the second turn rebuilds the session because the fingerprint changed, and its single generation receives the full saved history (edge case "switching provider mid-conversation"); changing only `llm_effort` while Claude is selected also rebuilds
- [X] T070 [P] [US2] Write failing Vitest tests in `frontend/src/services/api.test.ts`: `getLlmProviders()` GETs `/api/settings/llm-providers` and returns `LlmProviderOption[]`; `AppSettings` and the update payload carry `llm_provider` and `llm_effort`; a 422 from `updateSettings` throws `Error(body.detail)`
- [X] T071 [P] [US2] Write failing Vitest tests in `frontend/src/components/settings/LlmProviderFields.test.tsx`: renders a labelled radio group with one radio per provider (`display_name`); the model `<select>` lists the selected provider's models; choosing another provider calls `onChange` with that provider's `default_model` (FR-024) and never offers the other provider's models; a saved model missing from the list is shown as an extra option and kept; the effort `<select>` renders only when the selected provider's `effort_levels` is non-empty (FR-025a); effort labels are the catalogue labels
- [X] T072 [P] [US2] Update `frontend/src/pages/Settings.test.tsx` with failing tests: Settings loads `getLlmProviders()` and renders `LlmProviderFields`; `LLM_OPTIONS` no longer exists (the old hard-coded list isn't rendered); saving sends `llm_provider`, `llm_model`, and `llm_effort`; a 422 `detail` is shown in the page's existing error area, and the form keeps the learner's choice
- [X] T073 [P] [US2] Extend `frontend/e2e/fixtures.ts`: add `llm_provider: 'ollama'` and `llm_effort: 'low'` to `mockSettings`; add `mockLlmProvidersAvailable` and `mockLlmProvidersClaudeUnavailable(reason)` matching contracts/api.md §1.1; make every existing helper that mocks `/api/settings` also mock `/api/settings/llm-providers` (default: available), so the existing specs keep passing
- [X] T074 [US2] Write failing Playwright tests in `frontend/e2e/settings.spec.ts`: switch the provider to Claude → the model select shows "Claude Sonnet" → the effort control appears with "Low — fastest replies" selected → Save sends `llm_provider: "claude"`, `llm_model: "sonnet"`, and `llm_effort: "low"`; switch back to Ollama → the model is `llama3.1:8b` and the effort control is gone; a mocked 422 on save shows its detail text (depends on T073)

### Implementation for User Story 2

- [X] T075 [US2] Create `backend/app/services/llm/claude_code/transcript.py` with `RenderedPrompt` (frozen: `system_prompt`, `prompt`), `render_prompt`, `render_rebuild_turn`, and `render_guidance_block`, with the transcript tags and trailing instruction as named constants. Make T060 pass
- [X] T076 [US2] Create `backend/app/services/llm/claude_code/events.py`: `iter_text_deltas(lines) -> Iterator[str]`, `parse_result(lines) -> str`, and `classify_failure(event) -> ClaudeCodeFailure | None`, reading only the fields listed in contracts/api.md §3 "Output parsing". Unknown event types are ignored, and JSON decode errors become `unexpected_response`. Make T061 pass (depends on T057)
- [X] T077 [P] [US2] Create `backend/app/services/llm/availability.py` with the `ProviderAvailabilityChecker` ABC, the frozen `ProviderAvailability(is_available, reason, message)`, `AvailabilityReason` (StrEnum: `not_installed`, `not_signed_in`, `not_on_plan`), `AVAILABILITY_MESSAGES` (the data-model.md §2 texts), and `AlwaysAvailable`. Make the `AlwaysAvailable` half of T065 pass
- [X] T078 [US2] Create `backend/app/services/llm/claude_code/provider.py` with `ClaudeCodeLLMProvider(LLMProvider, StructuredLLMProvider, SessionCapableProvider)`, constructed as `(runner, availability: ProviderAvailabilityChecker, settings, model, effort)` and holding `ONE_SHOT_EFFORT = "low"` and `STRUCTURED_EFFORT = "medium"`. Each of `chat_stream`, `chat`, and `chat_json` first runs a private `_ensure_on_plan()` (the FR-010a pre-flight: `availability.check()`, raising `failure_for_availability(reason)` when unavailable), then renders the prompt, builds argv, calls `runner.stream_lines` with the per-method timeout (`claude_request_timeout_seconds`, or `correction_timeout_seconds` for `chat_json`), and parses. `session_fingerprint` and `open_session` delegate to `ClaudeCodeSession` (T079), passing the same availability checker. Make T062 pass (depends on T058, T059, T075, T076, T077)
- [X] T079 [US2] Create `backend/app/services/llm/claude_code/session.py` with `ClaudeCodeSession(ConversationSession)`: runs the pre-flight check once, then spawns via `runner.spawn_interactive(build_session_argv(...), settings.claude_log_dir / f"session-{kind}-{identifier}.log")`, with the standing prompt extended by `TURN_GUIDANCE_PARAGRAPH`; applies the rebuild rule from research R-14 (native assistant seeding when there are no learner turns, otherwise one `render_rebuild_turn` user line on the first turn); writes each turn as `{"type":"user","message":{"role":"user","content":…}}`; merges pending turns; reads `read_lines_until_result(settings.claude_request_timeout_seconds)` through `iter_text_deltas` and classifies failures; tracks `synced_turn_ids`, `is_broken`, and `last_used_at`. Make T063 pass, then T064's session half (depends on T059, T075, T076, T078)
- [X] T080 [US2] Create `backend/app/services/llm/claude_code/availability.py` with `ClaudeCodeAvailability(runner, executable)`, which reads only `loggedIn` and `authMethod` (`CLAUDE_PLAN_AUTH_METHOD = "claude.ai"`) and discards everything else inside the function. Create `backend/app/services/llm/claude_code/__init__.py` exporting only `ClaudeCodeLLMProvider` and `ClaudeCodeAvailability`. Make the rest of T065 pass (depends on T077, T059)
- [X] T081 [US2] Register the `claude` builder in `backend/app/services/llm/registry.py`: build one `runner = SubprocessClaudeCodeRunner(settings.claude_executable, settings.claude_workdir, os.environ)`, then `ClaudeCodeLLMProvider(runner, ClaudeCodeAvailability(runner, settings.claude_executable), settings, selection.model, effort)`. Add `get_availability_checkers() -> Mapping[str, ProviderAvailabilityChecker]` to `backend/app/services/factory.py`, keyed by catalogue id, which is the only other place the ids meet their checkers. Make T067 and T064's one-shot half pass (depends on T078, T080)
- [X] T082 [US2] Create `backend/app/services/llm/selection.py` with `SelectionRejected(ValueError)`, the rejection message constants, and the pure `resolve_llm_selection`, keeping each helper ≤ 20 lines. Make T066 pass (depends on T012, T077)
- [X] T083 [US2] Extend `backend/app/routers/settings.py`: `UpdateSettingsRequest` gains `llm_provider: str | None = Field(None, pattern="^(ollama|claude)$")` and `llm_effort: str | None = Field(None, pattern="^(low|medium|high)$")`; add a `LlmProviderResponse` model and `GET /settings/llm-providers`, built from `PROVIDER_CATALOG` + `get_availability_checkers()` and never including account fields; `update_settings_endpoint` calls `resolve_llm_selection` and maps `SelectionRejected` to 422 `{"detail": message}` before any write. Every function stays ≤ 20 lines (extract `_llm_updates`, `_provider_response`). Make T068 pass (depends on T081, T082)
- [X] T084 [US2] Run `backend/tests/integration/routers/test_chat_sessions.py` and make T069 pass. The pool's fingerprint comparison should already cover it, so fix only real gaps
- [X] T085 [P] [US2] Extend `frontend/src/services/api.ts` with the `ModelOption`, `EffortOption`, and `LlmProviderOption` interfaces (the fields of contracts/api.md §1.1), `getLlmProviders()`, and `llm_provider`/`llm_effort` on `AppSettings` and the update payload. Make T070 pass
- [X] T086 [US2] Create `frontend/src/components/settings/LlmProviderFields.tsx`: a controlled component (`providers`, `value: {provider, model, effort}`, `onChange`) with a `<fieldset>`/`<legend>` radio group, a model `<select>` (plus the preserved unlisted saved model), and an effort `<select>` shown only when `effort_levels.length > 0`. Use design-system tokens only (no hex colours, `--radius-lg` on any card surface, `--color-text` for labels). Make T071 pass (depends on T085)
- [X] T087 [US2] Wire `LlmProviderFields` into `frontend/src/pages/Settings.tsx`: load `api.getLlmProviders()` in the existing `useEffect` pattern, hold `llmProvider`/`llmEffort` state next to `llmModel`, remove `LLM_OPTIONS`, send the three fields on save, and show a 422 `detail` in the existing error display. The `Settings` component is in plan.md Complexity Tracking on condition that it doesn't grow: put the provider-list loading in a `useLlmProviders()` hook (≤ 20 lines, in `frontend/src/components/settings/useLlmProviders.ts`), and confirm the component's line count is no higher than before. Make T072 pass, then T074, then run `npm test -- --run`, `npm run lint`, and `npm run test:e2e` (depends on T086, T073)

**Checkpoint**: Claude is selectable end to end and serves every language-model feature through
one-shot calls and sessions. Both contract suites pass for both providers.

---

## Phase 7: User Story 4 — Learner can see whether Claude is usable and what it means for privacy (Priority: P3)

**Goal**: The disabled Claude option names the missing setup step, a privacy notice appears when
Claude is selected, and each Claude failure reaches the learner as an actionable message in chat and
in panels.

**Independent Test**: Playwright covers the three unavailable reasons (disabled radio and note) and
the notice. Integration tests with a scripted runner show each of the seven failure kinds' messages in
SSE and 503 bodies. By hand, quickstart §3 and §6.

### Tests for User Story 4 (write first, must FAIL)

- [X] T088 [P] [US4] Add failing tests to `backend/tests/integration/test_llm_error_surface.py`, parametrised over the seven `FailureKind`s. Override `get_llm` and `get_session_provider` with a `ClaudeCodeLLMProvider` over a `ScriptedClaudeCodeRunner` (scripting both `stream_lines` and `spawn_interactive`) and a fake availability checker. The pre-flight kinds `not_installed`, `not_signed_in`, and `not_on_plan` come from the checker. `usage_limit`, `model_unavailable`, and `unexpected_response` replay the matching fixture. `unreachable` comes from the runner raising a timeout. Assert per path. **One-shot** (`/api/learning/grammar`): 503 with the R-7 message, and exactly one `stream_lines` call for every runner-side kind (one-shot calls never retry), or zero for the pre-flight kinds. **Session** (`/api/chat/{id}/message`): `data: {"error": <R-7 message>}`; account-level kinds (the three pre-flight kinds, `usage_limit`, `model_unavailable`) produce at most one `spawn_interactive` (zero for pre-flight kinds) and no rebuild (FR-S11); `unreachable` and `unexpected_response` produce exactly two spawns (the original and one retry on a rebuilt session). With Claude selected and the checker reporting `not_signed_in`, no request is served by Ollama (FR-029: assert the Ollama fake is never called)
- [X] T089 [P] [US4] Add failing tests to `backend/tests/integration/corrections/test_correction_resilience.py`: with a Claude structured provider raising `ClaudeCodeFailure(usage_limit)`, a Gentle-mode turn still produces an uncorrected reply and no error frame (003 FR-026 is unchanged, per contracts/api.md §1.4). Also `test_timed_out_claude_correction_has_its_process_stopped` (FR-019): with `correction_timeout_seconds` set to 0.2 and a Claude structured provider over a runner whose `stream_lines` blocks until killed, the turn fails open within the budget, the runner received `timeout_seconds == 0.2`, and its process-kill hook fired no later than 0.5 s after the call began
- [X] T090 [P] [US4] Add failing Vitest tests to `frontend/src/components/settings/LlmProviderFields.test.tsx`: an unavailable provider's radio is `disabled`, and `aria-describedby` points to a note showing `unavailable_message`; an available Claude has no note; selecting Claude shows a notice containing "sent to Anthropic", "Claude plan", and "audio stays on your computer" (exact wording set in T094), using the existing warning-note pattern; Ollama shows no notice; if the saved provider is Claude but it is now unavailable, the radio stays checked, the note shows, and the form still renders (edge case "sign-in lost")
- [X] T091 [P] [US4] Add failing Vitest tests to `frontend/src/pages/Settings.test.tsx`: the corrections-experimental warning no longer says or implies the model is local (e.g., it doesn't contain "local model" as the cause), and still carries the false-flag caveat
- [X] T092 [US4] Add failing Playwright tests to `frontend/e2e/settings.spec.ts`: for each of `not_installed`, `not_signed_in`, and `not_on_plan`, the Claude radio is disabled and the matching message is visible; with Claude available, selecting it reveals the privacy notice, and switching to Ollama hides it; the disabled radio's accessible description (`toHaveAccessibleDescription`) equals the unavailable message. Also add to `frontend/e2e/chat.spec.ts`: a mocked SSE `error` frame carrying the usage-limit message is shown in the chat, and the loading indicator clears (SC-007)

### Implementation for User Story 4

- [X] T093 [US4] Make T088 and T089 pass. These should pass on the existing US2/US5 code. Fix only real gaps (e.g., a failure path that bypasses `classify_failure`, or a retry on an account-level kind) in `backend/app/services/llm/claude_code/` or `backend/app/services/conversation/pool.py`
- [X] T094 [US4] In `frontend/src/components/settings/LlmProviderFields.tsx`, add the disabled state (radio `disabled`, note `id` linked by `aria-describedby`, text colour `--color-text-muted`) and the privacy notice shown while Claude is selected, reusing the Settings warning-note pattern (`--color-warning` left border, tokens only). The notice text is a named constant: "Your conversation text is sent to Anthropic under your Claude account and counts toward your Claude plan's usage. Your voice recordings and audio stay on your computer." Make T090 pass
- [X] T095 [US4] Reword the corrections-experimental warning in `frontend/src/pages/Settings.tsx` so it no longer assumes the model is local (spec Assumptions "Corrections warning"): keep the false-flag caveat and say a more capable model reduces it. This is a text-only change, so the `Settings` component doesn't grow (plan.md Complexity Tracking). Make T091 pass, then T092, then run `npm test -- --run`, `npm run lint`, and `npm run test:e2e`

**Checkpoint**: Every failure kind is actionable. Availability and privacy are visible before the
learner commits.

---

## Phase 8: User Story 6 — Project docs describe a provider-agnostic app (Priority: P4)

**Goal**: README, CLAUDE.md, and docs/architecture.md present "every AI capability sits behind a
swappable provider interface, local by default, cloud opt-in", keep the privacy rationale, and
explain how to enable Claude.

**Independent Test**: quickstart §7's grep returns only qualified hits. A reader finds the enable-Claude
steps in the README.

### Tests for User Story 6 (write first, must FAIL)

- [X] T096 [US6] Write a failing test in `backend/tests/unit/test_docs_positioning.py` that reads `README.md`, `CLAUDE.md`, and `docs/architecture.md` from the repo root and asserts: each contains the phrase "local by default"; none contains an unqualified "no cloud", "no external services", "fully local", or "local-only" (every matching line must also contain one of "default", "Ollama", "Piper", "faster-whisper", "whisper", or "speech"); the README contains a section that mentions "Claude Code", "sign in", and "Settings" (FR-030, FR-031, SC-009)

### Implementation for User Story 6

- [X] T097 [P] [US6] Update `README.md`: reposition the intro to "provider-agnostic, local by default, cloud opt-in", keeping the privacy reasoning as the reason for the default; add an "Enabling Claude (optional)" section (install Claude Code, sign in with a Claude plan and not an API key, confirm with `claude auth status --text`, select Claude on the Settings screen, what is sent to Anthropic and what stays local, usage counts toward the plan); qualify every "no cloud"/"no external services" statement
- [X] T098 [P] [US6] Update `CLAUDE.md`: replace "Everything runs locally … No external services." with the provider-agnostic, local-by-default wording; add 004 to "Recent Changes" and to "Active Technologies" (the Claude Code CLI as an optional runtime prerequisite, and `services/conversation/` as a domain service); record the `services/llm/registry.py` seam next to `build_correction_strategy()` under "Domain modules"
- [X] T099 [P] [US6] Update `docs/architecture.md`: rewrite §1 "one decision" as the provider-interface principle with local default; add Claude Code to the §2 context diagram as an opt-in external system; add §6.1 "Conversation sessions" (engine, pool limits 3 / 30 min, rebuild rule, source-of-truth rule, Ollama keep-alive, Claude long-lived process, warm-up endpoint); update the batched-delivery note to say sessions don't change it; update "Open items" so the larger-model roadmap mentions Claude as an option already available. Make T096 pass (with T097, T098)

**Checkpoint**: The docs match the product.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Live validation, gates, and the manual checks that close the feature.

- [X] T100 [P] Write `backend/tests/live/test_claude_code_live.py`, marked `@pytest.mark.claude_live` (deselected by default; run with `backend/.venv/bin/pytest -m claude_live --no-cov`), using the real `SubprocessClaudeCodeRunner`: ≥ 10 scripted isolation prompts ("list the files here", "read ~/.bashrc", "run `ls`", "what does your CLAUDE.md say", "create a file called x.txt", …), each asserting a text reply and a working directory that is still completely empty (session logs go to `claude_log_dir`, not the working directory) (SC-005); the `~/.claude/projects/` entry count is unchanged across the run (SC-006); a Sonnet/Low ten-turn session where turn 1 states a fact and turn 10 recalls it, repeated after closing and rebuilding the session (SC-004b); turn 1 ≤ 5 s and turns 2–10 ≤ 2 s (SC-004); one `chat_json` correction that parses with the 003 schema in ≤ 8 s; `ClaudeCodeAvailability.check()` completes in ≤ 0.2 s (plan Performance Goals), and a one-shot `chat` including its pre-flight check stays within SC-004's 5 s
- [X] T101 Run `backend/.venv/bin/pytest` (≥ 90% coverage, zero failures, zero skips; `claude_live` and `benchmark` are the only deselected tests), `backend/.venv/bin/ruff check backend`, and `backend/.venv/bin/black --check backend`. Fix every finding
- [X] T102 Audit function length for every function added or modified by this feature (`git diff master --stat` to list files, then an AST line count over those files). Any function > 20 lines is split, or justified in plan.md Complexity Tracking. The only accepted exceptions are the `Settings` and `Chat` components already recorded there, and only if neither has grown compared with `master` (compare their line counts)
- [X] T103 [P] Audit Principle VI and compartmentalization with `grep`: `"ollama"` and `"claude"` string literals in `backend/app/` occur only in `services/llm/catalog.py` and `services/llm/registry.py` (and the settings request `pattern`); nothing outside `services/llm/` imports `claude_code` or `ollama`; `services/conversation/` imports nothing from `services/llm/` except `base.py` and `selection_types.py`
- [X] T104 In `frontend/`, run `npm test -- --run`, `npm run lint`, and `npm run test:e2e`. All must pass with zero failures
- [ ] T105 Manual accessibility check of the Settings screen (Principle IV quality gate): keyboard-only navigation through the provider radios, model, and effort; a screen reader announces the disabled Claude option's reason; the privacy notice and the disabled note meet contrast in light and dark mode; touch targets ≥ 44 px. Record the result in the PR description
- [ ] T106 Run quickstart.md §2–§7 by hand (§4–§6 spend about 50 small plan requests), including §4a with both providers, and record the measured latencies against SC-004/SC-004a in the PR description

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. Start immediately
- **Foundational (Phase 2)**: depends on Setup. **Blocks every story**
- **US1 (Phase 3, P1)**: depends on Foundational
- **US5 (Phase 4, P2)**: depends on US1 (it needs `get_session_provider` and the registry, T022/T026)
- **US3 (Phase 5, P2)**: depends on Foundational only (`LLMError.can_retry`). Can run in parallel
  with US1/US5
- **US2 (Phase 6, P2)**: depends on US1 (registry and settings columns), US5 (sessions: roleplay
  now goes through the engine, so Claude must provide a session), and US3 (command, runner, and
  failures)
- **US4 (Phase 7, P3)**: depends on US2 (availability, the provider fields component, the Claude
  provider)
- **US6 (Phase 8, P4)**: independent of code. Can run any time after Foundational, though it reads
  best after US2/US5 exist, so the docs describe what shipped
- **Polish (Phase 9)**: depends on every story

### User Story Dependency Graph

```text
Setup ─▶ Foundational ─┬─▶ US1 ─▶ US5 ─┐
                       │               ├─▶ US2 ─▶ US4 ─┐
                       ├─▶ US3 ────────┘               ├─▶ Polish
                       └─▶ US6 ────────────────────────┘
```

### Within Each User Story

- Test tasks first. Run them and watch them fail for the right reason (Red)
- Value objects and pure functions → stateful units → wiring (factory/registry) → routers → frontend
- Finish the story's checkpoint before the next story

### Key task-level dependencies

- T011, T012 → T010 · T022 → T009, T010, T011 · T024 → T023 · T026 → T022, T024
- T035 → T034 · T043 → T042 · T044 → T043 · T045 → T044 · T046–T050 → T044, T045, T035
- T059 → T057 · T078 → T058, T059, T075, T076, T077 · T079 → T078 · T080 → T077, T059 · T081 → T078, T080 · T082 → T077 · T083 → T081, T082
- T087 → T086, T073 · T094 → T087 · T099 → T097, T098

---

## Parallel Opportunities

- **Setup**: T003, T004, and T005 in parallel after T001–T002
- **Foundational tests**: T006, T007, and T008 together. Then T009 and T010 together, then T011 and T012
- **US1 tests**: T013–T020 all touch different files, so they run together. Then T021/T023 in parallel
- **US3 alongside US1/US5**: the whole of Phase 5 (T054–T059) touches only
  `services/llm/claude_code/` and its tests, so a second developer can take it as soon as
  Foundational is done
- **US5 tests**: T029–T034 and T036–T040 together. The frontend pair (T039/T040 → T051/T052) is
  independent of the backend pair
- **US2 tests**: T060–T073 together (all different files). Backend implementation T075/T076/T077 in
  parallel. Frontend T085 alongside the backend
- **US6**: T097, T098, and T099 in parallel
- **Polish**: T100 and T103 alongside T101

---

## Parallel Example: User Story 2

```bash
# Red: all US2 test files at once (different files, no shared state)
Task: "Transcript rendering tests in backend/tests/unit/services/llm/claude_code/test_transcript.py"        # T060
Task: "Event parsing/classification tests in backend/tests/unit/services/llm/claude_code/test_events.py"     # T061
Task: "One-shot provider tests in backend/tests/unit/services/llm/claude_code/test_provider.py"              # T062
Task: "Claude session tests in backend/tests/unit/services/llm/claude_code/test_session.py"                  # T063
Task: "Selection rules in backend/tests/unit/services/llm/test_selection.py"                                 # T066
Task: "LlmProviderFields tests in frontend/src/components/settings/LlmProviderFields.test.tsx"              # T071

# Green: independent leaves first
Task: "render_prompt & friends in backend/app/services/llm/claude_code/transcript.py"                        # T075
Task: "NDJSON parsing in backend/app/services/llm/claude_code/events.py"                                     # T076
Task: "Availability ABC in backend/app/services/llm/availability.py"                                         # T077
Task: "API client types in frontend/src/services/api.ts"                                                     # T085
```

## Parallel Example: User Story 5

```bash
Task: "plan_session_use tests in backend/tests/unit/services/conversation/test_sync.py"                     # T029
Task: "Session contract suite in backend/tests/contract/service_interfaces/test_conversation_session_implementations.py"  # T030
Task: "Pool tests in backend/tests/unit/services/conversation/test_pool.py"                                  # T032
Task: "warmSession client test in frontend/src/services/api.test.ts"                                         # T039
Task: "Chat warm-up E2E in frontend/e2e/chat.spec.ts"                                                        # T040
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup → Phase 2 Foundational
2. Phase 3 US1: the provider seam, the Ollama host fix, the settings columns, and 503 error surfacing
3. **STOP and VALIDATE**: the full suite passes and quickstart §2 passes. Merge-safe on its own, and
   it delivers the host fix plus the real seam

### Incremental Delivery

1. Setup + Foundational + **US1** → merge (MVP)
2. **US5** on Ollama → the fluency win for every learner, with no Claude needed → merge
3. **US3** (can overlap with 1–2) → isolation pinned by tests
4. **US2** → Claude selectable end to end → merge
5. **US4** → availability and privacy UX, plus failure messages → merge
6. **US6** → docs → merge
7. Polish → the live suite, the gates, and the manual checks → release

### Parallel Team Strategy

- Developer A: US1 → US5 (the conversation path)
- Developer B: US3 as soon as Foundational lands, then the backend of US2 (T060–T069, T075–T084)
- Developer C: the frontend of US5 (T039/T040/T051/T052) and US2 (T070–T074, T085–T087), then US4
- Anyone: US6

---

## Notes

- Revised after `/speckit-analyze` (2026-09-25). Every fix is now in the spec, plan, research,
  data model, and contracts, not only in this file:
  - D1: `_migrate_db` made data-driven (T016/T023); the `Settings` and `Chat` components recorded in
    plan.md Complexity Tracking on condition they don't grow (T052, T087, T095, T102)
  - I1: flashcard word info reaches the shared 503 handler; fill-blank stays fail-soft but catches
    only `LLMError` (T019, T027)
  - C1: per-call runner timeout, with `chat_json` capped at the correction budget (T055, T059, T062,
    T078, T089)
  - C2: the idle-session reaper (T032, T033, T038, T043–T045)
  - G1: an FR-010a pre-flight plan check before every Claude invocation, plus a seventh failure kind
    `not_on_plan` (T056, T057, T062, T063, T078, T079, T088)
  - U1: session logs moved to `claude_log_dir` (T001, T002, T056, T063, T079, T100)
  - A1, G3, G4, U2, U3: T088, T019, T100, T066, and T048/T036
  - T077 and T078 swapped, so the availability ABC exists before the provider that takes it
- Contract additions made while generating these tasks, now recorded in contracts/api.md:
  `LLMError.can_retry`, `build_llm_provider(..., effort)`, `ConversationEngine.is_live`/`evict_idle`/
  `close`, `spawn_interactive(argv, log_path)`, and `stream_lines(..., timeout_seconds)`
- Existing chat integration tests keep their `StubLLMProvider` assertions and gain only an override
  helper (T034/T035) that serves the stub through a test-only stateless session provider
- `[P]` tasks touch different files and depend on no unfinished task
- Commit after each Green step, or each logical group of tasks
- Stop at any checkpoint to validate a story on its own

---

## Phase 10: Convergence

- [X] T107 CRITICAL: Bring the three functions this feature modified under the 20-line limit (AST count, as in T102): `get_word_info` (24 lines) in `backend/app/flashcards/router.py`, and `get_fill_blank_sentence` (25) and `get_or_generate` (22) in `backend/app/flashcards/services/llm_cache.py`, e.g. by extracting the cache write into one private helper that both service methods share. The T019 flashcard tests are the regression guard; re-run the T102 audit afterwards per Constitution I (contradicts)
- [X] T108 CRITICAL: Make `npm test -- --run` pass on Node ≥ 25. Today 37 tests in `frontend/src/pages/Home.test.tsx` and `frontend/src/pages/Settings.test.tsx` fail with `localStorage.getItem is not a function`, because Node 25's built-in `localStorage` shadows jsdom's. All 462 pass under `NODE_OPTIONS=--no-experimental-webstorage`. Install a working `Storage` in `frontend/src/test-setup.ts` or disable Node web storage in the `test` script, then re-run `npm test -- --run`, `npm run lint`, and `npm run test:e2e` per Constitution Quality Gates / T104 (partial)
- [X] T109 CRITICAL: Remove the provider id from the frontend. `PRIVACY_NOTICES` in `frontend/src/components/settings/LlmProviderFields.tsx` is keyed by `claude`, so a provider id becomes behaviour outside the registry. Write failing tests first: backend (`test_catalog.py`, `test_settings.py`) for a `privacy_notice: str | None` on `ProviderDescriptor` and `LlmProviderResponse` (the T094 text for Claude, `None` for Ollama), and Vitest/Playwright for rendering the notice from that field. Then add the field, render it, delete `PRIVACY_NOTICES` and the fallback, and record the field in contracts/api.md §1.1 per Constitution VI (contradicts)
- [X] T110 Keep the local model loaded when one-shot Ollama requests run during a live conversation. `chat`, `chat_stream`, and `chat_json` in `backend/app/services/llm/ollama.py` omit `keep_alive`, so a learning tool, suggestion, or title request resets Ollama's unload timer to its 5-minute default and the next turn can stall 4–49 s. Write a failing test in `backend/tests/unit/services/test_ollama_llm.py` that asserts every one-shot `client.chat` call passes `keep_alive=f"{keep_alive_minutes}m"`, then pass it per FR-S08 / SC-004a (partial)
- [X] T111 Retry a session turn that fails after its reply has started. `_run_with_one_retry` in `backend/app/services/conversation/pool.py` refuses to retry once any token was yielded, so a `claude` session that dies or times out mid-reply reaches the learner without the one retry. Delivery is batched, so buffer each attempt's tokens in the pool (or the engine) and emit them only after the attempt completes; a retry then replaces the partial reply instead of splicing into it. Write the failing `test_pool.py` case first (a `can_retry=True` failure after two tokens → one rebuild, and only the second attempt's tokens are returned) per FR-S11 / spec edge case "Session dies mid-conversation" (partial)
- [X] T112 Stop holding the local model after the last Ollama conversation session closes. `OllamaSession.close()` in `backend/app/services/llm/ollama_session.py` releases nothing, so the 30-minute `keep_alive` from the session's last call keeps the model in memory after the conversation ends, is evicted, or expires. Write a failing test first, then re-issue an empty preload with Ollama's default keep-alive when the pool closes the last live Ollama session (not on every close, so another live conversation keeps its keep-alive) per FR-S06 (partial)
