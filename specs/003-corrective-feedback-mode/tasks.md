---

description: "Task list for Corrective Feedback Mode (003)"
---

# Tasks: Corrective Feedback Mode

**Input**: Design documents from `/specs/003-corrective-feedback-mode/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: MANDATORY per Constitution Principle III (TDD, non-negotiable). Every implementation task
is preceded by a test task that MUST be written and MUST fail before the implementation begins.

**Organization**: Grouped by user story so each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 = Strict mode (P1), US2 = Gentle mode (P2), US3 = Restraint (P3)
- **`[X]`** done · **`[~]`** partly done — the automatable half is verified and recorded under the
  task; what remains needs a running app and a human at the browser

**Task IDs are stable labels, not an execution order.** Execution order is the order tasks appear in
this file. Tasks added after the first generation carry a letter suffix (`T030a`) so existing
references stay valid, and some E2E tasks appear earlier than their numeric neighbours because
Constitution III requires them to be written and failing before the code they cover.

## Path Conventions

Web app: `backend/app/`, `backend/tests/`, `frontend/src/`, `frontend/e2e/`.
Run Python tools through the venv: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff`.
Per the repo's shell rules, run each command as a separate invocation — never chained with `&&`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the module skeleton and the named constants everything else references.

- [X] T001 Create the corrections domain package skeleton — `backend/app/corrections/__init__.py`, `backend/app/corrections/services/__init__.py` (empty placeholders; the public interface is filled in at T029)
- [X] T002 [P] Add `low_confidence_threshold: float = 0.55` and `correction_timeout_seconds: float = 8.0` to `Settings` in `backend/app/config.py` (env prefix `OPEN_LANGUAGE_` already applies)
- [X] T003 [P] Create `backend/app/corrections/config.py` with `MAX_CORRECTIONS_PER_MESSAGE = 2`, `MAX_CONSECUTIVE_CORRECTED_ATTEMPTS = 2`, `MIN_WORDS_FOR_EVALUATION = 2`, `MAX_REPEAT_REQUESTS_PER_MESSAGE = 1` (values and rationale in research.md summary table)
- [X] T004 [P] Create test packages `backend/tests/unit/corrections/__init__.py` and `backend/tests/integration/corrections/__init__.py`
- [X] T005 [P] Create `backend/app/services/stt/confidence.py` containing only the two module constants `NO_SPEECH_PROB_THRESHOLD = 0.6` and `COMPRESSION_RATIO_THRESHOLD = 2.4`, each with its Whisper-default provenance in a comment; the aggregation logic lands at T075

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared substrate every mode needs — the preference, persistence, the evaluator, the
strategy seam, the Off-mode baseline, and the two chat-screen fixes (resume, turn status) that both
US1 and US2 depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### 2A — The correction_mode preference (FR-001, FR-002, FR-003, FR-005)

- [X] T006 [P] Write failing test: `correction_mode` defaults to `"off"`, round-trips through GET/PUT, and rejects an invalid value with 422 — in `backend/tests/integration/routers/test_settings.py`
- [X] T007 [P] Write failing test: `_migrate_db()` adds `correction_mode` to an `app_settings` table created without it, and is idempotent on a second run — in `backend/tests/unit/test_database.py`
- [X] T008 Add `correction_mode: Mapped[str]` column (`String(10)`, `nullable=False`, `default="off"`) to `AppSettings` in `backend/app/models/app_settings.py`
- [X] T009 Add `_add_column_if_missing(conn, "app_settings", "correction_mode VARCHAR(10) NOT NULL DEFAULT 'off'")` to `_migrate_db()` in `backend/app/database.py`
- [X] T010 Add `correction_mode: str` to `AppSettingsRecord` in `backend/app/services/storage/base.py` and map it in `_settings_to_record()` in `backend/app/services/storage/sqlite.py`
- [X] T011 Add `correction_mode` to `SettingsResponse`, `_to_response()`, and `UpdateSettingsRequest` (validated `pattern="^(off|gentle|strict)$"`) in `backend/app/routers/settings.py`

### 2B — Structured LLM output (research.md R4)

- [X] T012 [P] Write failing contract test for `StructuredLLMProvider` — a stub returns schema-valid JSON; a raising stub surfaces `LLMError` — in `backend/tests/contract/service_interfaces/test_structured_llm_provider.py`
- [X] T013 Add the `StructuredLLMProvider` ABC with the single method `chat_json(messages, schema) -> str` to `backend/app/services/llm/base.py` (a separate ABC — do NOT add the method to `LLMProvider`)
- [X] T014 Make `OllamaLLMProvider` implement `StructuredLLMProvider`, passing `format=schema` to `ollama.chat`, in `backend/app/services/llm/ollama.py`
- [X] T015 Add `get_structured_llm()` dependency to `backend/app/services/factory.py`

### 2C — Corrections persistence (data-model.md)

- [X] T016 [P] Write failing contract test for `CorrectionStorageProvider` — `get_pause_state` on an unknown conversation returns a zeroed snapshot without creating a row; `save_feedback` is insert-only; `list_feedback` orders by `(message_id, rank)` — in `backend/tests/contract/service_interfaces/test_correction_storage_provider.py`
- [X] T017 [P] Create `backend/app/corrections/models.py` with the `MessageFeedback` and `ConversationCorrectionState` ORM models plus the `FeedbackKind`, `ErrorCategory`, and `CorrectionMode` str-enums, per the column tables in data-model.md
- [X] T018 Create `backend/app/corrections/services/storage.py` with the `CorrectionStorageProvider` ABC and the frozen value objects `FeedbackDraft`, `FeedbackRecord`, `PauseSnapshot`
- [X] T019 Create `backend/app/corrections/services/sqlite_storage.py` implementing `SQLiteCorrectionStorageProvider` against an injected `Session`
- [X] T020 Import `app.corrections.models` in `init_db()` in `backend/app/database.py` so `create_all()` creates both new tables
- [X] T021 Add `get_correction_storage()` dependency to `backend/app/services/factory.py`

