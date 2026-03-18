# Tasks: Speak — Role-Play Conversation Chat

**Input**: Design documents from `/specs/001-speak-roleplay-chat/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Test tasks are MANDATORY per the TDD constitution (Principle III). Tests MUST be written before implementation (Red-Green-Refactor). Write the test, confirm it fails, then implement.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US8)
- File paths are exact; create parent directories as needed

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding. No tests yet — pure structure.

- [ ] T001 Create backend/ and frontend/ directory trees as defined in plan.md Project Structure
- [ ] T002 Initialize Python backend: pyproject.toml with deps (fastapi, uvicorn[standard], sqlalchemy, faster-whisper, ollama, piper-tts, ffmpeg-python, pytest, httpx, pytest-cov, ruff, black, mypy) in backend/pyproject.toml
- [ ] T003 [P] Initialize frontend with Vite + React + TypeScript (`npm create vite@latest frontend -- --template react-ts`) and install deps (react-router-dom, @tanstack/react-query) in frontend/
- [ ] T004 [P] Configure backend linting: ruff + black + mypy settings in backend/pyproject.toml [tool.ruff], [tool.black], [tool.mypy]
- [ ] T005 [P] Configure frontend linting: ESLint + Prettier in frontend/.eslintrc.json and frontend/.prettierrc
- [ ] T006 Configure pytest with ≥90% coverage enforcement in backend/pyproject.toml [tool.pytest.ini_options] and [tool.coverage.report]
- [ ] T007 [P] Configure Vitest + React Testing Library in frontend/vite.config.ts and frontend/package.json (test script)
- [ ] T008 [P] Configure Vite dev proxy: /api → http://localhost:8000 in frontend/vite.config.ts server.proxy
- [ ] T009 [P] Create .env.example with all variables from quickstart.md (OPEN_LANGUAGE_DB_PATH, TTS_VOICE, VOICE_DIR, OLLAMA_URL, WHISPER_MODEL, WHISPER_DEVICE) at project root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can begin.

**⚠️ CRITICAL**: No user story work starts until this phase is complete.

### Config & Database

- [ ] T010 Implement config management: env vars → frozen Settings dataclass with defaults in backend/app/config.py
- [ ] T011 Implement SQLAlchemy engine (WAL mode + FK pragmas on connect), session factory, declarative Base, and `init_db()` in backend/app/database.py

### ORM Models (parallel — different files)

- [ ] T012 [P] Implement Conversation ORM model (id, scenario_id, scenario_title, target_language, native_language, status enum, started_at, ended_at, llm_model) in backend/app/models/conversation.py
- [ ] T013 [P] Implement Message ORM model (id, conversation_id FK, role enum, content, input_source enum, created_at, tts_audio_path) in backend/app/models/message.py
- [ ] T014 [P] Implement LearningToolResult ORM model (id, message_id FK, tool_type enum, input_selection, result, created_at) with unique constraint on (message_id, tool_type, input_selection) in backend/app/models/learning_tool_result.py
- [ ] T015 [P] Implement VocabularyItem ORM model (id, word, translation, target_language, native_language, source_conversation_id FK, saved_at) with unique constraint on (word, target_language) in backend/app/models/vocabulary_item.py
- [ ] T016 [P] Implement AppSettings ORM singleton model (id=1 always, llm_model, target_language, native_language, tts_voice, suggestion_count, updated_at) with upsert method in backend/app/models/app_settings.py

### Service ABCs (parallel — different files, declare before tests)

- [ ] T017 [P] Declare ScenarioProvider ABC + frozen Scenario dataclass (id, title, description, ai_context_prompt, target_language_hint) in backend/app/services/scenario/base.py
- [ ] T018 [P] Declare STTProvider ABC + TranscriptionResult dataclass + STTError in backend/app/services/stt/base.py
- [ ] T019 [P] Declare LLMProvider ABC (chat_stream → Iterator[str], chat → str, model_name property) + ChatMessage dataclass + LLMError in backend/app/services/llm/base.py
- [ ] T020 [P] Declare TTSProvider ABC (synthesize(text, output_path) → None, voice_name property) + TTSError in backend/app/services/tts/base.py
- [ ] T021 [P] Declare StorageProvider ABC + all DTO dataclasses (ConversationRecord, MessageRecord, LearningToolResultRecord, VocabularyItemRecord, AppSettingsRecord) in backend/app/services/storage/base.py

### Contract Tests (write BEFORE concrete implementations — expect RED)

> **TDD REQUIREMENT: These tests MUST fail before any concrete implementation exists**

- [ ] T022 [P] Contract test: ScenarioProvider — get_random(exclude_id=X) never returns scenario X; get_all() returns ≥1 item in backend/tests/contract/service_interfaces/test_scenario_provider.py
- [ ] T023 [P] Contract test: STTProvider — transcribe(valid_wav_path) returns TranscriptionResult with non-empty text field in backend/tests/contract/service_interfaces/test_stt_provider.py
- [ ] T024 [P] Contract test: LLMProvider — chat() returns str; chat_stream() yields ≥1 str token; concatenation matches chat() output for identical input in backend/tests/contract/service_interfaces/test_llm_provider.py
- [ ] T025 [P] Contract test: TTSProvider — after synthesize(), output_path exists and is a valid non-zero WAV file in backend/tests/contract/service_interfaces/test_tts_provider.py
- [ ] T026 [P] Contract test: StorageProvider — CRUD round-trips: create→get conversation; save→get message; save→list vocabulary; upsert→get settings in backend/tests/contract/service_interfaces/test_storage_provider.py

### Concrete Implementations (make contract tests GREEN)

- [ ] T027 Implement StaticScenarioProvider (10 hard-coded scenarios, no-consecutive-repeat shuffle) in backend/app/services/scenario/static.py
- [ ] T028 Implement SQLiteStorageProvider with all StorageProvider ABC methods (create_conversation, complete_conversation, save_message, get_messages, get_or_create_learning_result, save_vocabulary_item, list_vocabulary, get_settings, update_settings, set_tts_path) in backend/app/services/storage/sqlite.py
- [ ] T029 Unit tests for SQLiteStorageProvider covering all CRUD methods and the caching behaviour of get_or_create_learning_result in backend/tests/unit/services/test_sqlite_storage.py

### Prompt Templates

- [ ] T030 Implement prompt template builder functions (build_roleplay_system_prompt(scenario, target_lang, native_lang), build_grammar_prompt(message), build_translation_prompt(message, native_lang), build_phrasing_prompt(message, target_lang), build_word_lookup_prompt(word, target_lang, native_lang), build_suggestion_prompt(history, target_lang, n)) in backend/app/prompts/templates.py
- [ ] T031 [P] Unit tests for all prompt builder functions: assert required strings (language names, redirect rule, scenario context) appear in output in backend/tests/unit/prompts/test_templates.py

### FastAPI App Skeleton

- [ ] T032 Implement FastAPI app entry point: register all routers under /api prefix, mount frontend/dist as StaticFiles at / with html=True SPA fallback, call init_db() on startup in backend/app/main.py
- [ ] T033 Implement factory functions (make_scenario_provider, make_stt_provider, make_llm_provider, make_tts_provider, make_storage_provider) and FastAPI Depends wrappers in backend/app/services/factory.py
- [ ] T034 Implement global exception handler returning plain-language JSON {"detail": "..."} for all unhandled errors; no stack traces in responses in backend/app/main.py

### Frontend App Skeleton

- [ ] T035 [P] Implement React Router: routes for / (Home), /chat/:conversationId (Chat), /history (History), /settings (Settings) in frontend/src/App.tsx and frontend/src/main.tsx
- [ ] T036 [P] Implement typed API client with fetch wrappers for all endpoints defined in contracts/api.md (scenarios, conversations, chat, audio, learning, vocabulary, settings) in frontend/src/services/api.ts
- [ ] T037 [P] Implement ErrorBanner shared component (plain-language error display, dismiss button) with tests in frontend/src/components/shared/ErrorBanner.tsx and frontend/src/components/shared/ErrorBanner.test.tsx
- [ ] T038 [P] Implement conversation state store (React context: active conversation ID, message list, loading/error state) in frontend/src/store/conversationStore.ts

**Checkpoint**: Foundation complete — app boots, database initialises, all ABCs declared, contract tests red, StaticScenarioProvider and SQLiteStorageProvider green.

---

## Phase 3: User Story 1 — Scenario Selection & Starting a Chat (Priority: P1) 🎯 MVP

**Goal**: User opens app, sees a scenario card, taps Refresh to cycle, taps Start Chat, hears the AI's opening message in the target language.

**Independent Test**: Open the app at localhost, tap Refresh several times (never same scenario twice consecutively), tap Start Chat, verify an AI message bubble appears and audio plays automatically.

### Tests for US1 (write BEFORE implementation — expect RED)

- [ ] T039 [P] [US1] Integration test: GET /api/scenarios/current returns {id, title, description}; GET /api/scenarios/next returns a different scenario in backend/tests/integration/routers/test_scenarios.py
- [ ] T040 [P] [US1] Integration test: POST /api/conversations with valid scenario_id returns 201 with ConversationRecord shape in backend/tests/integration/routers/test_conversations.py
- [ ] T041 [P] [US1] Integration test: POST /api/chat/{id}/open streams SSE with ≥1 token event then a done event containing message_id in backend/tests/integration/routers/test_chat_open.py (mock LLM)
- [ ] T042 [P] [US1] Integration test: GET /api/audio/tts/{message_id} returns Content-Type: audio/wav with non-zero body in backend/tests/integration/routers/test_audio_tts.py (mock TTS)
- [ ] T043 [P] [US1] Frontend test: ScenarioCard renders title and description props in frontend/src/components/scenario/ScenarioCard.test.tsx
- [ ] T044 [P] [US1] Frontend test: Home page calls api.getNextScenario() when Refresh button is tapped in frontend/src/pages/Home.test.tsx

### Implementation for US1

- [ ] T045 [US1] Implement GET /api/scenarios/current and GET /api/scenarios/next endpoints (uses ScenarioProvider Depends) in backend/app/routers/scenarios.py
- [ ] T046 [US1] Implement POST /api/conversations endpoint: creates Conversation record from scenario_id + AppSettings languages in backend/app/routers/conversations.py
- [ ] T047 [US1] Implement OllamaLLMProvider: chat_stream() and chat() using ollama.chat(stream=True/False), model_name property in backend/app/services/llm/ollama.py
- [ ] T048 [US1] Implement POST /api/chat/{id}/open SSE endpoint: build roleplay system prompt → stream LLM tokens → persist assistant Message → trigger TTS cache in backend/app/routers/chat.py
- [ ] T049 [US1] Implement PiperTTSProvider: synthesize() via piper.voice.PiperVoice loaded at startup, executed in ThreadPoolExecutor(max_workers=2) in backend/app/services/tts/piper.py
- [ ] T050 [US1] Implement GET /api/audio/tts/{message_id}: return cached WAV from tts_audio_path if set; synthesize and cache otherwise in backend/app/routers/audio.py
- [ ] T051 [US1] Unit tests for OllamaLLMProvider with mocked ollama.chat (assert messages forwarded, stream=True/False, LLMError on failure) in backend/tests/unit/services/test_ollama_llm.py
- [ ] T052 [US1] Unit tests for PiperTTSProvider with mocked PiperVoice (assert WAV written to output_path, TTSError on failure) in backend/tests/unit/services/test_piper_tts.py
- [ ] T053 [US1] Implement ScenarioCard component (title heading, description paragraph, Refresh button as secondary action) in frontend/src/components/scenario/ScenarioCard.tsx
- [ ] T054 [US1] Implement Home page (ScenarioCard + "Start Chat" as single primary action button, navigate to /chat/:id on success) in frontend/src/pages/Home.tsx
- [ ] T055 [US1] Implement useSSE hook (fetch + ReadableStream SSE consumer: parses data: lines, emits onToken/onDone/onError callbacks) in frontend/src/hooks/useSSE.ts
- [ ] T056 [US1] Implement useAudio hook (wraps HTMLAudioElement: play(src), stop, setPlaybackRate, loading/error state) in frontend/src/hooks/useAudio.ts
- [ ] T057 [US1] Implement AudioPlayer shared component (invisible audio element + play/stop controls, accepts playbackRate prop) in frontend/src/components/shared/AudioPlayer.tsx
- [ ] T058 [US1] Implement Chat page skeleton: renders conversation context banner, scrollable message list, calls POST /chat/{id}/open on mount and autoplays TTS on done event in frontend/src/pages/Chat.tsx
- [ ] T059 [US1] Implement MessageBubble component (user/assistant role styling, content text, timestamp, slot for action buttons) with accessibility ARIA roles in frontend/src/components/chat/MessageBubble.tsx and frontend/src/components/chat/MessageBubble.test.tsx
- [ ] T060 [P] [US1] Frontend tests: useSSE hook (mocked fetch ReadableStream) emits correct callbacks in frontend/src/hooks/useSSE.test.ts

**Checkpoint**: US1 complete — open app, pick a scenario, Start Chat, hear AI speak its opening line.

---

## Phase 4: User Story 2 — Respond by Voice or Text (Priority: P1)

**Goal**: User records a voice response (or types), sees transcription, AI streams a reply and speaks it aloud. Wrong-language responses are politely redirected.

**Independent Test**: In an active chat, tap record, speak a sentence in the target language, tap stop — transcription appears as user message, AI replies and audio plays. Type a message and submit — same result.

### Tests for US2 (write BEFORE implementation — expect RED)

- [ ] T061 [P] [US2] Integration test: POST /api/audio/transcribe with WebM file returns {text, detected_language}; empty audio returns 400 in backend/tests/integration/routers/test_transcribe.py (mock STT)
- [ ] T062 [P] [US2] Integration test: POST /api/chat/{id}/message streams user_message_saved event then token events then done event in backend/tests/integration/routers/test_chat_message.py (mock LLM)
- [ ] T063 [P] [US2] Unit test: convert_webm_to_wav() writes a 16kHz mono WAV file from WebM bytes using ffmpeg subprocess in backend/tests/unit/services/test_audio_conversion.py
- [ ] T064 [P] [US2] Frontend test: RecordButton renders idle state; transitions to recording on click; shows stop button while recording in frontend/src/components/chat/RecordButton.test.tsx
- [ ] T065 [P] [US2] Frontend test: useRecorder hook calls MediaRecorder.start() on startRecording(); returns Blob on stop() in frontend/src/hooks/useRecorder.test.ts

### Implementation for US2

- [ ] T066 [US2] Implement convert_webm_to_wav(webm_bytes: bytes) → Path using ffmpeg subprocess (-acodec pcm_s16le -ar 16000 -ac 1) with temp file cleanup in backend/app/services/audio/conversion.py
- [ ] T067 [US2] Implement WhisperSTTProvider: transcribe() converts input WAV → WhisperModel.transcribe() in asyncio.run_in_executor(), joins segments into text in backend/app/services/stt/whisper.py
- [ ] T068 [US2] Implement POST /api/audio/transcribe endpoint: receive multipart audio file → convert → STT → return TranscriptionResult JSON in backend/app/routers/audio.py
- [ ] T069 [US2] Implement POST /api/chat/{id}/message SSE endpoint: persist user Message immediately → build full history + system prompt → stream LLM → persist assistant Message → yield done with message_id in backend/app/routers/chat.py
- [ ] T070 [US2] Extend build_roleplay_system_prompt() with full multi-turn history formatting and wrong-language redirect instruction (entire message = wrong language only) in backend/app/prompts/templates.py
- [ ] T071 [US2] Unit tests for WhisperSTTProvider with mocked WhisperModel (assert segments joined, STTError on model exception, executor used) in backend/tests/unit/services/test_whisper_stt.py
- [ ] T072 [US2] Implement useRecorder hook (MediaRecorder lifecycle: getUserMedia, isTypeSupported fallback, start, dataavailable accumulation, stop → Blob) in frontend/src/hooks/useRecorder.ts
- [ ] T073 [US2] Implement RecordButton component (idle/recording/processing states with visual indicator, microphone icon, accessible labels) in frontend/src/components/chat/RecordButton.tsx
- [ ] T074 [US2] Wire voice input into Chat page: record → POST /audio/transcribe → append user bubble → POST /chat/{id}/message SSE → append streaming assistant bubble → autoplay TTS in frontend/src/pages/Chat.tsx
- [ ] T075 [US2] Wire text input into Chat page: keyboard input field + submit button → same SSE flow as voice in frontend/src/pages/Chat.tsx
- [ ] T076 [US2] Add "Play Slower" button to AI MessageBubble: calls useAudio setPlaybackRate(0.65) and replays the TTS audio for that message in frontend/src/components/chat/MessageBubble.tsx

**Checkpoint**: US2 complete — full voice + text conversation loop works end-to-end, including language enforcement.

---

## Phase 5: User Story 3 — Per-Message Learning Tools (Priority: P2)

**Goal**: Grammar check, translate, and alternative phrasing buttons on each message; results are cached and re-readable.

**Independent Test**: Send two messages; tap Grammar Feedback on a user message — result appears. Tap Translate on an AI message — result appears. Tap the same button again — result returns instantly (cached, no LLM call).

### Tests for US3 (write BEFORE implementation — expect RED)

- [ ] T077 [P] [US3] Integration test: POST /api/learning/grammar returns result; second call returns cached=true with same result in backend/tests/integration/routers/test_learning.py
- [ ] T078 [P] [US3] Integration test: POST /api/learning/translate caches result; POST /api/learning/phrasing returns alternative in backend/tests/integration/routers/test_learning.py
- [ ] T079 [P] [US3] Unit test: get_or_create_learning_result calls compute() exactly once for same (message_id, tool_type, None); returns cached on repeat in backend/tests/unit/services/test_sqlite_storage.py
- [ ] T080 [P] [US3] Unit test: grammar, translation, phrasing prompts include message content and target/native language strings in backend/tests/unit/prompts/test_templates.py
- [ ] T081 [P] [US3] Frontend test: LearningToolPanel shows Grammar and Alternative Phrasing buttons for user messages; Translate button for all messages in frontend/src/components/chat/LearningToolPanel.test.tsx

### Implementation for US3

- [ ] T082 [US3] Implement POST /api/learning/grammar, POST /api/learning/translate, POST /api/learning/phrasing endpoints (LLM.chat with appropriate prompt → get_or_create_learning_result) in backend/app/routers/learning.py
- [ ] T083 [US3] Implement get_or_create_learning_result in SQLiteStorageProvider: fetch existing LearningToolResult or call compute() and persist in backend/app/services/storage/sqlite.py
- [ ] T084 [US3] Add grammar, translation, phrasing prompt templates to backend/app/prompts/templates.py
- [ ] T085 [US3] Implement LearningToolPanel component (collapsible action buttons: Grammar, Translate, Alternative Phrasing; inline result panel with loading state) in frontend/src/components/chat/LearningToolPanel.tsx
- [ ] T086 [US3] Wire LearningToolPanel into MessageBubble: show Grammar + Translate + Phrasing for user messages; show Translate only for assistant messages in frontend/src/components/chat/MessageBubble.tsx

**Checkpoint**: US3 complete — grammar, translate, and phrasing tools functional and cached on all messages.

---

## Phase 6: User Story 4 — In-Chat Word/Phrase Translation + Vocabulary Save (Priority: P2)

**Goal**: User selects any word in the chat, gets a dictionary-style translation, and can save it for future flashcard practice.

**Independent Test**: Long-press a word in a message bubble — translation popover appears. Tap Save Word — confirmation shown. Restart app — GET /api/vocabulary still returns that item.

### Tests for US4 (write BEFORE implementation — expect RED)

- [ ] T087 [P] [US4] Integration test: POST /api/learning/word-lookup with {message_id, selection} returns translation result in backend/tests/integration/routers/test_learning.py
- [ ] T088 [P] [US4] Integration test: POST /api/vocabulary saves item; GET /api/vocabulary returns it in backend/tests/integration/routers/test_vocabulary.py
- [ ] T089 [P] [US4] Integration test: duplicate POST /api/vocabulary for same (word, target_language) returns 200 (idempotent) in backend/tests/integration/routers/test_vocabulary.py
- [ ] T090 [P] [US4] Frontend test: WordLookupPopover renders translation text and Save Word button; Save Word calls api.saveVocabularyItem() in frontend/src/components/chat/WordLookupPopover.test.tsx

### Implementation for US4

- [ ] T091 [US4] Implement POST /api/learning/word-lookup endpoint (word-lookup prompt → LLM.chat → cache with input_selection → return result) in backend/app/routers/learning.py
- [ ] T092 [US4] Implement POST /api/vocabulary and GET /api/vocabulary endpoints in backend/app/routers/vocabulary.py
- [ ] T093 [US4] Implement save_vocabulary_item (upsert on word+target_language) and list_vocabulary in SQLiteStorageProvider in backend/app/services/storage/sqlite.py
- [ ] T094 [US4] Add word-lookup prompt template (dictionary-style: word, part of speech, definition, example) in backend/app/prompts/templates.py
- [ ] T095 [US4] Implement WordLookupPopover component (appears on text selection, shows translation result, Save Word button, confirmation feedback) in frontend/src/components/chat/WordLookupPopover.tsx
- [ ] T096 [US4] Wire text-selection word lookup into MessageBubble (onMouseUp/onTouchEnd → selection API → show WordLookupPopover) for both user and AI messages in frontend/src/components/chat/MessageBubble.tsx

**Checkpoint**: US4 complete — word/phrase lookup and vocabulary saving work end-to-end.

---

## Phase 7: User Story 5 — Suggested Responses Panel (Priority: P3)

**Goal**: A collapsible panel shows 1 read-only AI-generated suggestion (configurable). User must speak or type it manually.

**Independent Test**: Expand suggestions panel mid-conversation — one suggestion appears as read-only text. Tapping it does nothing. Close panel — conversation unaffected.

### Tests for US5 (write BEFORE implementation — expect RED)

- [ ] T097 [P] [US5] Integration test: POST /api/chat/{id}/suggestions returns {suggestions: [string]} with length equal to AppSettings.suggestion_count in backend/tests/integration/routers/test_suggestions.py
- [ ] T098 [P] [US5] Frontend test: SuggestedResponsePanel is collapsed by default; expands to show read-only text; click on suggestion does NOT call any API or modify input in frontend/src/components/chat/SuggestedResponsePanel.test.tsx

### Implementation for US5

- [ ] T099 [US5] Implement POST /api/chat/{id}/suggestions endpoint (suggestion prompt → LLM.chat → return list of N strings per settings.suggestion_count) in backend/app/routers/chat.py
- [ ] T100 [US5] Add suggestion prompt template (returns exactly N numbered suggestions in target language) in backend/app/prompts/templates.py
- [ ] T101 [US5] Implement SuggestedResponsePanel component (collapsed by default, expand toggle, displays suggestions as non-interactive read-only text with visual "read only" affordance) in frontend/src/components/chat/SuggestedResponsePanel.tsx
- [ ] T102 [US5] Wire SuggestedResponsePanel into Chat page (below input area, collapsed by default) in frontend/src/pages/Chat.tsx

**Checkpoint**: US5 complete — read-only suggestion panel available in chat.

---

## Phase 8: User Story 6 — Native-Language Expression Helper (Priority: P3)

**Goal**: A collapsible side panel with a separate AI chat where the user asks "How do I say X?" in their native language and gets a target-language answer as read-only reference.

**Independent Test**: Open expression helper, type "How do I say 'I need a window seat'?", receive a target-language answer. Return to main chat — conversation unchanged.

### Tests for US6 (write BEFORE implementation — expect RED)

- [ ] T103 [P] [US6] Integration test: POST /api/chat/helper streams SSE tokens + done; second call with same helper_session_id continues from prior context in backend/tests/integration/routers/test_helper.py (mock LLM)
- [ ] T104 [P] [US6] Frontend test: ExpressionHelperPanel maintains its own message list separate from main conversationStore in frontend/src/components/chat/ExpressionHelperPanel.test.tsx

### Implementation for US6

- [ ] T105 [US6] Implement POST /api/chat/helper SSE endpoint: helper_session_id keyed in-memory dict → build helper system prompt (answer in target language, no roleplay) → stream LLM → append to session history in backend/app/routers/chat.py
- [ ] T106 [US6] Implement ExpressionHelperPanel component (collapsible, own message list, native-language input, read-only assistant responses, separate from conversationStore) in frontend/src/components/chat/ExpressionHelperPanel.tsx
- [ ] T107 [US6] Wire ExpressionHelperPanel into Chat page as collapsible side panel in frontend/src/pages/Chat.tsx

**Checkpoint**: US6 complete — expression helper provides reference answers independently of main conversation.

---

## Phase 9: User Story 7 — Session Management & History (Priority: P3)

**Goal**: End Chat saves the session; history screen shows all past chats; each is fully readable.

**Independent Test**: Complete a 3-turn chat, tap End Chat, restart the app, navigate to Past Chats — the conversation appears with correct scenario name, date, and full transcript.

### Tests for US7 (write BEFORE implementation — expect RED)

- [ ] T108 [P] [US7] Integration test: PATCH /api/conversations/{id} with {status: "completed"} sets ended_at to a timestamp in backend/tests/integration/routers/test_conversations.py
- [ ] T109 [P] [US7] Integration test: GET /api/conversations returns list ordered by started_at DESC with correct shape in backend/tests/integration/routers/test_conversations.py
- [ ] T110 [P] [US7] Integration test: GET /api/conversations/{id}/messages returns messages ordered by created_at ASC in backend/tests/integration/routers/test_conversations.py
- [ ] T111 [P] [US7] Frontend test: History page renders a conversation list item with scenario title and formatted date in frontend/src/pages/History.test.tsx

### Implementation for US7

- [ ] T112 [US7] Implement PATCH /api/conversations/{id} endpoint (status=completed → set ended_at, return updated record) in backend/app/routers/conversations.py
- [ ] T113 [US7] Implement GET /api/conversations and GET /api/conversations/{id}/messages endpoints in backend/app/routers/conversations.py
- [ ] T114 [US7] Implement History page (chronological list of ConversationRecord items → click → read-only transcript with all messages) in frontend/src/pages/History.tsx
- [ ] T115 [US7] Add End Chat button to Chat page (primary action when chat is active): PATCH conversation to completed → navigate to / in frontend/src/pages/Chat.tsx
- [ ] T116 [US7] Add Past Chats navigation link to Home page in frontend/src/pages/Home.tsx

**Checkpoint**: US7 complete — all conversations persist and are browsable after restart.

---

## Phase 10: User Story 8 — LLM Model Settings (Priority: P3)

**Goal**: Settings screen lets user pick the LLM model and set suggestion count; change takes effect on next AI call without restart.

**Independent Test**: Open Settings, change LLM model to a different available model, return to chat, send a message — the new model is used (verifiable in Ollama logs).

### Tests for US8 (write BEFORE implementation — expect RED)

- [ ] T117 [P] [US8] Integration test: GET /api/settings returns AppSettings shape; PUT /api/settings with partial body updates and persists changed fields in backend/tests/integration/routers/test_settings.py
- [ ] T118 [P] [US8] Frontend test: Settings page renders model selector with current value and suggestion count input; Save calls api.updateSettings() in frontend/src/pages/Settings.test.tsx

### Implementation for US8

- [ ] T119 [US8] Implement GET /api/settings and PUT /api/settings endpoints (partial update; validate suggestion_count 1–5) in backend/app/routers/settings.py
- [ ] T120 [US8] Implement get_settings and update_settings in SQLiteStorageProvider (upsert singleton id=1) in backend/app/services/storage/sqlite.py
- [ ] T121 [US8] Implement Settings page (model selector dropdown, suggestion count number input 1–5, Save button as primary action, success feedback) in frontend/src/pages/Settings.tsx
- [ ] T122 [US8] Add Settings navigation link to Home page in frontend/src/pages/Home.tsx

**Checkpoint**: US8 complete — model and suggestion count settings persist across restarts.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements spanning all stories; must not break any story checkpoint.

- [ ] T123 [P] Add loading states (spinner/skeleton) and disabled states to all async actions on Home, Chat, History, and Settings pages per Constitution IV (immediate feedback for every action)
- [ ] T124 [P] Audit all interactive elements for accessibility: ARIA labels, roles, keyboard navigation, ≥4.5:1 contrast ratio, ≥44px touch targets, screen-reader semantics across all components
- [ ] T125 Add edge case error handling: empty transcription → show retry message; LLM timeout → show retry button; TTS failure → show text-only fallback; local storage full → warn before new conversation — per spec Edge Cases section in backend/app/routers/ and frontend/src/pages/Chat.tsx
- [ ] T126 [P] Add microphone permission denied handling in Chat page: detect denied permission on getUserMedia → hide RecordButton → show keyboard-only notice with plain-language explanation in frontend/src/pages/Chat.tsx
- [ ] T127 Run full backend test suite and confirm ≥90% line coverage: `pytest --cov=app --cov-report=term-missing` in backend/
- [ ] T128 [P] Run full frontend test suite and confirm ≥90% coverage: `npm run test -- --coverage` in frontend/
- [ ] T129 [P] Run linters with zero errors: `ruff check backend/app && black --check backend/app` and `eslint frontend/src` — fix any violations
- [ ] T130 Validate quickstart.md end-to-end: install all deps, start Ollama, start backend, start frontend, complete a 5-turn role-play conversation (SC-004 acceptance)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user stories**
- **Phase 3–10 (User Stories)**: All depend on Phase 2; can proceed in priority order or in parallel
- **Phase 11 (Polish)**: Depends on all desired user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Notes |
|-------|----------|------------|-------|
| US1 — Scenario + Start | P1 | Phase 2 | Requires LLM + TTS providers; MVP entry point |
| US2 — Voice + Text Loop | P1 | Phase 2, US1 | Requires STT provider + US1 chat page shell |
| US3 — Learning Tools | P2 | Phase 2 | Independent of US1/US2; uses LLM + StorageProvider |
| US4 — Word Lookup + Save | P2 | Phase 2 | Independent; extends LearningToolResult entity |
| US5 — Suggestions | P3 | Phase 2 | Independent; uses LLM |
| US6 — Expression Helper | P3 | Phase 2 | Independent; uses LLM with separate context |
| US7 — History | P3 | Phase 2, US1 | Needs Conversation + Message entities populated |
| US8 — Settings | P3 | Phase 2 | Independent; extends AppSettings entity |

### Within Each User Story

1. Write tests (expect RED)
2. Implement models/services (expect GREEN on contract tests)
3. Implement endpoints/components (expect GREEN on integration/UI tests)
4. Refactor if needed (stay GREEN)
5. Confirm checkpoint independently before moving on

### Parallel Opportunities

- All [P]-marked tasks within a phase can execute simultaneously
- After Phase 2: backend developer can work US3/US4 while frontend developer works US1/US2
- US5, US6, US7, US8 can all be worked simultaneously once Phase 2 is complete

---

## Parallel Example: Phase 2

```
# Can run simultaneously (different files):
T012 ORM: conversation.py
T013 ORM: message.py
T014 ORM: learning_tool_result.py
T015 ORM: vocabulary_item.py
T016 ORM: app_settings.py

