---

description: "Task list for 005 — Conversation Difficulty Level"
---

# Tasks: Conversation Difficulty Level

**Input**: Design documents from `/specs/005-conversation-difficulty-level/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md)

**Tests**: Test tasks are MANDATORY per the TDD constitution (Principle III). Every test task is
written first and must be seen to FAIL before the implementation task that follows it. Unit,
contract, integration, Vitest and Playwright tests are included at the level each guarantee in
[contracts/api.md](contracts/api.md) names.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on its
own. The Settings split (research R12) sits in its own phase before US1 so the new fieldset lands on
the split page; it can be dropped (see its phase header).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1, US2, US3 (spec.md user stories); absent in Setup, Foundational, Refactor and Polish
- Paths are relative to the repository root (`backend/app`, `backend/tests`, `frontend/src`,
  `frontend/e2e`)

## Standing rules for every task

- Python through the venv only: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff`,
  `backend/.venv/bin/black` (run from `backend/`).
- Every new or modified function is ≤ 20 lines (Constitution I). The only permitted exceptions are
  the two rows in plan.md § Complexity Tracking (`Chat` and the `Settings` layout).
- Routers import only from the package root `app.conversation_levels` (Principle V). Nothing under
  `backend/app/services/conversation/`, `backend/app/services/llm/`, `backend/app/corrections/` or
  `backend/app/prompts/templates.py` is modified (plan.md § Project Structure).
- Frontend styling uses design-system tokens only (`docs/design-system.md`); no hex colours, cards use
  `--radius-lg`, shadows use `--shadow-*`.
- A frontend task is complete only when `cd frontend && npm run test:e2e` passes.

---

## Phase 1: Setup

**Purpose**: Dev dependency, package skeletons, and a green baseline to measure against.

- [ ] T001 Add `wordfreq==3.1.1` to the `dev` list under `[project.optional-dependencies]` in `backend/pyproject.toml` (dev-only; the app never imports it, research R9), then run `backend/.venv/bin/pip install -e "backend[dev]"` and confirm `backend/.venv/bin/python -c "import wordfreq"` succeeds
- [ ] T002 [P] Create empty package files `backend/app/conversation_levels/__init__.py`, `backend/tests/unit/conversation_levels/__init__.py` and `backend/tests/integration/conversation_levels/__init__.py`
- [ ] T003 Record the green baseline before any change: from `backend/` run `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff check .`, `backend/.venv/bin/black --check .`; from `frontend/` run `npm run lint`, `npm test`, `npm run test:e2e`. All must pass; note any pre-existing failure in the PR description rather than fixing it in this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `conversation_levels` domain module, the stored setting, the settings API field, the
catalogue endpoint, and the frontend API types and fixtures. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for the foundation (write first, see them fail)

- [ ] T004 [P] Write catalogue unit tests in `backend/tests/unit/conversation_levels/test_catalog.py` (data-model §1–3): `ConversationLevel` is a `StrEnum` whose values are exactly `beginner`, `elementary`, `intermediate`, `natural` in that declaration order; `DEFAULT_CONVERSATION_LEVEL is ConversationLevel.NATURAL`; `LEVEL_CATALOG` keys iterate in the same order; labels are "Beginner", "Elementary", "Intermediate", "Natural" and CEFR labels are "A1", "A2", "B1", "No limit"; each `description` is one non-empty sentence; constructing a `LevelDescriptor` with `level=NATURAL` and non-`None` limits raises `ValueError`, and one with a limited level and `limits=None` raises `ValueError`; every `SpeechLimits` integer is positive; `max_sentences_per_reply` is 2/3/4, `max_words_per_sentence` is 8/12/20 and `vocabulary_rank` is 500/1500/3000 for Beginner/Elementary/Intermediate; `max_words_per_sentence` and `vocabulary_rank` strictly increase Beginner → Intermediate (SC-003 depends on this); `LevelDescriptor` and `SpeechLimits` are frozen (assigning a field raises `FrozenInstanceError`)
- [ ] T005 [P] Write rule-renderer unit tests in `backend/tests/unit/conversation_levels/test_rules.py` (data-model §4, research R3–R5): at `NATURAL`, `with_partner_speech_rules(p, NATURAL) == p` and `with_learner_text_rules(p, NATURAL) == p`, byte for byte (FR-004); at each other level both return `p + "\n\n" + <block>` (prompt first, block last); the partner block opens with a precedence line stating the rules override anything above, and contains that level's sentence count, words-per-sentence count and vocabulary band as numbers taken from `LEVEL_CATALOG` (assert against the catalogue values, not literals), its tense and idiom text, its question rule, the ceiling rule (may speak more simply, never more complexly; FR-005), both exceptions (words essential to the scenario, words the learner just used; FR-012), answer-the-substance (FR-013) and simplify-when-asked (FR-014); the learner-text block contains words-per-sentence, tenses, vocabulary and idioms but **not** the reply-length or question rules, and states that explanations in any other language are not limited (R6); neither block contains the words "native", "English" or the value of any `native_language`; blocks for different levels differ
- [ ] T006 [P] Extend `backend/tests/unit/test_database.py`: the last entry of `_ADDITIVE_COLUMNS` is `("app_settings", "conversation_level VARCHAR(12) NOT NULL DEFAULT 'natural'")`; migrating a database created without the column adds it, and the existing settings row reads `'natural'` (FR-009)
- [ ] T007 [P] Extend `backend/tests/unit/services/test_sqlite_storage.py`: `get_settings().conversation_level == "natural"` on a fresh database; `update_settings(conversation_level="beginner")` returns and persists `"beginner"` without changing any other field
- [ ] T008 [P] Write the catalogue endpoint contract test in `backend/tests/contract/test_conversation_levels_api.py` (contract §1): `GET /api/settings/conversation-levels` returns 200 with exactly four items in `ConversationLevel` declaration order; each item's keys are exactly `{"level_id", "label", "cefr_label", "description"}` (no limits or prompt text); the set of `level_id` values equals the set accepted by `PUT /api/settings` (derive both from `ConversationLevel`, and PUT each id to prove it is accepted); Beginner's description is "Very short, simple sentences — like talking with a young child."
- [ ] T009 [P] Extend `backend/tests/integration/routers/test_settings.py` (contract §2): `GET /api/settings` includes `"conversation_level": "natural"` by default; `PUT {"conversation_level": "elementary"}` alone returns 200 with `"elementary"` and leaves every other field unchanged; that level-only PUT makes **zero** availability-checker calls even when Claude is the stored provider and its checker reports unavailable (use `tests/support/fake_availability.py`; research R8); `PUT {"conversation_level": null}` and a PUT without the field leave the stored level unchanged; `PUT {"conversation_level": "expert"}` returns 422 and nothing is stored