### 2D — Error evaluation (FR-006, FR-007, FR-008, FR-009)

- [X] T022 [P] Write failing tests for the evaluation prompt: it names verb conjugation, agreement, word choice, and word order as correctable; it explicitly rules out diacritics, regionally valid variation, and unidiomatic-but-correct phrasing; it forbids praise; it caps at two; and **it asks for the `explanation` in the learner's native language while requiring `corrected_text` in the target language** (FR-015) — in `backend/tests/unit/corrections/test_prompts.py`
- [X] T023 [P] Write failing tests for `LlmCorrectionEvaluator`: parses valid JSON; strips code fences; truncates to `MAX_CORRECTIONS_PER_MESSAGE`; returns empty on malformed JSON, on `LLMError`, and for input under `MIN_WORDS_FOR_EVALUATION` words; never raises — in `backend/tests/unit/corrections/test_evaluator.py`
- [X] T024 Create `backend/app/corrections/prompts.py` with the evaluation prompt builder and its JSON Schema constant
- [X] T025 Create `backend/app/corrections/services/evaluator.py` with the `CorrectionEvaluator` ABC, the `EvaluationRequest` value object, and `LlmCorrectionEvaluator` (depends on `StructuredLLMProvider` only)

### 2E — Strategy seam, Off-mode baseline, and the replay endpoint

- [X] T026 [P] Write failing tests: `OffCorrectionStrategy` returns `TurnPlan((), generate_reply=True, reply_prompt_suffix=None)` and performs no LLM call and no storage read — in `backend/tests/unit/corrections/test_strategies.py`
- [X] T027 [P] Write failing test: with `correction_mode="off"` a turn produces exactly one LLM call and an SSE frame sequence byte-identical to the pre-feature stream (SC-002) — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T028 Create `backend/app/corrections/services/strategies.py` with the `CorrectionStrategy` ABC, the frozen `TurnPlan` and `TurnContext` value objects, and `OffCorrectionStrategy` as a null object
- [X] T029 Fill `backend/app/corrections/__init__.py` with the module's public interface — `CorrectionMode`, `TurnPlan`, `FeedbackDraft`, `build_correction_strategy(mode, …)` — as the only place a mode string becomes behaviour
- [X] T030 Add `get_correction_strategy()` dependency to `backend/app/services/factory.py`
- [X] T030a [P] Write failing tests for the router's correction wiring, driven by **stub strategies** rather than a real mode: a stub returning feedback causes exactly one `feedback` frame, emitted after `user_message_saved` and before any `token` frame, with the notes persisted; a stub returning `generate_reply=False` produces zero `token` frames, no assistant row, and `done` with `message_id: null`; a stub returning a `reply_prompt_suffix` has it appended to the system prompt without displacing the `CRITICAL LANGUAGE RULE` — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T030b [P] Write failing tests for fail-open resilience (FR-026, SC-004a): a strategy that exceeds `correction_timeout_seconds`, one that raises `LLMError`, and one whose evaluator returns unparseable prose each produce the §2.1 stream — reply delivered, **no** `feedback` frame, **no** error frame — and each logs at `warning`; assert the resulting stream is identical to the Off-mode stream — in `backend/tests/integration/corrections/test_correction_resilience.py`
- [X] T031 Wire strategy dispatch into `send_message` in `backend/app/routers/chat.py`: call `plan_turn` under `asyncio.wait_for(timeout=settings.correction_timeout_seconds)` failing open to an empty plan on `TimeoutError`/`LLMError` (log at `warning`), persist `plan.feedback`, emit the `feedback` SSE frame only when non-empty, append `plan.reply_prompt_suffix` to the system prompt, and skip reply generation entirely when `plan.generate_reply` is false — emitting `done` with `message_id: null`
- [X] T032 [P] Write failing test for `GET /api/corrections/conversations/{id}`: returns feedback ordered by `(message_id, rank)`, excludes `mode="gentle"` rows, returns zeroed state for an uncorrected conversation, 404s for an unknown one — in `backend/tests/integration/corrections/test_correction_endpoints.py`
- [X] T033 Create `backend/app/corrections/schemas.py` and `backend/app/corrections/router.py` implementing `GET /corrections/conversations/{conversation_id}` per contracts/api.md §1.5
- [X] T034 Register the corrections router with `prefix="/api"` in `backend/app/main.py`

### 2F — Frontend foundation

- [X] T035 [P] Add `correction_mode: 'off'` to `mockSettings`, plus a `mockFeedbackNote` fixture and an SSE helper that emits a `feedback` frame, in `frontend/e2e/fixtures.ts`
- [X] T036 [P] Add `correction_mode` to `AppSettings`, add the `FeedbackKind`/`FeedbackNoteData`/`ConversationFeedback` types and `getConversationFeedback()`, widen `onDone` to `{ message_id: number | null }`, and append the optional `onFeedback` and `transcriptionConfidence` parameters to `streamChatMessage` — in `frontend/src/services/api.ts`
- [X] T037 [P] Write failing tests: the correction-mode control renders three options, defaults from the loaded settings, submits the chosen value, and exposes the performance hint via `aria-describedby` — in `frontend/src/pages/Settings.test.tsx`
- [X] T038 Add the correction-mode radio group (real `fieldset`/`legend`) and the performance hint — extra model pass per message, several seconds per turn without a GPU, a slow check is skipped so the conversation continues — in `frontend/src/pages/Settings.tsx`, using `--color-text-muted` and no hardcoded hex
- [X] T039 Extend `frontend/e2e/settings.spec.ts` with the correction-mode selection and hint-visibility cases
- [X] T040 [P] Write failing E2E regression tests: reloading a conversation that already has messages restores the transcript and does NOT call `/api/chat/{id}/open`; opening an empty conversation still calls it — in `frontend/e2e/chat.spec.ts`
- [X] T041 Make the chat screen resume-aware in `frontend/src/pages/Chat.tsx`: fetch `GET /api/conversations/{id}/messages` on mount, call `streamChatOpen` only when that returns an empty list, and hydrate feedback and pause state from `getConversationFeedback()` in the same load (research.md R8)
- [X] T042 [P] Create `frontend/src/components/chat/TurnStatusIndicator.tsx` and `TurnStatusIndicator.test.tsx` — an `aria-live="polite"` status line reading "Checking your sentence…", using design-system tokens only
- [X] T042a Write failing E2E turn-status tests in `frontend/e2e/corrective-feedback.spec.ts` (creates the file; later tasks extend it) covering quickstart checks 6.1, 6.2 and 6.4: with mode ≠ Off the indicator appears within 1 s of sending and no assistant bubble exists before the first token; the indicator clears and the bubble appears on the first token; and **with mode Off the screen behaves exactly as before — the assistant placeholder still appears on send and no indicator is rendered** (SC-002, SC-004)
- [X] T043 Introduce turn status `idle | checking | replying` in `frontend/src/pages/Chat.tsx`, reading `correction_mode` from the `api.getSettings()` call the page already makes on mount: enter `checking` on send when `correction_mode !== 'off'`, and **in that case only, create the assistant bubble on the first `token` frame rather than on send**, so a flagged Strict turn never produces a placeholder to remove. **Off mode keeps today's send-time placeholder untouched** — deferring it there would be a visible change and would break SC-002's "zero visual change" (research.md R10, R11)