# Then simultaneously:
T017 ABC: scenario/base.py
T018 ABC: stt/base.py
T019 ABC: llm/base.py
T020 ABC: tts/base.py
T021 ABC: storage/base.py

# Then simultaneously (write all contract tests):
T022 Contract: ScenarioProvider
T023 Contract: STTProvider
T024 Contract: LLMProvider
T025 Contract: TTSProvider
T026 Contract: StorageProvider
```

## Parallel Example: User Story 1

```
# Write these simultaneously (different test files):
T039 Integration: GET /api/scenarios/*
T040 Integration: POST /api/conversations
T041 Integration: POST /api/chat/{id}/open SSE
T042 Integration: GET /api/audio/tts/{message_id}
T043 Frontend: ScenarioCard.test.tsx
T044 Frontend: Home.test.tsx

# After tests are RED, implement simultaneously:
T047 OllamaLLMProvider     ← backend developer A
T049 PiperTTSProvider      ← backend developer B
T053 ScenarioCard.tsx      ← frontend developer
```

---

## Implementation Strategy

### MVP First (US1 + US2 only — P1 stories)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**critical path**)
3. Complete Phase 3: US1 — Scenario Selection + Start Chat
4. **STOP and VALIDATE**: open app, pick scenario, hear AI opening
5. Complete Phase 4: US2 — Voice + Text Loop
6. **STOP and VALIDATE**: full conversation loop end-to-end
7. Demo / ship MVP

### Incremental Delivery

1. Setup + Foundational → foundation green
2. US1 → hear AI speak → demo
3. US2 → full voice conversation → demo
4. US3 + US4 → learning tools → demo
5. US5 + US6 → assistance features → demo
6. US7 → session history → demo
7. US8 → model settings → demo
8. Polish → production ready

---

## Notes

- [P] = parallel-safe (different files, no incomplete dependencies)
- [US#] label maps every task to its user story for traceability
- Each story checkpoint must be verified before proceeding
- TDD: every RED test must be seen failing before writing implementation
- Commit after each task or logical group; do not batch across checkpoints
- `suggestion_count` default is 1 (AppSettings); configurable up to 5 via US8 Settings
- Expression helper conversation history is in-memory only; not persisted (by design)
- TTS audio files are cached to disk by message_id; cache directory may be cleared between runs
