# Implementation Plan: Speak — Role-Play Conversation Chat

**Branch**: `001-speak-roleplay-chat` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-speak-roleplay-chat/spec.md`

## Summary

Build a fully local language-practice application where a learner selects a role-play scenario and holds a spoken conversation with an AI partner. The user speaks (via browser MediaRecorder → faster-whisper STT) or types; the AI replies (via Ollama/llama3.1) and its response is spoken aloud (via Piper TTS). Per-message learning tools (grammar feedback, translation, alternative phrasing, word lookup + save) and assistance panels (suggested response, expression helper) layer on top. All inference, transcription, synthesis, and storage run locally with no cloud dependencies.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript/React 18 (frontend)
**Primary Dependencies**: FastAPI, Uvicorn, SQLite (via SQLAlchemy), faster-whisper, Ollama Python client (llama3.1), Piper TTS, ffmpeg/pydub (audio conversion), React 18, Vite, React Query
**Storage**: SQLite — conversations, messages, vocabulary items, user settings
**Testing**: pytest + httpx (backend unit + integration), Vitest + React Testing Library (frontend)
**Target Platform**: Linux desktop, single-machine local app (browser UI served by FastAPI)
**Project Type**: Web application (single-process: FastAPI serves both React SPA and REST/SSE API)
**Performance Goals**: AI first token visible ≤ 3 s; TTS audio starts playing ≤ 2 s after generation; STT result returned ≤ 3 s for recordings up to 30 s
**Constraints**: Fully offline; no API keys; single port (FastAPI); MediaRecorder → WAV conversion before STT
**Scale/Scope**: Single local user; single active conversation at a time; SQLite sufficient at any realistic local history size

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clean Code — functions ≤ 20 lines, intention-revealing names | ✅ PASS | Enforced at implementation; plan specifies small focused services |
| II. SOLID — SRP, OCP, LSP, ISP, DIP | ✅ PASS | ABC + factory pattern explicitly requested; each service is one responsibility |
| III. TDD — tests before code, ≥ 90% coverage, no skips | ✅ PASS | All tasks will include test tasks as mandatory first step |
| IV. Simple UI — single primary action per screen, immediate feedback, accessibility | ✅ PASS | Home screen: "Start Chat" is primary; chat screen: record button is primary |
| V. Extensibility & Compartmentalization — ABCs, defined interfaces, no cross-module imports | ✅ PASS | ScenarioProvider, LLMProvider, STTProvider, TTSProvider, StorageProvider all declared as ABCs before implementation |

**Complexity Tracking** (justified violations only):

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Dual-process dev server (Vite dev + FastAPI) | Hot-reload DX during development | Serving the unbuilt Vite bundle from FastAPI is not possible; only the built output is served in production; acceptable split limited to dev environment |
| Audio conversion step (WebM → WAV) before STT | faster-whisper requires PCM/WAV input; MediaRecorder outputs WebM/Opus | No pure-Python zero-dependency path; ffmpeg is a standard system dependency on Linux |

## Project Structure

### Documentation (this feature)

```text
specs/001-speak-roleplay-chat/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   ├── api.md           ← REST + SSE endpoint contracts
│   └── service-interfaces.md  ← ABC contracts for all four services
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                  # FastAPI app entry point; mounts static, registers routers
│   ├── config.py                # Settings (model name, voice, languages, DB path)
│   ├── database.py              # SQLAlchemy engine + session factory
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── vocabulary_item.py
│   │   └── settings.py
│   ├── services/
│   │   ├── base.py              # Abstract base classes (STTProvider, LLMProvider, TTSProvider, StorageProvider)
│   │   ├── factory.py           # Factory functions returning configured concrete instances
│   │   ├── stt/
│   │   │   ├── base.py          # STTProvider ABC
│   │   │   └── whisper.py       # WhisperSTT (faster-whisper)
│   │   ├── llm/
│   │   │   ├── base.py          # LLMProvider ABC
│   │   │   └── ollama.py        # OllamaLLM (ollama Python client)
│   │   ├── tts/
│   │   │   ├── base.py          # TTSProvider ABC
│   │   │   └── piper.py         # PiperTTS
│   │   └── storage/
│   │       ├── base.py          # StorageProvider ABC
│   │       └── sqlite.py        # SQLiteStorage (SQLAlchemy)
│   ├── routers/
│   │   ├── conversations.py     # CRUD for conversations + messages
│   │   ├── chat.py              # POST /chat/message (SSE stream), POST /chat/start
│   │   ├── audio.py             # POST /audio/transcribe, GET /audio/tts, GET /audio/tts/slow
│   │   ├── learning.py          # POST /learning/grammar, /learning/translate, /learning/phrasing
│   │   ├── vocabulary.py        # POST/GET /vocabulary (save + list saved words)
│   │   └── settings.py          # GET/PUT /settings
│   └── prompts/
│       └── templates.py         # System prompt builders per language/scenario
└── tests/
    ├── unit/
    │   ├── services/
    │   └── prompts/
    ├── integration/
    │   ├── routers/
    │   └── services/
    └── contract/
        └── service_interfaces/  # Tests that each concrete impl satisfies ABC contract