**Checkpoint**: The mode can be set and read, Off mode is provably unchanged, corrections can be
stored and replayed, and the chat screen resumes and reports its own status. User stories can begin.

---

## Phase 3: User Story 1 - Learner is told when they got it wrong and asked to try again (Priority: P1) 🎯 MVP

**Goal**: In Strict mode a substantive error yields a correction — what was wrong, the fixed
sentence, a prompt to retry — as the turn's *only* output, with no character reply generated at all
until the learner tries again.

**Independent Test**: Set the mode to Strict, send a sentence with a known conjugation error, and
confirm the learner receives an explicit correction with the fixed sentence and a retry prompt, that
no character reply is produced for that turn, and that the scenario does not advance until they
respond.

### Tests for User Story 1 (MANDATORY — write before implementation)

> **TDD REQUIREMENT: write these FIRST and confirm they FAIL before implementing.**

- [X] T044 [P] [US1] Write failing tests for `CorrectionPauseTracker` covering the state-machine table in data-model.md: a correction increments the counter; a clean message resets it to 0; **at two consecutive corrected attempts the third message is answered whatever it contains, including a brand-new error** (FR-018, SC-006) — in `backend/tests/unit/corrections/test_pause_tracker.py`
- [X] T045 [P] [US1] Write failing tests: `StrictCorrectionStrategy` returns `generate_reply=False` with feedback when findings exist, and `generate_reply=True` with empty feedback when they do not; only Strict may ever return `generate_reply=False` — in `backend/tests/unit/corrections/test_strategies.py`
- [X] T046 [P] [US1] Write failing test: a flagged Strict turn emits `feedback` then `done` with `message_id: null`, streams zero `token` frames, and **stores no assistant message row** (FR-016) — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T047 [P] [US1] Write failing test: the message after a Strict correction gets a character reply built with the full prior history intact (FR-017) — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T048 [P] [US1] Write failing test: a conversation reopened mid-pause still reports `awaiting_retry: true` with the counter carried over, and previously issued corrections are still returned (FR-022, FR-029) — in `backend/tests/integration/corrections/test_correction_endpoints.py`
- [X] T049 [P] [US1] Write failing tests: `FeedbackNote` renders the error fragment, corrected text, and explanation for `kind="correction"`, carries `role="note"` with an accessible label identifying it as learning feedback, and uses no hardcoded hex colours (FR-014, FR-019, FR-023) — in `frontend/src/components/chat/FeedbackNote.test.tsx`
- [X] T049a [P] [US1] Write failing tests: `MessageBubble` renders content passed through its `children` slot beneath the message text, and renders nothing extra when no children are supplied — in the existing `frontend/src/components/chat/MessageBubble.test.tsx`
- [X] T056 [US1] Write failing E2E coverage of the Strict happy path in `frontend/e2e/corrective-feedback.spec.ts`: the correction renders under the learner's own message, the conversation does not advance, the composer switches to retry mode, and the retry receives a character reply
- [X] T057 [US1] Write failing E2E assertions in `frontend/e2e/corrective-feedback.spec.ts` that a flagged Strict turn issues **no** `/api/audio/tts/` request (FR-020, SC-005) and that an assistant bubble is **never** created — asserted during the turn, not merely absent at the end (quickstart check 6.3)

> T056 and T057 keep their original IDs but run here, before T053–T055, because they are the only
> tests covering the `Chat.tsx` feedback handling and the retry composer. Confirm both fail first.

### Implementation for User Story 1

- [X] T050 [US1] Create `backend/app/corrections/services/pause_tracker.py` implementing `CorrectionPauseTracker`, including the derived `awaiting_retry` rule and the `MAX_CONSECUTIVE_CORRECTED_ATTEMPTS` cap
- [X] T051 [US1] Add `StrictCorrectionStrategy` to `backend/app/corrections/services/strategies.py`, composing the evaluator and pause tracker via constructor injection
- [X] T052 [US1] Register `strict` in `build_correction_strategy()` in `backend/app/corrections/__init__.py`
- [X] T053 [P] [US1] Create `frontend/src/components/chat/FeedbackNote.tsx` styled per research.md R9 — `--color-warning` rule, `--color-surface-raised` background, `--radius-lg`, `--shadow-sm`, tokens only
- [X] T054 [US1] Render attached feedback through the existing `children` slot in `frontend/src/components/chat/MessageBubble.tsx`
- [X] T055 [US1] Handle the `feedback` SSE frame in `frontend/src/pages/Chat.tsx`: attach notes to the learner's message and switch the composer to retry mode (placeholder "Try again…") when `awaiting_retry` is set — turning T056 and T057 green
- [~] T058 [US1] Run the User Story 1 checks from [quickstart.md](quickstart.md) §2 (1.1–1.5), §3a, §3b (Strict does not trap you, SC-006), and §3b-2 (the wait is legible, SC-004), timing the settings round-trip against the 15-second budget (SC-001), and record any deviation