### Implementation for the foundation

- [ ] T010 Implement `backend/app/conversation_levels/catalog.py` to pass T004: `ConversationLevel(StrEnum)`; `DEFAULT_CONVERSATION_LEVEL = ConversationLevel.NATURAL`; `@dataclass(frozen=True, slots=True) SpeechLimits` with fields `max_sentences_per_reply: int`, `max_words_per_sentence: int`, `sentence_joining: str`, `tenses: str`, `vocabulary_rank: int`, `idioms: str`, `questions: str` and a `__post_init__` rejecting non-positive integers; `@dataclass(frozen=True, slots=True) LevelDescriptor` with `level`, `label`, `cefr_label`, `description`, `limits: SpeechLimits | None` and a `__post_init__` enforcing "`limits is None` ⇔ `level == NATURAL`" with a `ValueError` that names the level; `LEVEL_CATALOG: Mapping[ConversationLevel, LevelDescriptor]` (a `MappingProxyType`) holding the four descriptors with exactly the values in data-model §3 — Beginner: 2 / 8 / "one idea per sentence" / "present tense only" / 500 / "none" / "one easy yes/no or either/or question"; Elementary: 3 / 12 / "simple connectors only (and, but, because)" / "present, simple past, near future (\"going to\" + verb)" / 1500 / "none" / "one simple open question"; Intermediate: 4 / 20 / "at most one subordinate clause" / "all common indicative tenses; subjunctive only in fixed everyday phrases" / 3000 / "common, widely understood idioms only" / "as the conversation needs"; Natural: `limits=None`. Every number is a named field, never a literal elsewhere
- [ ] T011 Implement `backend/app/conversation_levels/rules.py` to pass T005: public `with_partner_speech_rules(prompt: str, level: ConversationLevel) -> str` and `with_learner_text_rules(prompt: str, level: ConversationLevel) -> str`, each returning `prompt` unchanged when the descriptor's `limits is None` and otherwise `f"{prompt}\n\n{block}"`; private renderers `_partner_speech_block(limits)` and `_learner_text_block(limits)` built from short, numeric, imperative lines (research R4) with **no example sentences in any language** and no mention of the native language (FR-015); the partner block starts with the precedence line ("These rules about how you speak override anything above.") and ends with the ceiling, exceptions, substance and simplify-on-request lines; the learner block limits "the target-language words the learner will say or read" and says explanations in any other language are not limited. Pure functions: no I/O, no settings lookup, each ≤ 20 lines
- [ ] T012 Export exactly five public names from `backend/app/conversation_levels/__init__.py` via `__all__`: `ConversationLevel`, `DEFAULT_CONVERSATION_LEVEL`, `LEVEL_CATALOG`, `with_partner_speech_rules`, `with_learner_text_rules` (research R10). Add a test in `backend/tests/unit/conversation_levels/test_catalog.py` asserting `set(app.conversation_levels.__all__)` equals those five
- [ ] T013 Append `("app_settings", f"conversation_level VARCHAR(12) NOT NULL DEFAULT '{DEFAULT_CONVERSATION_LEVEL.value}'")` as the **last** entry of `_ADDITIVE_COLUMNS` in `backend/app/database.py`, importing `DEFAULT_CONVERSATION_LEVEL` from `app.conversation_levels` (passes T006)
- [ ] T014 Add `conversation_level: Mapped[str] = mapped_column(String(12), nullable=False, default=DEFAULT_CONVERSATION_LEVEL.value)` to `AppSettings` in `backend/app/models/app_settings.py`
- [ ] T015 Add `conversation_level: str = "natural"` to `AppSettingsRecord` in `backend/app/services/storage/base.py` (with the other defaulted fields, after `llm_effort`), and copy it in `_settings_to_record` in `backend/app/services/storage/sqlite.py` (passes T007; `update_settings` needs no change)
- [ ] T016 Extend `backend/app/routers/settings.py` to pass T008 and T009: add `CONVERSATION_LEVEL_PATTERN = f"^({'|'.join(ConversationLevel)})$"` next to `LLM_PROVIDER_PATTERN`; add `conversation_level: str` to `SettingsResponse` and `_to_response`; add `conversation_level: str | None = Field(None, pattern=CONVERSATION_LEVEL_PATTERN)` to `UpdateSettingsRequest`; add `ConversationLevelResponse(level_id, label, cefr_label, description)` and `@router.get("/settings/conversation-levels", response_model=list[ConversationLevelResponse])` built from `LEVEL_CATALOG.values()` in order. Import only from `app.conversation_levels`. Confirm `update_settings_endpoint` still passes the existing tests unchanged (the level-only PUT resolves to the stored LLM selection and skips the availability check, research R8)
- [ ] T017 [P] Write a failing test in `frontend/src/services/api.test.ts` that `getConversationLevels()` issues `GET /api/settings/conversation-levels` and returns the parsed list, following the file's existing fetch-mock pattern
- [ ] T018 Extend `frontend/src/services/api.ts` (passes T017): `export type ConversationLevelId = 'beginner' | 'elementary' | 'intermediate' | 'natural'`; `export interface ConversationLevelOption { level_id: ConversationLevelId; label: string; cefr_label: string; description: string }`; add `conversation_level: ConversationLevelId` to `AppSettings`; `export const getConversationLevels = (): Promise<ConversationLevelOption[]>` next to `getSettings`
- [ ] T019 [P] Extend `frontend/e2e/fixtures.ts`: add `conversation_level: 'natural'` to `mockSettings`; add `export const mockConversationLevels` (the four levels from contract §1, with descriptions matching the backend catalogue); add `export async function mockConversationLevelsApi(page: Page)` routing `GET /api/settings/conversation-levels`; call it from `mockChatApis` so every chat spec gets the catalogue. Run `npm run test:e2e` to confirm no existing spec regresses
- [ ] T020 [P] Write `frontend/src/components/settings/useConversationLevels.test.ts` (loads the list and clears `isLoading`; a failed load sets `error` and leaves `levels` empty), then implement `frontend/src/components/settings/useConversationLevels.ts` returning `{ levels: ConversationLevelOption[], isLoading: boolean, error: string | null }` (contract §5), shaped like `useLlmProviders.ts`