frontend/
├── index.html
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── pages/
│   │   ├── Home.tsx             # Scenario selection + Start Chat
│   │   ├── Chat.tsx             # Main conversation screen
│   │   ├── History.tsx          # Past conversations list
│   │   └── Settings.tsx         # Model + preference configuration
│   ├── components/
│   │   ├── scenario/
│   │   │   ├── ScenarioCard.tsx
│   │   │   └── ScenarioCard.test.tsx
│   │   ├── chat/
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── MessageBubble.test.tsx
│   │   │   ├── RecordButton.tsx
│   │   │   ├── RecordButton.test.tsx
│   │   │   ├── LearningToolPanel.tsx
│   │   │   ├── SuggestedResponsePanel.tsx
│   │   │   └── ExpressionHelperPanel.tsx
│   │   └── shared/
│   │       ├── AudioPlayer.tsx  # Wraps <audio> element, exposes playbackRate
│   │       └── ErrorBanner.tsx
│   ├── hooks/
│   │   ├── useRecorder.ts       # MediaRecorder lifecycle
│   │   ├── useSSE.ts            # SSE stream consumer
│   │   └── useAudio.ts          # <audio> element control + slow playback
│   ├── services/
│   │   └── api.ts               # Typed fetch wrappers for all backend endpoints
│   └── store/
│       └── conversationStore.ts # React context/state for active conversation
└── tests/                       # Vitest + React Testing Library
```

**Structure Decision**: Web application split (Option 2). FastAPI backend owns all AI services, data persistence, and audio processing. React/Vite frontend is the UI layer. In production, `npm run build` outputs to `backend/static/` and FastAPI serves it from `/`; all API routes are under `/api/`. In development, Vite dev server proxies `/api` to FastAPI.

## Phase 0: Research

*Full findings in [research.md](research.md). Key decisions:*

| Topic | Decision |
|-------|----------|
| Browser → STT audio | MediaRecorder (WebM/Opus) → multipart POST → FFmpeg → 16kHz WAV → faster-whisper |
| STT settings | `model=base`, `beam_size=5`, explicit language, startup model preload |
| TTS integration | `piper.voice.PiperVoice` PyPI API; `ThreadPoolExecutor`; returns WAV bytes |
| Slow playback | Client-side `<audio>.playbackRate = 0.65` — zero server overhead |
| LLM streaming | Ollama `stream=True` → FastAPI `StreamingResponse(text/event-stream)` → React `fetch()` + `ReadableStream` |
| SSE vs WebSocket | SSE — turn-taking pattern needs only server→client streaming; POST body requires `fetch()` not `EventSource` |
| Single port | FastAPI serves Vite build as static at `/`; API at `/api/*`; Vite proxy in dev |
| SQLite access | Sync SQLAlchemy in `run_in_executor`; WAL mode for concurrent read/write |

## Phase 1: Design Decisions

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](data-model.md) |
| API contracts | [contracts/api.md](contracts/api.md) |
| Service interface contracts | [contracts/service-interfaces.md](contracts/service-interfaces.md) |
| Quickstart | [quickstart.md](quickstart.md) |

**Key architectural decisions**:

1. **All four services behind ABCs before any concrete code**: `ScenarioProvider`, `STTProvider`, `LLMProvider`, `TTSProvider`, `StorageProvider` — declared as ABCs with factory functions. Concrete impls injected via FastAPI `Depends`. Satisfies Constitution V.

2. **SSE streaming for LLM turns**: Tokens stream from Ollama through FastAPI to React as SSE. The `done` event triggers the TTS call. This keeps the conversation loop responsive.

3. **TTS audio caching**: Generated WAV files are cached to disk by `message_id`. Slow playback reuses the same file client-side. Avoids regeneration costs.

4. **Per-message auto-save**: Every message is persisted immediately on add (before LLM call for user messages; at `done` event for assistant messages). Crash-safe.

5. **LearningToolResult caching**: `get_or_create_learning_result` pattern — first call hits LLM, subsequent calls return DB row. Idempotent endpoints.

6. **Expression helper in memory only**: Side-panel conversation history is held in server memory keyed by client-generated `helper_session_id`. Not persisted — aligns with spec intent.

7. **Language detection via LLM system prompt**: No separate `langdetect` library. The system prompt instructs llama3.1 to redirect only on full-message wrong-language input (clarification-aligned).

## Phase 2: Implementation Notes

*See [tasks.md](tasks.md) — generated by `/speckit.tasks`.*