**Checkpoint**: Strict mode is fully functional and demonstrable on its own — this is the MVP.

---

## Phase 4: User Story 2 - Learner is corrected without breaking the conversation (Priority: P2)

**Goal**: In Gentle mode the character stays in character, speaks only the target language, and
restates the corrected form naturally inside its own reply. The conversation never stops.

**Independent Test**: Set the mode to Gentle, send a sentence with a known error, and confirm the
character's single reply contains the corrected form woven in naturally, is entirely in the target
language, and does not stop to ask the learner to repeat anything.

### Tests for User Story 2 (MANDATORY — write before implementation)

- [X] T059 [P] [US2] Write failing tests: `GentleCorrectionStrategy` always returns `generate_reply=True`, supplies a `reply_prompt_suffix` when findings exist and `None` when they do not, and never touches the pause tracker (FR-013) — in `backend/tests/unit/corrections/test_strategies.py`
- [X] T060 [P] [US2] Write failing tests: the recast instruction never requests native-language output, never displaces the existing `CRITICAL LANGUAGE RULE` at the head of the roleplay prompt, and instructs a natural restatement rather than an explicit correction (FR-011, FR-012, SC-007) — in `backend/tests/unit/corrections/test_prompts.py`
- [X] T061 [P] [US2] Write failing test: a Gentle turn with an error streams reply tokens, emits **no** `feedback` frame, persists the correction with `mode="gentle"`, and leaves the pause counter untouched — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T065 [US2] Write failing E2E coverage in `frontend/e2e/corrective-feedback.spec.ts`: Gentle produces one uninterrupted reply, shows the checking indicator while evaluating, never renders a feedback note, and **does issue a `/api/audio/tts/` request for that reply** — the recast is part of the character's speech and must be voiced normally (FR-021)

> T065 keeps its ID but runs here, before T062–T064, per Constitution III. Confirm it fails first.

### Implementation for User Story 2

- [X] T062 [US2] Add the recast instruction builder to `backend/app/corrections/prompts.py`
- [X] T063 [US2] Add `GentleCorrectionStrategy` to `backend/app/corrections/services/strategies.py`
- [X] T064 [US2] Register `gentle` in `build_correction_strategy()` in `backend/app/corrections/__init__.py`
- [~] T066 [US2] Run the User Story 2 checks from [quickstart.md](quickstart.md) §2 (2.1–2.4) and §3c, reading replies for native-language leakage (SC-007)

**Checkpoint**: Gentle and Strict both work, independently selectable and independently testable.

---

## Phase 5: User Story 3 - Learner is not nagged (Priority: P3)

**Goal**: Correct only what would actually confuse a native speaker, never more than two per message,
never with praise — and never invent a correction from a mishearing. Adds the transcription-confidence
pipeline and the Strict repeat request.

**Independent Test**: Send a batch of sentences covering correct text, trivial deviations (missing
diacritic, valid regional word choice), and multi-error text, and confirm corrections appear only for
substantive errors and never exceed two per message. Separately, send a low-confidence spoken message
and confirm no correction is produced in either mode.

### Tests for User Story 3 (MANDATORY — write before implementation)

- [X] T067 [P] [US3] Write failing tests for the confidence aggregator covering every row of the research.md R1 edge table (quickstart checks 5.1–5.13) against synthetic segments — token-count weighting not duration; silence/empty/zero-duration segments excluded; **text present with all segments silent yields 0.0**; **`compression_ratio > 2.4` forces low confidence despite high `avg_logprob`**; no segments yields `None`; empty token lists yield `None` not a division error — in `backend/tests/unit/services/test_transcription_confidence.py`
- [X] T068 [P] [US3] Update the STT contract test for the added `confidence` field, confirming the existing `StubSTTProvider` still satisfies the contract unmodified (LSP) — in `backend/tests/contract/service_interfaces/test_stt_provider.py`
- [X] T069 [P] [US3] Write failing test: `WhisperSTTProvider` delegates to the aggregator rather than computing confidence inline — in `backend/tests/unit/services/test_whisper_stt.py`
- [X] T070 [P] [US3] Write failing tests for the classification rule: `confidence is None` is **not** low-confidence (typed input evaluated normally), `0.0` is, and a value below the threshold is — in `backend/tests/unit/corrections/test_strategies.py`
- [X] T071 [P] [US3] Write failing tests: a repeat request is issued at most once per message, and a second consecutive low-confidence message proceeds normally with no correction (FR-027) — in `backend/tests/unit/corrections/test_pause_tracker.py`
- [X] T072 [P] [US3] Write failing tests: a low-confidence message in Strict yields a repeat request with no correction and no reply; in Gentle it yields an ordinary reply with no correction and no pause (FR-010a, FR-028) — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T073 [P] [US3] Write failing tests: four substantive errors surface at most two corrections ordered by rank; a missing-diacritic-only sentence surfaces none; a correct sentence surfaces no praise (FR-007, FR-008, FR-009) — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T073a [P] [US3] Write failing test: `POST /api/audio/transcribe` returns `confidence` and `is_low_confidence`, with `confidence: null` passed through as `is_low_confidence: false` and `0.0` as `true` (FR-010) — in `backend/tests/integration/routers/test_transcribe.py`
- [X] T073b [P] [US3] Write failing tests: `_migrate_db()` adds `transcription_confidence` and `is_low_confidence` to a `messages` table created without them and is idempotent on a second run; `MessageRecord` exposes both fields — in `backend/tests/unit/test_database.py`
- [X] T073c [P] [US3] Write failing tests for the request contract (quickstart 5.14, 5.15): a `transcription_confidence` outside 0.0–1.0 returns `422`; a value supplied with `input_source="keyboard"` is ignored and persisted as NULL, and that message is still evaluated normally — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T074 [P] [US3] Write the SC-003 **pipeline** test over the fixed 20-sentence set (10 with a deliberate substantive error, 10 correct) against a scripted evaluator stub, asserting that every finding the evaluator reports is surfaced and that clean sentences produce none. **This is a determinism test of the wiring, not a measurement of detection quality — it does not satisfy SC-003** — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T074a [P] [US3] Write the SC-003 **detection benchmark** over the same 20 sentences against the **real Ollama evaluator**, asserting ≥ 8/10 detected and 0/10 false positives, and printing the two figures. Mark it `@pytest.mark.benchmark` and deselect it by default in `pyproject.toml` so CI stays hermetic; it is run by hand at T084 and recorded there — in `backend/tests/integration/corrections/test_correction_benchmark.py`
- [X] T083 [US3] Write failing E2E coverage in `frontend/e2e/corrective-feedback.spec.ts`: a low-confidence spoken message in Strict renders the repeat request as a note, issues no TTS request, and produces no grammar correction; and the `POST /chat/{id}/message` body carries `transcription_confidence` for a voice message **including when the value is `0.0`**