**Checkpoint**: `backend/.venv/bin/pytest` (≥ 90% coverage) and `npm test` pass. The level is stored,
served and validated, and nothing a learner sees has changed yet (all prompts are still Natural).

---

## Phase 3: Settings page split (behaviour-preserving refactor, research R12)

**Purpose**: Carry out 004's deferred split of `frontend/src/pages/Settings.tsx` (370 lines) into a
`useSettingsForm` hook and per-section components, before the level fieldset is added.

**Droppable**: if skipped, T037 adds the fieldset to today's `Settings.tsx`, and a Complexity
Tracking row must be added to plan.md justifying the long component. **No behaviour change**: the
existing `frontend/src/pages/Settings.test.tsx` and `frontend/e2e/settings.spec.ts` are the guard and
must pass unmodified at the end of this phase.

- [ ] T021 Write `frontend/src/components/settings/useSettingsForm.test.ts` covering the logic being moved out of `Settings`: loads settings and voices on mount and clears `isLoading`; exposes each field's value and setter (LLM selection, whisper model, TTS voice, suggestion count, correction mode); `save()` sends every field in one `updateSettings` call, sets `isSaving` during it, then shows the success message; a failed save shows the error message
- [ ] T022 Implement `frontend/src/components/settings/useSettingsForm.ts` by moving the state, both `useEffect` loaders and `handleSave` out of `frontend/src/pages/Settings.tsx` unchanged in behaviour (passes T021); split internally so no function exceeds 20 lines
- [ ] T023 [P] Extract the correction-mode `<fieldset>` (legend "Correction Feedback", the three radios, `CORRECTION_MODE_HINT_ID`, and the "Corrections are experimental" warning) into `frontend/src/components/settings/CorrectionModeFieldset.tsx` with props `{ value, onChange }`, and add `frontend/src/components/settings/CorrectionModeFieldset.test.tsx` (renders three radios, reflects `value`, calls `onChange`, shows the experimental warning)
- [ ] T024 [P] Extract the whisper-model `<select>` (`htmlFor='whisper-model'`), the TTS-voice `<select>` (`htmlFor='tts-voice'`) and the suggestion-count `<input>` (`htmlFor='suggestion-count'`) into `frontend/src/components/settings/WhisperModelField.tsx`, `TtsVoiceField.tsx` and `SuggestionCountField.tsx`, each `{ value, onChange }` (plus `voices` for the voice field), each with a colocated `*.test.tsx` checking its label, value and change callback
- [ ] T025 [P] Extract the theme button group (`role='group' aria-label='Theme'`) into `frontend/src/components/settings/ThemeField.tsx` with `frontend/src/components/settings/ThemeField.test.tsx`
- [ ] T026 [P] Extract the save status (`role='status'`), error (`role='alert'`) and Save button into `frontend/src/components/settings/SettingsSaveBar.tsx` with props `{ isSaving, successMessage, errorMessage, onSave }`, and `frontend/src/components/settings/SettingsSaveBar.test.tsx`
- [ ] T027 Rewrite `frontend/src/pages/Settings.tsx` as declarative layout only: one `useSettingsForm()` call, `useLlmProviders()`, and the ordered section components (`LlmProviderFields`, `WhisperModelField`, `TtsVoiceField`, `CorrectionModeFieldset`, `ThemeField`, `SuggestionCountField`, `SettingsSaveBar`) in today's order, with no state, effects or handlers of its own (plan.md Complexity Tracking row 2)
- [ ] T028 Verify the refactor: `frontend/src/pages/Settings.test.tsx` and `frontend/e2e/settings.spec.ts` pass **without edits**; `npm run lint`, `npm test` and `npm run test:e2e` pass; the Settings screen looks the same in light and dark themes

