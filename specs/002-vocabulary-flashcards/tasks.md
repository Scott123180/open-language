# Tasks: Vocabulary Flashcards

**Input**: Design documents from `/specs/002-vocabulary-flashcards/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/api.md ✅

**Tests**: TDD is mandatory per the constitution (Principle III). Every test task MUST be written and confirmed to FAIL before the implementation task it covers is started. Red → Green → Refactor.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Can run in parallel (different files, no shared dependencies in-flight)
- **[Story]**: Which user story this task belongs to (US1–US9)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the scaffolding that all subsequent phases depend on.

- [X] T001 Create `backend/app/flashcards/` package skeleton: `__init__.py`, empty `router.py`, empty `models.py`, empty `schemas.py`, `services/__init__.py`, empty `services/storage.py`, `services/classification.py`, `services/deck_generation.py`, `services/session.py`, `services/analytics.py`, `services/llm_cache.py`, `services/srs.py`
- [X] T002 [P] Create backend test skeleton: `backend/tests/unit/flashcards/__init__.py`, `backend/tests/integration/flashcards/__init__.py`, `backend/tests/integration/flashcards/conftest.py` (shared test client + in-memory SQLite fixture)
- [X] T003 [P] Install Recharts in frontend — run `npm install recharts` from `frontend/` and verify `frontend/package.json` lists `"recharts"` in dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data layer and wiring that ALL user stories depend on. No story work begins until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Write failing contract test for `FlashcardStorageProvider` ABC covering all required method signatures — `backend/tests/contract/service_interfaces/test_flashcard_storage_provider.py`
- [X] T005 Define `FlashcardStorageProvider(ABC)` with all abstract method stubs matching data-model.md (word CRUD, deck CRUD, session lifecycle, card results, rating history, LLM cache, SRS schedule, analytics snapshots) — `backend/app/flashcards/services/storage.py`
- [X] T006 [P] Create all SQLAlchemy ORM models: `Deck`, `DeckCard`, `PracticeSession`, `CardResult`, `FlashcardRatingHistory`, `WordLlmCache`, `SpacedRepetitionSchedule`, `SessionClassificationSnapshot` — all in `backend/app/flashcards/models.py` with foreign keys, indexes, and unique constraints per data-model.md
- [X] T007 [P] Extend `backend/app/models/vocabulary_item.py`: add `WordClassification` enum (`not_practiced`, `difficult`, `almost_learned`, `learned`) and three new `Mapped` columns: `classification`, `manual_override`, `tts_cache_path`
- [X] T008 Extend `backend/app/database.py`: import `backend/app/flashcards/models` in `init_db()` (so `create_all()` creates new tables); add `_add_column_if_missing` calls for `vocabulary_items.classification`, `vocabulary_items.manual_override`, `vocabulary_items.tts_cache_path`
- [X] T009 Implement `SQLiteFlashcardStorageProvider` concrete class implementing `FlashcardStorageProvider`; make T004 contract tests pass — `backend/app/flashcards/services/sqlite_storage.py`
- [X] T010 Add `get_flashcard_storage()` dependency factory to `backend/app/services/factory.py`; create `backend/app/flashcards/router.py` with prefix `/flashcards` and include it in `backend/app/main.py`
- [X] T011 [P] Create base Pydantic schemas in `backend/app/flashcards/schemas.py`: `WordClassification` enum, `PracticeMode` enum, `GenerationAlgorithm` enum, `Rating` enum, and shared `ErrorResponse` shape
- [X] T012 [P] Add `/flashcards`, `/flashcards/decks`, `/flashcards/practice/:sessionId`, `/flashcards/summary/:sessionId`, `/flashcards/analytics` routes to `frontend/src/App.tsx`; create `frontend/src/services/flashcardsApi.ts` with base `apiFetch` wrapper and TypeScript interface stubs for all API response shapes from `contracts/api.md`

**Checkpoint**: `backend/.venv/bin/pytest tests/contract/` passes; app starts without error; frontend routes resolve.

---

## Phase 3: User Story 1 — Word Library Management (Priority: P1) 🎯 MVP

**Goal**: Users can view, filter, search, classify, and delete their saved vocabulary words through a dedicated Flashcards section.

**Independent Test**: Add words from chat → open `/flashcards` → verify word list displays, filters work, classification updates, deletion removes the word.

### Tests for User Story 1 (Write FIRST — must FAIL before implementation)

- [X] T013 [P] [US1] Unit tests for word list filtering logic (classification multi-select, date range, search) covering all filter combinations — `backend/tests/unit/flashcards/test_word_library.py`
- [X] T014 [P] [US1] Integration tests for `GET /api/flashcards/words` (all filters), `PATCH /api/flashcards/words/{id}/classification`, `DELETE /api/flashcards/words/{id}` — `backend/tests/integration/flashcards/test_word_library_endpoints.py`
- [X] T015 [P] [US1] Unit tests for `WordListItem` component: renders word, translation, classification badge, delete button; tests for `WordFilterBar` component: emits filter change events — `frontend/src/components/flashcards/WordListItem.test.tsx` and `frontend/src/components/flashcards/WordFilterBar.test.tsx`

### Implementation for User Story 1

- [X] T016 [US1] Implement `list_words_filtered()` method on `SQLiteFlashcardStorageProvider` supporting classification array filter, date range filter, and text search — `backend/app/flashcards/services/sqlite_storage.py`
- [X] T017 [US1] Implement `GET /api/flashcards/words`, `PATCH /api/flashcards/words/{id}/classification`, and `DELETE /api/flashcards/words/{id}` endpoints; add `WordListItem` and `WordFilterParams` Pydantic schemas — `backend/app/flashcards/router.py` and `backend/app/flashcards/schemas.py`
- [X] T018 [US1] Update `backend/app/routers/vocabulary.py` `save_vocabulary_item` to implement merge-on-duplicate behavior (update `saved_at` + `source_conversation_id`; preserve classification/history; return `already_saved: true` flag in response)
- [X] T019 [P] [US1] Create `frontend/src/components/flashcards/WordListItem.tsx`: word row displaying word, translation, classification badge (color-coded), date added, delete button with confirmation, classify dropdown
- [X] T020 [P] [US1] Create `frontend/src/components/flashcards/WordFilterBar.tsx`: multi-select classification chips, date-range presets (7d/30d/custom), free-text search input, Select All / Deselect All controls
- [X] T021 [US1] Create `frontend/src/pages/Flashcards.tsx`: word list page using TanStack Query `useQuery` for `GET /api/flashcards/words`; integrates `WordListItem` and `WordFilterBar`; primary action = "Generate Deck" button (disabled when 0 words)
- [X] T022 [US1] Add Flashcards navigation card to `frontend/src/pages/Home.tsx` (icon, label "Flashcards", link to `/flashcards`)
- [X] T023 [US1] Add `flashcardsApi.ts` implementations for word library endpoints: `fetchWords(filters)`, `updateClassification(id, classification)`, `deleteWord(id)` with proper TypeScript types
- [X] T024 [US1] Write E2E tests for word list: display, filter by classification, search, manual classify, delete — `frontend/e2e/flashcards.spec.ts` (all API calls intercepted via `page.route()`)

**Checkpoint**: Navigate to `/flashcards` → words list correctly → filters work → classification updates → delete works → `npm run test:e2e` passes for `flashcards.spec.ts`.

---

## Phase 4: User Story 2 — Basic Flashcard Practice / Recall Mode (Priority: P1) 🎯 MVP

**Goal**: Users can generate a Recall-mode deck, practice all cards one at a time (flip, self-grade), and reach a session summary screen with score breakdown.

**Independent Test**: Save words → generate Recall deck → complete all cards with ratings → verify summary screen shows correct counts.

### Tests for User Story 2 (Write FIRST — must FAIL before implementation)

- [X] T025 [P] [US2] Unit tests for `ClassificationEngine.recalculate()` covering all 5 transition rules with priority ordering — `backend/tests/unit/flashcards/test_classification_engine.py`
- [X] T026 [P] [US2] Unit tests for `DeckGenerationService` basic word selection (random selection from pool, exact deck size, pool-smaller-than-size fallback) — `backend/tests/unit/flashcards/test_deck_generation.py`
- [X] T027 [P] [US2] Integration tests for `POST /api/flashcards/decks`, `POST /api/flashcards/sessions`, `POST /api/flashcards/sessions/{id}/cards/{pos}`, `POST /api/flashcards/sessions/{id}/end`, `GET /api/flashcards/sessions/{id}/summary`, `GET /api/flashcards/tts/{vocab_item_id}` — `backend/tests/integration/flashcards/test_session_endpoints.py`
- [X] T028 [P] [US2] Unit tests for `CardPrompt` (Recall mode: shows target-language word), `SelfAssessmentBar` (three buttons, emits correct rating), `AudioControls` (listen triggers playback, slow speed sets rate to 0.6) — `frontend/src/components/flashcards/CardPrompt.test.tsx`, `SelfAssessmentBar.test.tsx`, `AudioControls.test.tsx`

### Implementation for User Story 2

- [X] T029 [US2] Implement `ClassificationEngine` as a pure function service: `recalculate(ratings: list[Rating]) -> WordClassification` with priority-ordered rules from FR-009 — `backend/app/flashcards/services/classification.py`
- [X] T030 [US2] Implement `DeckGenerationService` with basic `select_words(pool, size, algorithm)` logic (Recall mode; default algorithm = random selection; fallback when pool < size; per-tier randomization) — `backend/app/flashcards/services/deck_generation.py`
- [X] T031 [US2] Implement `SessionService`: `create_session()`, `record_card_result()` (appends `CardResult` + `FlashcardRatingHistory`), `end_session()` (marks complete/incomplete, triggers `ClassificationEngine.recalculate()` for all rated words, updates `vocabulary_items.classification`) — `backend/app/flashcards/services/session.py`
- [X] T032 [US2] Add `GET /api/flashcards/tts/{vocabulary_item_id}` endpoint: reads word text from `vocabulary_items`, calls `TTSProvider.synthesize()`, caches WAV at `~/.open-language/tts_cache/vocab_{id}.wav`, returns `FileResponse` — `backend/app/flashcards/router.py`
- [X] T033 [US2] Implement deck and session endpoints in `backend/app/flashcards/router.py`: `POST /decks`, `GET /decks`, `GET /decks/{id}`, `POST /sessions`, `POST /sessions/{id}/cards/{pos}`, `POST /sessions/{id}/end`, `GET /sessions/{id}/summary`; add all required Pydantic schemas to `backend/app/flashcards/schemas.py`
- [X] T034 [P] [US2] Create `frontend/src/components/flashcards/CardPrompt.tsx`: mode-aware card front; for Recall mode renders target-language word as large text
- [X] T035 [P] [US2] Create `frontend/src/components/flashcards/SelfAssessmentBar.tsx`: three buttons (Didn't Know / Guessed Correctly / Knew It) with distinct visual styles; only visible after card is flipped; emits `onRate(rating)` callback
- [X] T036 [P] [US2] Create `frontend/src/components/flashcards/AudioControls.tsx`: "Listen" button (calls TTS endpoint; uses existing `AudioPlayer` with `playbackRate={1.0}`); "Slow Speed" button (replays at `playbackRate={0.6}` via existing `AudioPlayer.playbackRate` prop)
- [X] T037 [US2] Create `frontend/src/pages/FlashcardDecks.tsx`: My Decks list using TanStack Query; shows deck name, card count, mode, algorithm, creation date, last practiced, last accuracy; "Start Practice" and "Delete" actions per deck
- [X] T038 [US2] Create `frontend/src/components/flashcards/DeckConfigPanel.tsx`: deck size presets (10/20/40) + custom input; word source (all/filtered/selected); practice mode (Recall only for now); "Generate" button with loading state; shows adjusted-size notification when pool < requested size
- [X] T039 [US2] Create `frontend/src/pages/FlashcardPractice.tsx`: manages active session with `useReducer` for card state (current position, accumulated ratings, timer); renders `CardPrompt`, `AudioControls`, flip button, `SelfAssessmentBar`; calls `POST /sessions/{id}/cards/{pos}` on each rating; navigates to summary on session end
- [X] T040 [US2] Create `frontend/src/pages/FlashcardSummary.tsx` (basic): shows Knew It / Guessed / Didn't Know counts and percentages, cards reviewed vs total, session duration; "Practice Again" and "Back to Decks" actions; uses `GET /sessions/{id}/summary`
- [X] T041 [US2] Add `flashcardsApi.ts` implementations for deck and session endpoints: `createDeck()`, `listDecks()`, `getDeck()`, `deleteDeck()`, `startSession()`, `recordCardResult()`, `endSession()`, `getSessionSummary()`, `getVocabTtsUrl()`
- [X] T042 [US2] Write E2E tests for full Recall mode session: generate deck → practice all cards → self-grade → verify summary counts — `frontend/e2e/flashcard-practice.spec.ts` (all API calls intercepted)

**Checkpoint**: Full Recall mode session works end-to-end; summary screen shows correct data; `npm run test:e2e` passes for `flashcard-practice.spec.ts` (Recall section).

---

## Phase 5: User Story 3 — Deck Generation with Smart Algorithms (Priority: P2)

**Goal**: Users can choose from 4 generation algorithms (Not Practiced, Unknown/Difficult, Previously Guessed, Mixed Review) when creating a deck; words are selected according to the algorithm's priority order and fallback chain.

**Independent Test**: Seed words in multiple classification states → generate decks with each algorithm → verify word composition matches expected priority order.

### Tests for User Story 3 (Write FIRST — must FAIL before implementation)

- [X] T043 [P] [US3] Unit tests for all 4 `AlgorithmStrategy` implementations: correct priority ordering, correct fallback chaining, correct Mixed Review ratios (40/30/20/10%), per-tier randomization — `backend/tests/unit/flashcards/test_deck_generation.py` (extend file)
- [X] T044 [P] [US3] Integration tests for deck generation with each algorithm; verify adjusted-size notification when pool < requested size — `backend/tests/integration/flashcards/test_deck_endpoints.py`

### Implementation for User Story 3

- [X] T045 [US3] Implement 4 `AlgorithmStrategy` classes in `backend/app/flashcards/services/deck_generation.py`: `NotPracticedStrategy`, `DifficultStrategy`, `PreviouslyGuessedStrategy`, `MixedReviewStrategy` — each implements `select(pool, size) -> list`; register all in `DeckGenerationService` strategy registry
- [X] T046 [US3] Extend `DeckConfigPanel.tsx` with algorithm selection dropdown: 4 options with descriptions; default = Mixed Review — `frontend/src/components/flashcards/DeckConfigPanel.tsx`
- [X] T047 [US3] Extend E2E tests in `frontend/e2e/flashcards.spec.ts` with deck configuration panel tests: algorithm selection, size adjustment notification

**Checkpoint**: Each algorithm produces correctly ordered decks; unit tests pass; E2E deck generation panel works.

---

## Phase 6: User Story 4 — Additional Practice Modes (Priority: P2)

**Goal**: Users can practice in Listen mode (audio auto-plays, no text), Produce mode (native-language prompt, user supplies target), and Fill-in-the-Blank mode (LLM-generated gapped sentences); each mode is selectable at deck creation.

**Independent Test**: Generate a deck in each mode → verify correct prompt type is displayed → verify answer reveal is mode-appropriate.

### Tests for User Story 4 (Write FIRST — must FAIL before implementation)

- [X] T048 [P] [US4] Unit tests for `LlmCacheService.get_fill_blank_sentence()`: returns cached sentence on second call; generates new sentence for new word; LLM error triggers graceful fallback — `backend/tests/unit/flashcards/test_llm_cache.py`
- [X] T049 [P] [US4] Integration tests for deck creation in Listen, Produce, Fill-in-the-Blank modes; verify `fill_blank_sentence` populated in DeckCard for FitB decks — `backend/tests/integration/flashcards/test_deck_endpoints.py` (extend)
- [X] T050 [P] [US4] Unit tests for `CardPrompt` in Listen mode (no text, audio auto-plays), Produce mode (native word shown), FitB mode (sentence with blank shown) — `frontend/src/components/flashcards/CardPrompt.test.tsx` (extend)
- [X] T051 [P] [US4] Unit tests for `HelpOverlay` component: correct help text per mode — `frontend/src/components/flashcards/HelpOverlay.test.tsx`

### Implementation for User Story 4

- [X] T052 [US4] Implement `LlmCacheService.generate_fill_blank_sentence(word, context_lang)`: calls LLM to generate natural sentence with word removed; stores in `word_llm_cache` table; returns cached result on subsequent calls; fallback to `None` on LLM error — `backend/app/flashcards/services/llm_cache.py`
- [X] T053 [US4] Extend deck creation (`POST /api/flashcards/decks`) to call `LlmCacheService.generate_fill_blank_sentence()` for each DeckCard when mode is `fill_blank`; store sentence in `DeckCard.fill_blank_sentence` — `backend/app/flashcards/router.py` and `backend/app/flashcards/services/session.py`
- [X] T054 [US4] Extend `CardPrompt.tsx` with mode-specific rendering: Listen (hidden text, auto-play audio via `AudioControls` on mount), Produce (native-language word as prompt), Fill-in-the-Blank (sentence with `___` replacing the target word) — `frontend/src/components/flashcards/CardPrompt.tsx`
- [X] T055 [US4] Create `frontend/src/components/flashcards/HelpOverlay.tsx`: modal overlay with mode-specific instructions; triggered by `?` help button on each card
- [X] T056 [US4] Extend `DeckConfigPanel.tsx` with all 4 mode options; explain each mode briefly — `frontend/src/components/flashcards/DeckConfigPanel.tsx`
- [X] T057 [US4] Extend E2E tests in `frontend/e2e/flashcard-practice.spec.ts` with Listen, Produce, and FitB mode sections

**Checkpoint**: Each mode shows correct prompt type; FitB sentences are present in deck cards; E2E passes for all 4 modes.

---

## Phase 7: User Story 5 — Classification & Spaced Repetition (Priority: P2)

**Goal**: Word classifications update automatically after each session (complete or early exit) using priority-ordered rules; "Learned" words are scheduled for adaptive spaced-repetition resurfacing.

**Independent Test**: Complete sessions with controlled ratings → verify classification state transitions match FR-009 priority rules; verify SRS-eligible words appear in subsequent decks after their due date.

### Tests for User Story 5 (Write FIRST — must FAIL before implementation)

- [X] T058 [P] [US5] Unit tests for `ClassificationEngine` priority conflict scenarios (3-consecutive Knew overrides 2 Didn't Know), regression from Learned to Difficult, Almost Learned threshold edge cases — `backend/tests/unit/flashcards/test_classification_engine.py` (extend)
- [X] T059 [P] [US5] Unit tests for `SpacedRepetitionService`: stage advances on `knew_it`, holds on `guessed`, resets to stage 1 on `didnt_know`; `next_due_at` computed correctly per stage — `backend/tests/unit/flashcards/test_srs_service.py`
- [X] T060 [P] [US5] Integration tests for SRS eligibility: words past due date are included in deck generation; words not yet due are excluded — `backend/tests/integration/flashcards/test_deck_endpoints.py` (extend)

### Implementation for User Story 5

- [X] T061 [US5] Implement `SpacedRepetitionService`: `update_after_rating(vocab_item_id, rating, db)` — looks up or creates `SpacedRepetitionSchedule` record; advances/holds/resets interval stage; writes new `next_due_at` — `backend/app/flashcards/services/srs.py`
- [X] T062 [US5] Integrate `SpacedRepetitionService` into `SessionService.end_session()`: after `ClassificationEngine.recalculate()` for each word, call `SpacedRepetitionService.update_after_rating()` for any word classified as `learned` — `backend/app/flashcards/services/session.py`
- [X] T063 [US5] Extend `DeckGenerationService` word pool query to include Learned words whose `spaced_repetition_schedule.next_due_at <= now()`; exclude Learned words not yet due — `backend/app/flashcards/services/deck_generation.py`
- [X] T064 [US5] Clear `vocabulary_items.manual_override` flag to `False` in `SessionService` for each word that appears in a completed or partially-completed session — `backend/app/flashcards/services/session.py`

**Checkpoint**: Classification transitions verified by unit tests; SRS-due Learned words appear in new decks; manual override clears after session.

---

## Phase 8: User Story 6 — Contextual Word Information (Priority: P2)

**Goal**: After flipping a card, users can tap "All Meanings", "Usage & Sentences", "Common Phrases", or "Similar Words" to get LLM-generated contextual information; results are cached per word and invalidated on language config change.

**Independent Test**: Flip a card → tap "All Meanings" → verify LLM content displayed; tap again → verify cached (no new LLM call); change language → verify cache invalidated.

### Tests for User Story 6 (Write FIRST — must FAIL before implementation)

- [X] T065 [P] [US6] Unit tests for `LlmCacheService.get_or_generate()`: cache hit returns stored content; cache miss triggers LLM call and stores result; language change invalidates cache — `backend/tests/unit/flashcards/test_llm_cache.py` (extend)
- [X] T066 [P] [US6] Integration tests for `GET /api/flashcards/words/{id}/info/{cache_type}`: first call triggers LLM; second call returns cached; LLM error returns 503 — `backend/tests/integration/flashcards/test_word_library_endpoints.py` (extend)
- [X] T067 [P] [US6] Unit tests for `CardAnswer` component: info buttons hidden before flip; all 4 buttons visible after flip; loading state during fetch; content rendered on success — `frontend/src/components/flashcards/CardAnswer.test.tsx`

### Implementation for User Story 6

- [X] T068 [US6] Implement `LlmCacheService.get_or_generate(vocab_item_id, cache_type, language, llm_provider)`: checks `word_llm_cache` for existing entry; if missing, calls LLM with type-appropriate prompt; persists and returns content — `backend/app/flashcards/services/llm_cache.py`
- [X] T069 [US6] Add `GET /api/flashcards/words/{id}/info/{cache_type}` endpoint to `backend/app/flashcards/router.py`; add `LlmCacheResponse` schema; return 503 with retry-friendly message on LLM failure
- [X] T070 [US6] Add language-change cache invalidation: on settings update (`PUT /settings`), delete all `word_llm_cache` rows where `language` matches the old target language — `backend/app/routers/settings.py` (extend)
- [X] T071 [US6] Create `frontend/src/components/flashcards/CardAnswer.tsx`: shown after card flip; displays translation/correct answer; renders 4 contextual info buttons (All Meanings, Usage & Sentences, Common Phrases, Similar Words); each button uses TanStack Query `useQuery` with `enabled: false` on first render, fetches on click; shows spinner during fetch; renders content inline
- [X] T072 [US6] Add `fetchWordInfo(id, cacheType)` to `frontend/src/services/flashcardsApi.ts`; integrate `CardAnswer` into `FlashcardPractice.tsx` (shown when card is flipped)

**Checkpoint**: Contextual info buttons appear after flip; LLM content displayed; second tap is instant (cached); 503 shows retry prompt without breaking session.

---

## Phase 9: User Story 7 — Session Summary & Post-Session Actions (Priority: P2)

**Goal**: After every session (complete or early exit), users see a rich summary screen with score visualization, streak count, words needing work, an LLM encouragement message, and actions to practice again, drill missed words, or navigate back.

**Independent Test**: Complete a session → verify summary shows correct counts, streak, and word list → tap "Practice Missed Words" → verify new mini-deck contains only Didn't Know words.

### Tests for User Story 7 (Write FIRST — must FAIL before implementation)

- [X] T073 [P] [US7] Integration tests for `GET /api/flashcards/sessions/{id}/summary` (words needing work list), `GET /api/flashcards/sessions/{id}/encouragement` (LLM response), `POST /api/flashcards/sessions/{id}/missed-deck` (new deck with Didn't Know words only) — `backend/tests/integration/flashcards/test_session_endpoints.py` (extend)
- [X] T074 [P] [US7] Unit tests for `FlashcardSummary` component: score donut chart shows correct proportions; words-needing-work list rendered; all 4 post-session action buttons present and link correctly — `frontend/src/pages/FlashcardSummary.test.tsx`

### Implementation for User Story 7

- [X] T075 [US7] Implement `GET /api/flashcards/sessions/{id}/summary` to return full summary including `words_needing_work` list (words rated `didnt_know` or `guessed`) — `backend/app/flashcards/router.py`
- [X] T076 [US7] Implement `GET /api/flashcards/sessions/{id}/encouragement` endpoint: calls LLM with session score context; returns generated message; returns 503 fallback message on LLM failure — `backend/app/flashcards/router.py`
- [X] T077 [US7] Implement `POST /api/flashcards/sessions/{id}/missed-deck`: queries `card_results` for `didnt_know` ratings in this session; creates a new Deck containing only those words; returns `DeckDetail` — `backend/app/flashcards/router.py`
- [X] T078 [US7] Extend `frontend/src/pages/FlashcardSummary.tsx`: score donut/bar chart (Recharts `PieChart` with `innerRadius` for donut); streak indicator; words needing work list; LLM encouragement message (fetched via `GET /encouragement`); 4 action buttons: Practice Again, Practice Missed Words, Back to Decks, Back to Word List
- [X] T079 [US7] Add `getEncouragement(sessionId)`, `createMissedDeck(sessionId)` to `frontend/src/services/flashcardsApi.ts`; wire "Practice Missed Words" button to create missed deck then navigate to practice
- [X] T080 [US7] Extend E2E tests in `frontend/e2e/flashcard-practice.spec.ts` with summary screen assertions: correct counts displayed, "Practice Missed Words" generates new deck, "Practice Again" restarts same deck

**Checkpoint**: Summary screen renders correctly; encouragement message loads; missed-deck mini-practice works end-to-end.

---

## Phase 10: User Story 8 — Deck Refresh (Priority: P3)

**Goal**: Users can refresh an existing deck to replace Learned words with new eligible words, preserving the original deck name and configuration.

**Independent Test**: Create a deck with some words now Learned → tap "Refresh Deck" → verify Learned words replaced by Not Practiced or Difficult words; deck name and mode unchanged.

### Tests for User Story 8 (Write FIRST — must FAIL before implementation)

- [X] T081 [P] [US8] Integration tests for `POST /api/flashcards/decks/{id}/refresh`: Learned words replaced; deck size preserved; name/mode/algorithm unchanged; returns updated DeckDetail — `backend/tests/integration/flashcards/test_deck_endpoints.py` (extend)

### Implementation for User Story 8

- [X] T082 [US8] Implement `POST /api/flashcards/decks/{id}/refresh` endpoint: fetches current deck config; identifies Learned DeckCards (via vocabulary_item classification); replaces them by running the original algorithm on the remaining eligible pool; returns updated DeckDetail — `backend/app/flashcards/router.py`
- [X] T083 [US8] Add "Refresh Deck" button to `frontend/src/pages/FlashcardDecks.tsx` per deck row; calls `POST /decks/{id}/refresh` via TanStack Query `useMutation`; invalidates deck query on success; shows confirmation before refreshing
- [X] T084 [US8] Add `refreshDeck(id)` to `frontend/src/services/flashcardsApi.ts`

**Checkpoint**: Refresh replaces Learned words while preserving deck config; UI updates immediately after refresh.

---

## Phase 11: User Story 9 — Analytics Dashboard (Priority: P3)

**Goal**: Users can view a comprehensive analytics dashboard showing at-a-glance stats, time-series charts (accuracy trend, daily activity, classification over time), vocabulary breakdown (donut chart, hardest words, recently learned), and mode performance comparison.

**Independent Test**: Seed session history with known data → open Analytics Dashboard → verify each chart and stat card shows correct aggregated values.

### Tests for User Story 9 (Write FIRST — must FAIL before implementation)

- [X] T085 [P] [US9] Unit tests for `AnalyticsService`: accuracy trend query, daily activity query, classification-now query, hardest-words query, mode-performance query, streak calculation — `backend/tests/unit/flashcards/test_analytics_service.py`
- [X] T086 [P] [US9] Integration tests for `GET /api/flashcards/analytics` with 7-day, 30-day, and all-time range parameters; verify response structure matches contract — `backend/tests/integration/flashcards/test_analytics_endpoints.py`
- [X] T087 [P] [US9] Unit tests for `AnalyticsCharts` component: renders `<ResponsiveContainer>` wrappers; passes correct `dataKey` props; shows empty-state when no data — `frontend/src/components/flashcards/AnalyticsCharts.test.tsx`

### Implementation for User Story 9

- [X] T088 [US9] Add `SessionClassificationSnapshot` creation to `SessionService.end_session()`: after recalculation, count words per classification and write one snapshot row — `backend/app/flashcards/services/session.py`
- [X] T089 [US9] Implement `AnalyticsService` with 6 query methods: `accuracy_trend(cutoff)`, `daily_activity(cutoff)`, `classification_over_time(cutoff)` (from `session_classification_snapshot`), `classification_now()`, `hardest_words(limit)`, `mode_performance()`, plus `streak()` helper — `backend/app/flashcards/services/analytics.py`
- [X] T090 [US9] Add `GET /api/flashcards/analytics` endpoint with `range` query param (`7d` | `30d` | `all`); wire to `AnalyticsService`; return full `AnalyticsSummary` schema — `backend/app/flashcards/router.py` and `backend/app/flashcards/schemas.py`
- [X] T091 [P] [US9] Create `frontend/src/components/flashcards/AnalyticsCharts.tsx`: exports 5 Recharts chart components — `AccuracyTrendChart` (LineChart), `DailyActivityChart` (BarChart), `ClassificationOverTimeChart` (AreaChart stacked), `ClassificationDonut` (PieChart innerRadius), `ModePerformanceChart` (BarChart grouped); each wrapped in `<ResponsiveContainer>`; each shows empty-state message when data is empty
- [X] T092 [US9] Create `frontend/src/pages/FlashcardAnalytics.tsx`: at-a-glance stat cards row; time-range toggle (7d/30d/all); renders all 5 charts from `AnalyticsCharts`; hardest-words table (tappable rows → navigate to word in list); recently-learned list; uses TanStack Query `useQuery` for `GET /api/flashcards/analytics`
- [X] T093 [US9] Add Analytics Dashboard navigation entry to `frontend/src/pages/Flashcards.tsx` (e.g., header link or tab); add `fetchAnalytics(range)` to `frontend/src/services/flashcardsApi.ts`
- [X] T094 [US9] Write E2E tests for analytics dashboard: stat cards display, chart elements render, time-range toggle changes data, hardest-word tap navigates to word list — `frontend/e2e/flashcard-analytics.spec.ts`

**Checkpoint**: Analytics dashboard renders all charts and stats; time-range toggle works; hardest-word navigation works; `npm run test:e2e` passes for `flashcard-analytics.spec.ts`.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Accessibility audit, linter compliance, test coverage validation, and documentation verification across all stories.

- [X] T095 Run manual accessibility audit on all new screens (Flashcards, FlashcardDecks, FlashcardPractice, FlashcardSummary, FlashcardAnalytics): verify contrast ratios ≥ 4.5:1, touch targets ≥ 44×44px, all interactive elements have `aria-label` — document results in `specs/002-vocabulary-flashcards/checklists/requirements.md`
- [X] T096 [P] Run `backend/.venv/bin/ruff check backend/app/flashcards/ backend/tests/` and `backend/.venv/bin/black --check backend/app/flashcards/` — fix all reported issues until zero warnings
- [X] T097 [P] Run `cd frontend && npm run lint` — fix all ESLint errors in new files; run `npm run format` to apply Prettier
- [X] T098 Run `backend/.venv/bin/pytest --cov=app --cov-fail-under=90` — confirm coverage ≥ 90%; add targeted tests for any uncovered branches
- [X] T099 [P] Run `npm run test:e2e` — confirm all three E2E spec files pass with zero failures: `flashcards.spec.ts`, `flashcard-practice.spec.ts`, `flashcard-analytics.spec.ts`
- [X] T100 Verify `quickstart.md` is accurate: start app, navigate to `/flashcards`, confirm all major flows work end-to-end with a freshly-seeded word library

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1, US2 (Phases 3–4)**: Both P1, both depend on Foundational only — can run in parallel with separate developers
- **US3 (Phase 5)**: Depends on US2 (extends deck generation)
- **US4 (Phase 6)**: Depends on US2 (extends practice mode rendering) and US3 (mode selection at deck config)
- **US5 (Phase 7)**: Depends on US2 (SessionService must exist) — can start in parallel with US3/US4
- **US6 (Phase 8)**: Depends on US2 (CardAnswer shown post-flip) — can start in parallel with US3/US4/US5
- **US7 (Phase 9)**: Depends on US2 (session summary extends FlashcardSummary)
- **US8 (Phase 10)**: Depends on US3 (deck generation algorithms needed for refresh)
- **US9 (Phase 11)**: Depends on US2 (sessions must exist) + US5 (classification snapshots needed)
- **Polish (Phase 12)**: Depends on all user stories complete

### User Story Dependencies

```
US1 (P1) ─────────────────────────────────────────┐
US2 (P1) ─── US3 (P2) ─── US4 (P2)               │
         └── US5 (P2)                              ├─ Polish
         └── US6 (P2)                              │
         └── US7 (P2)                              │
         └─────────── US8 (P3) ─── US9 (P3) ──────┘