> T083 keeps its ID but runs here, before T075–T082, per Constitution III. Confirm it fails first.

### Implementation for User Story 3

- [X] T075 [P] [US3] Implement the three-step aggregator in `backend/app/services/stt/confidence.py` — filter contentless segments, force low confidence on a repetition loop, then return `exp(Σ(avg_logprob×n_tokens)/Σ n_tokens)`; log `segment.temperature > 0` at `debug` without gating on it
- [X] T076 [US3] Add `confidence: float | None = None` to `TranscriptionResult` in `backend/app/services/stt/base.py` (defaulted, to preserve LSP) and call the aggregator from both the primary and CPU-fallback paths in `backend/app/services/stt/whisper.py`
- [X] T077 [US3] Return `confidence` and `is_low_confidence` from `POST /audio/transcribe` in `backend/app/routers/audio.py`
- [X] T078 [US3] Add `transcription_confidence` and `is_low_confidence` columns to `Message` in `backend/app/models/message.py`, the two `_add_column_if_missing` calls in `backend/app/database.py`, the fields on `MessageRecord`, and the `save_message` parameters in `backend/app/services/storage/base.py` and `backend/app/services/storage/sqlite.py`
- [X] T079 [US3] Add `transcription_confidence: float | None = None` (validated `ge=0.0, le=1.0`) to `ChatMessageRequest` in `backend/app/routers/chat.py`, ignoring it and persisting NULL when `input_source == "keyboard"`
- [X] T080 [US3] Apply the low-confidence gate in `backend/app/corrections/services/strategies.py` so no correction is produced in any mode for a low-confidence message (FR-010a)
- [X] T081 [US3] Add the repeat-request branch to `StrictCorrectionStrategy` and the `awaiting_clarification` transitions to `CorrectionPauseTracker`, with the repeat-request text in `backend/app/corrections/prompts.py`
- [X] T082 [US3] Surface `confidence`/`is_low_confidence` from `transcribeAudio` in `frontend/src/services/api.ts` and forward the value through `sendMessage` in `frontend/src/pages/Chat.tsx` (including a `0.0` value — do not treat it as falsy) — turning T083 green
- [~] T084 [US3] Run the User Story 3 checks from [quickstart.md](quickstart.md) §2 (3.1–3.6, 5.1–5.16) and §3e, then run the deselected T074a benchmark by hand against the real model and record the detected/false-positive figures against SC-003
  - **Benchmark run (T074a) against `llama3.1:8b`: detected 10/10, false positives 10/10 — SC-003 NOT met.**
    Detection clears the >= 8/10 bar comfortably. Restraint does not: the model flags every correct
    sentence, and its inventions are themselves wrong (e.g. "Ella es mi hermana" -> "hermano";
    "examen" -> "exámen", which the prompt explicitly rules out as a diacritic).
  - Prompt work done in response: the schema now requires a `verdict` field the model must commit to
    before it may list anything, plus explicit "most sentences are correct" / "never invent a mistake"
    framing. One probe measured this at 5/10 false positives, but it did not reproduce — the result is
    highly sensitive to exact wording, so the verdict gate is kept as structural restraint (it can only
    suppress, never add) rather than claimed as a fix.
  - **Decision (user, 2026-08-26): ship both modes anyway, labelled experimental.** The Settings screen
    now carries an in-app warning that corrections come from the selected model, can be wrong, are a
    reason to double-check rather than the last word, and improve with a larger model. Trying larger
    models is on the roadmap in `docs/architecture.md` § "Open items and known debt", with the measured
    figures, the prompt approaches already tried, and the untested candidates (`qwen3.6`,
    `llama3.1:70b`, `mistral`) recorded so the work is not repeated.
  - Remaining §2/§3e manual checks need a running app and a human at the browser.

**Checkpoint**: All three modes work, and the feature is restrained rather than nagging.

---

## Phase 6: Polish & Cross-Cutting Concerns

### 6A — Cross-story requirement coverage

These three span more than one mode, so they cannot be written inside a single user story. Each is
still test-first: nothing here needs new production code if the earlier phases were built correctly,
and a failure means a real gap rather than an unwritten feature.

- [X] T084a [P] Write tests for FR-004 (quickstart 4.5, 4.6): changing the mode mid-conversation applies from the learner's next message only and leaves every existing `message_feedback` row byte-identical; switching to Off while a Strict pause is open causes the next message to be answered normally — in `backend/tests/integration/corrections/test_chat_correction_modes.py`
- [X] T084b [P] Write tests for FR-024 and FR-025 (quickstart 4.10): the Grammar, Translate, and Alternative Phrasing endpoints return the same result for a message that carries `message_feedback` rows as for one that does not, and an automatic correction neither pre-fills nor suppresses the on-demand Grammar result — in `backend/tests/integration/corrections/test_correction_endpoints.py`
- [X] T084c [P] Write the SC-004a E2E (quickstart 6.5): when evaluation times out, the checking indicator clears, the reply streams, no feedback note renders, and **no error banner appears** — the turn is indistinguishable from an Off-mode turn — in `frontend/e2e/corrective-feedback.spec.ts`