**Checkpoint**: the Settings screen behaves exactly as before, and is ready for a new section.

---

## Phase 4: User Story 1 — Learner holds a conversation they can actually follow (Priority: P1) 🎯 MVP

**Goal**: The learner picks a level on the Settings screen and the roleplay partner's replies —
including the opening message, in scenario and custom-prompt conversations alike — follow that
level's limits. Natural is exactly today's behaviour.

**Independent Test**: Set Beginner on Settings, start a scenario, and check the opening and replies
against the Beginner limits; set Natural and check the standing prompt equals today's. Automated:
T029–T033. Model adherence: T041 (benchmark).

### Tests for User Story 1 (write first, see them fail)

- [ ] T029 [P] [US1] Write `backend/tests/integration/conversation_levels/test_level_in_prompts.py` using `tests/support/recording_session_provider.py` to capture each `TurnRequest` (contract §3): at `natural`, the `standing_prompt` sent by `POST /api/chat/{id}/open` and `POST /api/chat/{id}/message` equals `build_roleplay_system_prompt(...)` for that conversation exactly (FR-004); at `beginner`, it equals `with_partner_speech_rules(build_roleplay_system_prompt(...), ConversationLevel.BEGINNER)`, begins with the unchanged roleplay prompt (so the CRITICAL LANGUAGE RULE is still first, FR-015) and ends with the partner block; the opening request (`opening_instruction` set) carries the level (FR-011, US1 AS1); a custom-prompt conversation gets the block **after** the custom character text (spec edge case); with correction mode `gentle`, `TurnRequest.guidance` is identical to what it is at `natural` (FR-018, the guidance channel is untouched); the standing prompt is identical whether `llm_provider` is `ollama` or `claude`, and changing the provider leaves `conversation_level` unchanged (FR-016)
- [ ] T030 [P] [US1] Write `backend/tests/integration/conversation_levels/test_level_warm_session.py` (a separate file from T029, so both can be written in parallel): at `beginner`, `POST /api/chat/{id}/session` warms a session whose fingerprint's `standing_prompt_digest` matches the one the next `/message` turn expects, so that turn reuses the warmed session and does **not** rebuild (research R8)
- [ ] T031 [P] [US1] Write `frontend/src/components/settings/ConversationLevelFieldset.test.tsx` (contract §5): a `<fieldset>` with legend "Conversation level"; one radio per level in the given order; each radio's accessible name shows label and CEFR label (e.g. "Beginner" and "A1"); each radio's description is linked via `aria-describedby`; the radio matching `value` is checked; clicking a radio calls `onChange` with its `level_id`; the component never calls the API
- [ ] T032 [P] [US1] Extend `frontend/src/pages/Settings.test.tsx`: the "Conversation level" fieldset renders the four levels from a mocked `getConversationLevels`, shows the stored `conversation_level` checked, and Save sends the chosen `conversation_level` in the same `updateSettings` call as the other fields
- [ ] T033 [P] [US1] Extend `frontend/e2e/settings.spec.ts`: the level fieldset lists Beginner, Elementary, Intermediate and Natural from `mockConversationLevels`; the stored level is checked; choosing Elementary and pressing Save sends a `PUT /api/settings` body with `conversation_level: 'elementary'`
- [ ] T034 [P] [US1] Write the benchmark's text metrics in `backend/tests/integration/conversation_levels/text_metrics.py` (a deterministic, language-neutral sentence splitter on `.`, `!`, `?`, `…` and their Spanish inverted openers; a word splitter on Unicode letters) with unit tests in `backend/tests/integration/conversation_levels/test_text_metrics.py` that run in the default suite (not benchmark-marked): sentence counts, words per sentence, `¿…?` and `¡…!` handling, and a native-language-word detector that flags common English function words (SC-004)
- [ ] T035 [P] [US1] Write the fixed evaluation set in `backend/tests/integration/conversation_levels/evaluation_set.py` (research R9): 4 built-in scenario ids × 5 scripted Spanish learner turns = 20 turns, including at least one turn written well above Beginner (FR-013), one "más despacio, no entiendo" request (FR-014) and one scenario needing specialist words (doctor or bank; FR-012)
- [ ] T036 [US1] Write the hand-run benchmark `backend/tests/integration/conversation_levels/test_level_benchmark.py`, marked `@pytest.mark.benchmark` (deselected by the existing `addopts`; follow `tests/integration/corrections/test_correction_benchmark.py`), that plays the evaluation set at each of the four levels against the real default Ollama model through the real conversation engine, then: asserts ≥ 18/20 Beginner replies (`SC_BEGINNER_MIN_COMPLIANCE = 0.90`) and ≥ 17/20 Elementary and Intermediate replies (`SC_OTHER_MIN_COMPLIANCE = 0.85`) meet the reply-length and words-per-sentence limits read from `LEVEL_CATALOG`; asserts 0 replies contain native-language words (SC-004); prints `SC-001 …`, `SC-002 …`, `SC-003 mean words per sentence` and `share outside top 1,500` per level (`VOCABULARY_BAND_FOR_SC_003 = 1500`, via `wordfreq.top_n_list`) and asserts both rise strictly Beginner → Elementary → Intermediate → Natural; writes `level-review-sheet.md` (one reply per row with its level's allowed tenses and a blank within/outside column) to `tmp_path` and prints its path

### Implementation for User Story 1

- [ ] T037 [US1] In `backend/app/routers/chat.py` (passes T029, T030): give `_standing_roleplay_prompt` a `level: ConversationLevel` parameter and return `with_partner_speech_rules(build_roleplay_system_prompt(...), level)`; add `app_settings: AppSettingsRecord = Depends(get_app_settings)` to `_roleplay_context` and pass `ConversationLevel(app_settings.conversation_level)` (a corrupt stored value raises rather than being guessed, data-model §5); add the same dependency to `warm_session` and extract `_start_warming(engine, provider, key, standing_prompt, history)` so `warm_session` stays ≤ 20 lines (plan.md Function-length plan). Import only from `app.conversation_levels`. Existing tests in `backend/tests/integration/routers/test_chat_open.py`, `test_chat_message.py` and `test_chat_sessions.py` must pass unchanged
- [ ] T038 [US1] Implement `frontend/src/components/settings/ConversationLevelFieldset.tsx` with props `{ levels: ConversationLevelOption[]; value: ConversationLevelId; onChange: (level: ConversationLevelId) => void }`, matching `CorrectionModeFieldset`'s radio pattern and tokens (passes T031); ids use the prefix `conversation-level-`
- [ ] T039 [US1] Add `conversationLevel` / `setConversationLevel` (default `'natural'`) to `frontend/src/components/settings/useSettingsForm.ts`, loaded from `settings.conversation_level` and sent as `conversation_level` by `save()`; extend `frontend/src/components/settings/useSettingsForm.test.ts` first
- [ ] T040 [US1] Render `<ConversationLevelFieldset levels={useConversationLevels().levels} …/>` in `frontend/src/pages/Settings.tsx` directly before `CorrectionModeFieldset` (passes T032, T033); hide it while `levels` is empty. Run `npm run lint`, `npm test`, `npm run test:e2e`
- [ ] T041 [US1] **Run the benchmark (manual, needs Ollama with `llama3.1:8b`)**: from `backend/`, `backend/.venv/bin/pytest -m benchmark -s tests/integration/conversation_levels/test_level_benchmark.py`; mark tense compliance in the printed `level-review-sheet.md` (quickstart §3); record every printed figure and the marked tense results for the PR description. If SC-003 fails, the numbers in `LEVEL_CATALOG` may be tuned (spec Assumptions) without changing the level order or the kind of limit; update data-model.md §3 to match
- [ ] T042 [US1] **Only if T041 misses SC-001 or SC-002**: mark the feature experimental — add a `role='note'` warning to `frontend/src/components/settings/ConversationLevelFieldset.tsx` in the same style as the "Corrections are experimental" note (plain language: the local model does not always keep to the level; a larger model is on the roadmap), cover it in `ConversationLevelFieldset.test.tsx` and `frontend/e2e/settings.spec.ts`, and add the item to "Open items" in `docs/architecture.md`. The thresholds are **not** lowered. If T041 passes, mark this task done with "not needed" and the figures

**Checkpoint (MVP)**: Choosing a level on Settings changes how the partner speaks; Natural is
byte-identical to today; the benchmark figures are recorded.

---

## Phase 5: User Story 2 — Learner steps the level down (or up) mid-conversation (Priority: P2)

**Goal**: A compact **Level** control in the conversation header changes the same learner-wide
setting instantly; the partner's next reply follows the new level with no restart and no lost
history.

**Independent Test**: At Intermediate, exchange two turns, switch the header control to Beginner, send
a message: the next reply's request carries the Beginner block, the session was rebuilt from saved
history, earlier messages are unchanged, and Settings shows Beginner. Automated: T043–T047.

### Tests for User Story 2 (write first, see them fail)

- [ ] T043 [P] [US2] Write `backend/tests/integration/conversation_levels/test_level_change.py` with `tests/support/recording_session_provider.py` (contract §3, FR-008, SC-005): two turns at `intermediate`, then `PUT /api/settings {"conversation_level": "beginner"}`, then a third `/message`: the third `TurnRequest.standing_prompt` carries the Beginner block; the recording provider closed the first session and opened a new one (rebuild); the new session's history contains the earlier saved turns; the stored earlier messages are byte-identical to before the change; no restart or new conversation was created. Also: a conversation started at `natural`, level changed to `elementary`, reopened by a new `/message` → uses `elementary` (US2 AS3); and a reply whose stream is in progress when the level changes finishes with the level its request started with — have the recording session's reply callback perform the level-only PUT through storage mid-turn, then assert that turn's request carried the old block and the following turn carries the new one (spec edge case)
- [ ] T044 [P] [US2] Write `frontend/src/components/chat/useConversationLevelSetting.test.ts` for a new hook `useConversationLevelSetting()` returning `{ levels, level, isSaving, announcement, error, changeLevel }`: loads the stored level and the catalogue on mount; `changeLevel('beginner')` calls `updateSettings({ conversation_level: 'beginner' })` with **only** that key, sets `isSaving` while pending, then sets `announcement` to "Level set to Beginner. It applies from the next reply."; on a rejected save it reverts `level` to the previous value, clears `announcement`, and sets `error` to a plain-language message saying the level was not changed and to try again
- [ ] T045 [P] [US2] Write `frontend/src/components/chat/ConversationLevelControl.test.tsx` (contract §5): a native `<select>` with accessible name "Level"; options read "Beginner (A1)", "Elementary (A2)", "Intermediate (B1)", "Natural"; shows the stored level; disabled while saving; the announcement is rendered in an `aria-live='polite'` region; an error is rendered with `role='alert'`; takes no props
- [ ] T046 [P] [US2] Extend `frontend/src/pages/Chat.test.tsx`: the header contains the "Level" control showing the stored level, and the Send button remains the only primary-styled action (FR-010)
- [ ] T047 [P] [US2] Write `frontend/e2e/conversation-level.spec.ts` (contract §5): changing the header Level control sends `PUT /api/settings` whose body is exactly `{ conversation_level: 'beginner' }`; the "Level set to Beginner. It applies from the next reply." announcement appears; no navigation happens and the existing messages stay on screen; a mocked 500 on the PUT reverts the control to its previous value and shows an alert; with a stateful `/api/settings` route, a change in the chat header shows on the Settings screen and a Settings save shows in the chat header (US2 AS4); the level change takes at most two interactions (select, choose) (SC-006). Extend `frontend/e2e/chat.spec.ts`: the header shows the stored level and the existing open/send/stream flows still pass

### Implementation for User Story 2

- [ ] T048 [US2] Confirm T043 passes with **no new backend code** (research R2: the session fingerprint's `standing_prompt_digest` already triggers the rebuild). If it does not, stop and revisit research R2 rather than modifying `backend/app/services/conversation/`
- [ ] T049 [US2] Implement `frontend/src/components/chat/useConversationLevelSetting.ts` (passes T044), composing `useConversationLevels` from `frontend/src/components/settings/useConversationLevels.ts` plus `getSettings`/`updateSettings` from `frontend/src/services/api.ts`; each function ≤ 20 lines
- [ ] T050 [US2] Implement `frontend/src/components/chat/ConversationLevelControl.tsx` (passes T045): renders from `useConversationLevelSetting()` only; a visually secondary `<select>` — `--color-text-muted` text, no fill, `--radius` border using a border token, Plus Jakarta Sans inherited — with a hit area of at least 44 × 44 px; a visually hidden `aria-live='polite'` status region; a `role='alert'` error; not disabled by streaming (only by `isSaving`). Tokens only, no hex values
- [ ] T051 [US2] Add `<ConversationLevelControl />` to the `<header>` in `frontend/src/pages/Chat.tsx` beside the `<h1>` (one import, one element; plan.md Complexity Tracking row 1 — `Chat` gains no state, effects or handlers) (passes T046, T047). Check the header at 360 px wide: no overflow or wrapping of the title. Run `npm run lint`, `npm test`, `npm run test:e2e`

**Checkpoint**: Both controls read and write the same setting; a mid-conversation change applies from
the next reply with history intact.

---

## Phase 6: User Story 3 — Learner aids speak at the same level (Priority: P3)

**Goal**: Reply suggestions, alternative phrasings and the expression helper's target-language
phrase follow the level; grammar explanations, translations and word lookups do not change.

**Independent Test**: At Beginner, request suggestions, phrasings and a helper answer and check each
prompt carries the learner-text block; at Natural each prompt equals today's; a phrasing cached at
Natural is not served at Beginner. Automated: T052–T053.

### Tests for User Story 3 (write first, see them fail)

- [ ] T052 [P] [US3] Write `backend/tests/integration/conversation_levels/test_level_in_learner_aids.py` with a capturing fake `LLMProvider` (like the stub in `backend/tests/integration/routers/test_suggestions.py`) and `tests/support/recording_session_provider.py` for the helper (contract §4): at `natural`, the prompts for `POST /api/chat/{id}/suggestions` and `POST /api/learning/phrasing`, and the helper `standing_prompt` for `POST /api/chat/helper`, equal `build_suggestion_prompt(...)`, `build_phrasing_prompt(...)` and `build_helper_system_prompt(...)` exactly; at `beginner` each equals `with_learner_text_rules(<that prompt>, ConversationLevel.BEGINNER)` and contains no reply-length or question rule (FR-017, R5); changing the level between two helper questions rebuilds the helper session (R6); the prompts for `/api/learning/grammar`, `/api/learning/translate` and `/api/learning/word-lookup` are identical at `natural` and `beginner` (FR-018)
- [ ] T053 [P] [US3] Write phrasing-cache tests in `backend/tests/integration/conversation_levels/test_phrasing_cache_key.py` (data-model §6, research R7): a phrasing computed at `natural` is **not** served after switching to `beginner` (the fake LLM is called again, `cached: false`); a second request at `beginner` for the same message is served from the cache (`cached: true`); a `learning_tool_results` row inserted with the bare message content as `input_selection` (a pre-feature row) is still a cache hit at `natural`; the Beginner row's `input_selection` is `"[level:beginner] "` followed by the message content

### Implementation for User Story 3

- [ ] T054 [US3] In `backend/app/routers/chat.py`, refactor `get_suggestions` to ≤ 20 lines while applying the level (passes the suggestion part of T052): extract `_parse_numbered_suggestions(text: str, count: int) -> list[str]` (today's numbered/bulleted parsing and whole-text fallback, unchanged) and `_suggestion_prompt(conversation, messages, app_settings) -> str` returning `with_learner_text_rules(build_suggestion_prompt(...), ConversationLevel(app_settings.conversation_level))`. The existing `backend/tests/integration/routers/test_suggestions.py` must pass unchanged
- [ ] T055 [US3] In `backend/app/routers/chat.py`, add `app_settings: AppSettingsRecord = Depends(get_app_settings)` to `chat_helper` and extract `_helper_turn_request(req, stored, level) -> TurnRequest` whose `standing_prompt` is `with_learner_text_rules(build_helper_system_prompt(req.target_language, req.native_language), level)`, keeping `chat_helper` ≤ 20 lines (passes the helper part of T052). The existing `backend/tests/integration/routers/test_helper.py` must pass unchanged
- [ ] T056 [US3] In `backend/app/routers/learning.py`, add `_phrasing_cache_key(content: str, level: ConversationLevel) -> str` returning `content` unchanged at `NATURAL` and `f"[level:{level.value}] {content}"` otherwise (the `"[level:"` prefix as a named constant), build the phrasing prompt with `with_learner_text_rules(build_phrasing_prompt(...), level)`, and pass the key to `get_or_create_learning_result`; keep `alternative_phrasing` ≤ 20 lines (passes T053 and the phrasing part of T052). Grammar, translate and word-lookup are not touched. The existing `backend/tests/integration/routers/test_learning.py` must pass unchanged

**Checkpoint**: All three stories work independently; every target-language output follows the level.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T057 [P] Update `docs/architecture.md`: the `conversation_levels` domain module and its five public names; the level entering the standing prompt through composition (Natural byte-identical); level changes rebuilding sessions via the existing fingerprint (no engine change); the level-qualified phrasing cache key; and, if T042 applied, the experimental note under "Open items"
- [ ] T058 [P] Update `docs/design-system.md` with the secondary header `<select>` pattern used by `ConversationLevelControl` (muted text, no fill, 44 px hit area, tokens), if it is not already covered by an existing pattern
- [ ] T059 [P] Update `CLAUDE.md` (it already has uncommitted edits — merge, do not overwrite): add a **005-conversation-difficulty-level** entry to "Recent Changes" and a sentence on `backend/app/conversation_levels/` under "Domain modules" (or run `/speckit-agent-context-update` and review its diff)
- [ ] T060 Function-length audit: confirm every function added or modified by T010–T056 is ≤ 20 lines, including `get_suggestions`, `warm_session`, `chat_helper` and `alternative_phrasing` (plan.md Function-length plan); the only exceptions are `Chat` and the `Settings` layout recorded in plan.md Complexity Tracking
- [ ] T061 Run all quality gates (quickstart §1): from `backend/`, `backend/.venv/bin/pytest` (≥ 90% coverage, zero failures, zero skips), `backend/.venv/bin/ruff check .`, `backend/.venv/bin/black --check .`; from `frontend/`, `npm run lint`, `npm test`, `npm run test:e2e`
- [ ] T062 Manual accessibility check (Constitution quality gate, quickstart §5): keyboard-only, Tab to the header Level control, change it with the arrow keys and hear the announcement with a screen reader; Tab through the Settings level fieldset; check the control's and fieldset's contrast in light and dark themes
- [ ] T063 Run quickstart §2 (settings API smoke check with `curl` against `./run.sh`), §4 (manual walkthrough of US1–US3, FR-016, FR-018) and §5 (SC-006 stopwatch, SC-007 translation counts, SC-008 time-to-first-byte excluding the first turn after a change); record the results with the T041 benchmark figures in the PR description

---

## Dependencies & Execution Order

### Phase dependencies

| Phase | Depends on | Blocks |
|---|---|---|
| 1 Setup | — | everything |
| 2 Foundational | Setup | all stories |
| 3 Settings split | Foundational (T018 types) | US1's frontend tasks T032, T033, T038–T040 (not US1's backend) |
| 4 US1 (P1) | Foundational; Phase 3 for its frontend | — (MVP) |
| 5 US2 (P2) | Foundational; T020 hook | — |
| 6 US3 (P3) | Foundational | — |
| 7 Polish | the stories being shipped | — |

### Story independence

- **US1** stands alone. Its backend (T029, T030, T037) needs only Phase 2; its Settings fieldset
  needs Phase 3.
- **US2** needs only Phase 2 to build and test: `ConversationLevelControl` reads and writes the
  setting directly, and T043 passes on the Phase 2 storage plus the roleplay wiring. T043 does
  exercise T037's roleplay prompt, so in practice run US2 after US1's T037.
- **US3** needs only Phase 2; its tasks touch `get_suggestions`, `chat_helper` and `learning.py`,
  none of which US1 changes.

### Same-file sequencing (not parallel)

- `backend/app/routers/chat.py`: T037 → T054 → T055
- `frontend/src/components/settings/useSettingsForm.ts`: T022 → T039
- `frontend/src/pages/Settings.tsx`: T027 → T040 (→ T042 touches the fieldset, not the page)
- `backend/tests/unit/conversation_levels/test_catalog.py`: T004 → T012's added test
- `frontend/e2e/settings.spec.ts`: T033 → T042 (if needed)

### Within each story

Tests first and failing → implementation → the story's checkpoint. The benchmark (T041) runs at the
end of US1, before US2/US3 build further on the adherence assumption (plan.md suggested order).

---

## Parallel Opportunities

### Phase 2

```text
T004 test_catalog.py   T005 test_rules.py   T006 test_database.py   T007 test_sqlite_storage.py
T008 contract test     T009 test_settings.py   T017 api.test.ts   T019 fixtures.ts   T020 hook
```

### Phase 3

```text
After T022:  T023 CorrectionModeFieldset   T024 three fields   T025 ThemeField   T026 SettingsSaveBar
```

### User Story 1

```text
T029 test_level_in_prompts.py   T030 test_level_warm_session.py   T031 fieldset test
T032 Settings.test.tsx          T033 settings.spec.ts             T034 text_metrics   T035 evaluation_set
```

### User Story 2

```text
T043 test_level_change.py   T044 hook test   T045 control test   T046 Chat.test.tsx   T047 e2e specs
```

### User Story 3

```text
T052 test_level_in_learner_aids.py   T053 test_phrasing_cache_key.py
```

### Across stories (after Phase 2)

US1 backend (T029–T030, T037) and US3 (T052–T056) touch different functions but share
`chat.py`, so their **implementation** tasks are sequential while their **tests** can be written
together. US2's frontend (T044–T051) can run alongside US1's backend.

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 → Phase 2 (foundation, all prompts still Natural).
2. Phase 3 (Settings split), or drop it and record the Complexity Tracking row.
3. Phase 4 (US1) — then **stop and run the benchmark (T041)**. This is the feature's one real risk
   (`llama3.1:8b` adherence, as in 003). Decide experimental vs. not (T042) before going further.

### Incremental delivery

1. Foundation + US1 → Settings-driven levels (MVP).
2. + US2 → change the level from the conversation header without losing the conversation.
3. + US3 → suggestions, phrasings and helper at the same level.
4. Polish → docs, audits, quickstart, PR with benchmark figures.

---

## Notes

- No task edits `prompts/templates.py`, the conversation engine/pool, the LLM providers or
  `corrections/`. A task that finds it needs to must stop and revisit research R2/R10 first.
- Commit after each task or logical group, with the Red commit (failing test) before the Green one
  where practical.