```

### Within Each User Story

1. **Test tasks** (marked [P]) → MUST be written FIRST; run them and confirm they FAIL
2. **Models / service logic** → implement after tests fail
3. **Endpoints** → implement after service layer is tested
4. **Frontend components** → implement after backend endpoints are available (or mock in tests)
5. **E2E tests** → written alongside frontend; all `page.route()` mocks required

---

## Parallel Opportunities

### Phase 1
```
T001 → T002 [P] + T003 [P] run simultaneously
```

### Phase 2
```
T004 → T005 → T006 [P] + T007 [P] run simultaneously → T008 → T009 → T010
T011 [P] + T012 [P] run simultaneously alongside T004–T010
```

### US1 + US2 in parallel (separate developers)
```
Developer A: T013 → T016 → T017 → T018 → T019 [P] + T020 [P] → T021 → T022 → T023 → T024
Developer B: T025 + T026 + T027 + T028 → T029 → T030 → T031 → T032 → T033 → T034 [P] + T035 [P] + T036 [P] → T037 → T038 → T039 → T040 → T041 → T042
```

### US5 + US6 in parallel (after US2)
```
Developer A: T058 + T059 + T060 → T061 → T062 → T063 → T064
Developer B: T065 + T066 + T067 → T068 → T069 → T070 → T071 → T072
```

---

## Implementation Strategy

### MVP Scope (User Stories 1 + 2 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: US1 — Word Library Management
4. Complete Phase 4: US2 — Basic Flashcard Practice (Recall)
5. **STOP and VALIDATE**: Full Recall-mode session works; `npm run test:e2e` passes
6. Demo-able: users can save words, browse library, generate a Recall deck, practice, and see a summary

### Incremental Delivery

| Milestone | Phases | Deliverable |
|---|---|---|
| MVP | 1–4 | Word library + Recall mode |
| Adaptive Decks | + Phase 5 (US3) | 4 smart algorithms |
| Full Practice | + Phase 6 (US4) | Listen, Produce, FitB modes |
| Smart Learning | + Phase 7 (US5) | Auto-classification + SRS |
| Deep Vocabulary | + Phase 8 (US6) | Contextual LLM info |
| Complete Loop | + Phase 9 (US7) | Rich summary + Practice Missed Words |
| Maintenance | + Phase 10 (US8) | Deck refresh |
| Insights | + Phase 11 (US9) | Analytics dashboard |

---

## Notes

- All test tasks marked [P] within a story can launch simultaneously before any implementation task in that story
- Every `[P]` task touches different files — no write conflicts when parallelized
- Commit after each task or logical group (test + implementation pairs)
- `npm run test:e2e` MUST pass before marking any frontend story complete
- `backend/.venv/bin/pytest` MUST pass before marking any backend story complete
- Coverage must remain ≥ 90% throughout — check after each story, not just at Polish