### 6B — Gates and documentation

- [X] T085 [P] Document the `corrections` domain module, its two tables, and the strategy seam in `docs/architecture.md`
- [X] T086 [P] Refresh the managed agent-context section by running `/speckit-agent-context-update`, which updates `CLAUDE.md`
- [X] T087 Verify the constitution's coverage gate: `backend/.venv/bin/pytest --cov=app --cov-report=term-missing` reports ≥ 90% on new code with zero failures and zero skips
- [X] T088 [P] Run `backend/.venv/bin/ruff check backend/app backend/tests`, then `backend/.venv/bin/black --check backend/app backend/tests`, then `cd frontend && npm run lint` — each as a separate command, all clean
- [X] T089 Run the full E2E suite `cd frontend && npm run test:e2e` with zero failures (constitution gate for frontend changes)
- [~] T090 Perform the manual accessibility check from [quickstart.md](quickstart.md) §3f in **both** light and dark themes — contrast on `FeedbackNote`, its note role and label, and the Settings hint association
- [X] T091 Measure evaluation latency on the target host and tune the `OPEN_LANGUAGE_CORRECTION_TIMEOUT_SECONDS` default in `backend/app/config.py` if the 8 s budget proves wrong in practice (research.md R5)
  - **Measured** on this host (GPU, `llama3.1:8b`, warm model, 7 sentences): min 2.59 s, median 2.84 s, max 3.07 s.
    Latency did not vary meaningfully between sentences that produced corrections and clean ones.
  - **Decision: 8.0 s default kept unchanged.** Median sits inside SC-004's 4 s GPU budget with ~2.6x
    headroom to the timeout, so tightening it would only cost corrections on a slower host for no gain.
  - Note: an earlier run measured 27–83 s per call; that was a second large model contending for the
    GPU, not the evaluator. Latency here is dominated by whether the model is resident.
- [~] T092 Work through the merge checklist in [quickstart.md](quickstart.md) §4, plus the manual walkthroughs not covered by a story task — §3d (Off mode, SC-002, including that the send-time placeholder still behaves as it did before) and §3d-2 (resume, FR-022, FR-029, R8)
  - Verified automatically: pytest 595 passed / 0 skipped / 95.9% (>= 90%); ruff + black + eslint clean;
    `npm run test:e2e` 197 passed / 0 failed; `docs/architecture.md` documents the module (S 6.3);
    no hardcoded hex in `FeedbackNote.tsx`; Off mode asserted byte-identical (check 4.9) by
    `TestOffModeIsUnchanged`; reload does not call `/open` (check 4.8a) by the `chat.spec.ts` resume
    tests; no phantom bubble on a flagged Strict turn (check 6.3), polled during the turn.
  - Still open: `npm test` has 7 pre-existing failures unrelated to this feature (see below), and the
    S 3d / S 3d-2 walkthroughs plus the S 3f accessibility pass need a human at the browser.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup — **blocks all user stories**
- **User Stories (Phases 3–5)**: all depend on Foundational; may then run in parallel or sequentially in priority order
- **Polish (Phase 6)**: depends on all desired stories being complete

### Within Phase 2 (the critical path)

```text
2A settings ──┐
2B llm ───────┼──> 2D evaluator ──> 2E strategy seam ──> 2F frontend
2C storage ───┘                          (T031 chat router is the hinge)
```

2A, 2B, and 2C are mutually independent and can run concurrently. 2D needs 2B (structured output).
2E needs 2C and 2D. 2F needs 2E's endpoint (T033) for the resume hydration in T041.

Within 2E, T030a and T030b are the failing tests for T031 and are written against **stub strategies**,
so they need neither Gentle nor Strict to exist — which is what lets the hinge task be built test-first
while only the Off strategy is implemented.

### User Story Dependencies

- **US1 (P1)**: depends only on Foundational. No dependency on US2 or US3.
- **US2 (P2)**: depends only on Foundational. Shares the evaluator with US1 but adds no dependency on it — both extend the same seam.
- **US3 (P3)**: depends on Foundational, and touches files owned by US1 (`strategies.py`, `pause_tracker.py`) and US2 (`strategies.py`) when adding the low-confidence gate and repeat request. **If US1 and US3 are worked concurrently, coordinate on `strategies.py` and `pause_tracker.py`** — these are the only cross-story file collisions in the plan.

### Within Each User Story

- Tests are written and confirmed failing before any implementation (Constitution III)
- Models before services, services before endpoints, backend before the frontend that consumes it
- Story complete and independently demonstrated before moving to the next priority

---

## Parallel Opportunities

**Phase 1**: T002, T003, T004, T005 all run in parallel after T001.

**Phase 2 — three independent tracks after Setup:**

```bash
# Track A (settings)   Track B (structured LLM)   Track C (persistence)
Task: "T006 settings integration test"   Task: "T012 structured LLM contract test"   Task: "T016 correction storage contract test"
Task: "T007 migration test"              Task: "T013 StructuredLLMProvider ABC"      Task: "T017 corrections/models.py"
```

**Phase 3 (US1)** — the parallel-safe test tasks are in different files and run together:

```bash
Task: "T044 pause tracker tests in backend/tests/unit/corrections/test_pause_tracker.py"
Task: "T045 strict strategy tests in backend/tests/unit/corrections/test_strategies.py"
Task: "T046 flagged-turn SSE test in backend/tests/integration/corrections/test_chat_correction_modes.py"
Task: "T047 retry-context test in backend/tests/integration/corrections/test_chat_correction_modes.py"
Task: "T048 pause persistence test in backend/tests/integration/corrections/test_correction_endpoints.py"
Task: "T049 FeedbackNote tests in frontend/src/components/chat/FeedbackNote.test.tsx"
Task: "T049a MessageBubble children-slot tests in frontend/src/components/chat/MessageBubble.test.tsx"
```

Note T046 and T047 share a file — write them in one pass rather than concurrently. T056 and T057
also share a file (`corrective-feedback.spec.ts`, created at T042a) and are likewise written in one
pass, after the list above.

**Phase 5 (US3)**: T067–T074a are twelve test tasks across eight files; T075 (the aggregator) is
implementable in parallel with the frontend tasks of other stories since nothing else imports it yet.
T073c, T074 and T083 share files with earlier tasks — T073a and T073b are the parallel-safe pair.

**Phase 6A**: T084a, T084b and T084c are in three different files and run together.

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1: Setup (T001–T005)
2. Phase 2: Foundational (T006–T043, including T030a, T030b and T042a) — **critical, blocks everything**
3. Phase 3: User Story 1 (T044–T058, including T049a)
4. **STOP and VALIDATE**: T058 runs quickstart §3a, §3b and §3b-2 by hand — Strict mode corrects, pauses, resumes, never speaks the correction, and the wait is legible
5. Demo-ready: the learner is now told when they got it wrong

### Incremental Delivery

1. Setup + Foundational → Off mode provably unchanged, mode selectable, chat screen resumes
2. + US1 → Strict mode (**MVP**) → validate → demo
3. + US2 → Gentle mode → validate → demo
4. + US3 → restraint and the confidence pipeline → validate → demo
5. + Polish → coverage, lint, accessibility, latency tuning

Each increment leaves the previous ones working; nothing in US2 or US3 removes US1 behaviour.

### Parallel Team Strategy

Phase 2's three tracks (2A settings, 2B structured LLM, 2C persistence) suit three developers.
After Foundational, US1 and US2 are cleanly separable. Hold US3 until US1's `strategies.py` and
`pause_tracker.py` have landed, or accept a merge on those two files.

---

## Notes

- Constitution III is non-negotiable: no implementation task starts before its test task fails
- Every threshold is a named constant — no magic numbers in domain logic (research.md summary table)
- Off mode's guarantee is byte-identical output **and zero visual change**, verified on the server at T027 and in the browser at T042a — not assumed on either side
- T031 in the chat router is the single hinge for the whole feature — review it carefully; its failing tests are T030a (wiring) and T030b (fail-open)
- SC-003 is satisfied only by T074a against the real model, run by hand at T084. T074 is a wiring test and must not be reported as the benchmark
- Cross-story file collisions are limited to `strategies.py` and `pause_tracker.py` (US1 ↔ US3)
- Commit after each task or logical group; stop at any checkpoint to validate a story independently

---

## Phase 7: Convergence

Appended by `/speckit-converge` on 2026-08-27 from an assessment of the codebase against
[spec.md](spec.md), [plan.md](plan.md), and this file. Constitution violations first.

The already-open `[~]` tasks (T058, T066, T084, T090, T092) are **not** repeated here — they still
track the quickstart walkthroughs and the manual accessibility pass, which need a human at the
browser.

- [X] T093 [P] CRITICAL Scope the Vitest run to `src/` — add `test.include` / `test.exclude` to `frontend/vite.config.ts` so `npm test` stops collecting the nine Playwright specs in `frontend/e2e/`, each of which currently errors at collection per Constitution "Quality Gates — all tests pass" (contradicts)
- [X] T094 [P] CRITICAL Repair the two stale assertions in `frontend/src/components/chat/LearningToolPanel.test.tsx`: assert `checkGrammar` is called with the three arguments its signature takes (`frontend/src/services/api.ts:243`) rather than `(1)`, and scope the loading-spinner query so it no longer matches multiple `role="status"` elements — this is the FR-024 on-demand Grammar component, so its suite must be green per Constitution "Quality Gates — all tests pass" (contradicts)
- [X] T095 [P] CRITICAL Repair the five stale assertions in `frontend/src/components/chat/ExpressionHelperPanel.test.tsx`, where the `/expression helper/i` accessible-name query now matches more than one button; scope it to the intended control per Constitution "Quality Gates — all tests pass" (contradicts)
  - `ExpressionHelperPanel` no longer has a collapsed state at all: `Chat.tsx` gates the mount on
    `helperExpanded` and passes `onClose`, so the panel is always open when rendered. The five tests
    were asserting a design that had moved, and `streamHelper` had grown from 5 params to 7. The
    suite was rewritten against the current contract rather than re-scoped.
- [X] T096 [P] Write `frontend/src/pages/Chat.test.tsx` covering this feature's additions to a 517-line file currently at **0%** unit coverage — mount-time hydration with the `/open` carve-out (T041), the `idle | checking | replying` turn status including the Off-mode send-time-placeholder carve-out (T043), the `feedback` SSE frame and the retry composer (T055), and forwarding a `0.0` transcription confidence without treating it as falsy (T082) — per Constitution "≥ 90% line coverage on new code" (missing)
  - 22 tests across four groups: resume-on-mount, turn status, the feedback frame and retry composer,
    and confidence forwarding. **Chat.tsx line coverage 0% -> 91.29%** (branches 85.04%).
  - Two assertions had to be reworked to mean anything: `useAudio` drives a detached `new Audio()`
    and `AudioPlayer` renders `null`, so `document.querySelector('audio')` is always null and the
    first draft's TTS checks were vacuous. Playback is now recorded through a `play()` spy, which
    makes the FR-020 / SC-005 "nothing is voiced on a flagged Strict turn" assertion real — its
    sibling test proves the recorder does populate on an ordinary turn.
- [X] T097 Verify the frontend coverage gate — `cd frontend && npx vitest run --coverage` reports >= 90% on lines, functions, branches, and statements with zero failures. This is the frontend counterpart to T087, which checks the backend only — per Constitution "≥ 90% line coverage on new code" (missing)
  - **Gate now passes, exit 0**: lines **96.29%**, statements **96.29%**, branches **93.52%**,
    functions **91.00%** — 32 files, **435 tests**, zero failures, zero skips (was 24 files / 183 tests
    at 61.71% lines when Phase 7 opened).
  - Closing it meant paying down feature 002's coverage debt, which the user asked for on 2026-08-27.
    New suites: `flashcardsApi.test.ts` (27), `api.test.ts` (48), `Flashcards.test.tsx` (30),
    `FlashcardDecks.test.tsx` (24), `DeckConfigPanel.test.tsx` (22), `FlashcardPractice.test.tsx` (17),
    `FlashcardAnalytics.test.tsx` (15). Extended: `Chat`, `Home`, `FlashcardSummary`, `MessageBubble`,
    `LearningToolPanel`, `WordLookupPopover`, `WordListItem`, `WordFilterBar`.
  - Every file that was at 0% is now covered: `flashcardsApi.ts`, `Flashcards.tsx`, `FlashcardDecks.tsx`,
    `FlashcardAnalytics.tsx` and `DeckConfigPanel.tsx` at 100% lines, `FlashcardPractice.tsx` at 99.6%.
    `api.ts` went 44.94% -> 100%, `Home.tsx` 69.67% -> 100%, `Chat.tsx` 0% -> 98.06%.
  - `coverage.include` was narrowed to `src/**` so Playwright's `e2e/fixtures.ts` stops counting as
    application coverage. No source file is excluded to flatter the number.
  - **Two real defects surfaced by the new tests**, both fixed:
    `FlashcardPractice.handleExit` used `try/finally` with no `catch`, so a failing `endSession`
    escaped as an unhandled promise rejection and failed the whole run (`Chat.handleEndChat` already
    caught); and `store/conversationStore.ts` is dead **and broken** — nothing imports it, and it calls
    `ConversationContext.Provider({...})` as a function, which throws `TypeError: Provider is not a
    function` on any render under React 18. **It still needs deleting** (Constitution I, "dead code MUST
    be deleted") — the removal was blocked by a permissions prompt in this session.
- [X] T098 Re-run the T074a detection benchmark against the untested candidate models recorded in `docs/architecture.md` § "Open items and known debt" (`qwen3.6`, `llama3.1:70b`, `mistral`) and record detected / false-positive figures for each. `llama3.1:8b` scores 10/10 detected but **10/10 false positives**, and its inventions include a diacritic fix ("examen" → "exámen") that FR-007 rules out explicitly — per SC-003, FR-007, FR-009 (partial). Feature 003 ships experimental by the recorded 2026-08-26 decision; this task tracks the unmet criterion, it does not reopen that decision
  - **Hardware is the binding constraint.** This host is an RTX 3070 Ti with **8 GB VRAM**. Two of the
    three roadmap candidates do not fit and are therefore not viable whatever their accuracy:
    `qwen3.6` (23 GB) loads at **79% CPU / 21% GPU** and `llama3.1:70b` (42 GB) is worse. At that
    offload every turn would blow `CORRECTION_EVALUATION_TIMEOUT_SECONDS` and fail open, so the
    feature would silently do nothing (SC-004a). The qwen run was abandoned rather than scored.
  - **`mistral` (4.4 GB) fits, and inverts the failure.** Three runs: **7/10 detected, 0-1/10 false
    positives** (0, 0, 1) at ~1.6 s/sentence — comfortably inside SC-004's 4 s GPU budget.
    Compare `llama3.1:8b`: 10/10 detected but **10/10 false positives**.
  - **Neither viable model satisfies SC-003** (>= 8 detected AND 0 false positives). `mistral` meets the
    restraint half exactly and misses detection by one sentence; `llama3.1:8b` meets detection and
    fails restraint completely.
  - What `mistral` misses is specific and pedagogically real - gender agreement
    ("el leche"), the *gustar* construction ("Yo gusta mucho el cafe"), and the subjunctive
    ("Quiero que tu vienes"). Its one intermittent false positive reorders a correct sentence
    ("A mi me gusta mucho el cafe" -> "Me gusta mucho el cafe a mi"), which is the
    unidiomatic-but-correct case FR-007 rules out.
  - **Open decision for the user**: `mistral` is the better trade for US3 ("Learner is not nagged"),
    which is the story feature 003 actually fails, but it would trade away detection of three common
    error classes. Changing the default model is a product call, not a convergence fix, so
    `ollama_model` is left at `llama3.1:8b` and the figures are recorded here and in
    `docs/architecture.md` for that decision.


- [X] T099 Repair the pre-existing TypeScript build failures so `npm run build` succeeds (contradicts, Constitution "Quality Gates — linter and formatter report zero errors"). Found while verifying T097; not part of feature 003, fixed at the user's request on 2026-08-27
  - `tsc -b` was failing with **8 errors across 5 files**, so `npm run build` (`tsc -b && vite build`)
    could not produce a bundle at all. None were introduced by this feature — verified against baseline
    by stashing the branch's only config change.
  - `frontend/vite.config.ts` — `test` is not a key of Vite's `UserConfigExport`; now imports
    `defineConfig` from `vitest/config`, which re-exports it with `test` typed.
  - `src/components/flashcards/AnalyticsCharts.tsx` (the only production file) — two `<Tooltip
    formatter={(v: number) => …}>` annotations contradicted Recharts' `Formatter`, whose value may be
    `undefined`. Now `(v) => … Number(v) …`, matching the `tickFormatter` style already used on the
    adjacent `YAxis`. Behaviour is unchanged for the numeric values Recharts actually passes.
  - `src/pages/History.test.tsx` — two `Conversation` fixtures predated the `custom_prompt` field.
  - `src/pages/FlashcardSummary.test.tsx` — `beforeEach` was used but never imported, and the untyped
    `mockSummary` widened `rating` to `string`; annotating it `api.SessionSummary` narrows it to `Rating`.
  - `src/components/flashcards/CardPrompt.test.tsx` — the `makeCard` base literal omitted `translation`
    and leaned on `Partial<DeckCardItem>` to supply it, which made it optional; defaulted to `null`.
  - Verified after: `tsc -b` exits 0, `npm run build` produces a bundle, and all three suites stay green
    (vitest 205, Playwright 199, pytest 595).