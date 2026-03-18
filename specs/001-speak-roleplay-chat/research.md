# Research: Speak — Role-Play Conversation Chat

**Branch**: `001-speak-roleplay-chat` | **Date**: 2026-03-17

## Decision 1: Audio Format Pipeline (MediaRecorder → faster-whisper)

**Decision**: Browser records as `audio/webm;codecs=opus` → multipart POST to FastAPI → FFmpeg subprocess converts to 16kHz mono WAV → faster-whisper receives file path.

**Rationale**: faster-whisper does not accept WebM/Opus directly; it requires 16kHz mono PCM input via file path (not raw bytes). FFmpeg is the most reliable converter, handles all codec variations, and is already a standard system dependency for audio work on Linux. `pydub` is slower and adds a dependency with the same FFmpeg requirement. `soundfile` cannot transcode.

**Alternatives considered**:
- `pydub`: Higher-level but slower; still requires FFmpeg. Rejected.
- `soundfile`: No codec transcoding support. Rejected.
- Raw binary POST: Marginally faster but adds error-handling complexity. Rejected.

**Browser MIME type strategy**: Use `MediaRecorder.isTypeSupported('audio/webm;codecs=opus')` with WAV fallback for Safari. Explicit MIME type is mandatory — no consistent browser default exists.

**faster-whisper settings for conversational speech**:
- `model_size`: `"base"` (speed/accuracy balance)
- `beam_size`: `5`
- `language`: explicit (e.g. `"es"`) — faster than auto-detect
- `initial_prompt`: `"Conversation in Spanish"` — improves domain accuracy
- `word_level_timestamps`: `False` — not needed, saves latency

**Latency optimizations (to meet SC-002: ≤3s for ≤30s recording)**:
1. Load WhisperModel at app startup (saves 500ms–2s on first request)
2. Run conversion + transcription in `asyncio.run_in_executor()` (non-blocking)
3. Trim trailing silence at the browser before upload (saves 200–500ms)

**System requirement**: `ffmpeg` installed (`apt install ffmpeg`)

---

## Decision 2: Piper TTS Integration Pattern

**Decision**: Use `piper-tts` PyPI package with `PiperVoice` Python API (falling back to subprocess if library API is unstable); run synthesis in `ThreadPoolExecutor` via `asyncio.run_in_executor()`; return WAV bytes as `StreamingResponse(media_type="audio/wav")`; implement slow playback via `<audio>.playbackRate` on the client (no server-side re-synthesis).

**Rationale**: Piper is primarily CLI/binary-based, but the `piper-tts` PyPI package (v1.2+) includes `piper.voice.PiperVoice` for direct Python import. Synthesis is CPU-bound and must be offloaded from the async event loop. Client-side `playbackRate` (e.g. `0.65`) is zero-overhead for slow replay — Piper has no native speed parameter and server-side time-stretching (librosa/sox) wastes compute.

**Voice/language selection**: Voices are ONNX model files named by locale and quality tier (e.g. `es_ES-mls-medium.onnx`). Voice is selected at `PiperVoice.load(model_path)` time. Models are pre-loaded at app startup and cached.

**Audio output**: Piper outputs WAV only (16-bit PCM, typically 22kHz mono). Served as-is to the browser; no transcoding needed.

**Async threading notes**: ONNX Runtime sessions can be thread-sensitive. Pre-load voice model once at startup; use a `ThreadPoolExecutor(max_workers=2)` — one worker per concurrent TTS call. Do not share ONNX sessions across threads; load one session per executor thread if concurrency issues arise.

**Alternatives considered**:
- Server-side speed reduction (librosa/sox pitch-preserving stretch): Wastes compute, adds latency for a trivial UX feature. Rejected.
- Pure subprocess (CLI binary): More portable but slower to start per call and harder to test. Used as fallback only.

---

## Decision 3: LLM Streaming — Ollama + FastAPI SSE + React

**Decision**: Ollama Python client with `stream=True` → FastAPI `StreamingResponse(media_type="text/event-stream")` → React `fetch()` with `ReadableStream` consumer (not `EventSource`, since messages need a POST body with conversation history).

**Rationale**: SSE is the right transport for unidirectional server→client token streaming in a conversational turn-taking pattern. Turns are sequential (user waits for AI, then responds), not concurrent, so WebSocket bidirectionality is wasted overhead. `EventSource` only supports GET; since we need to POST the conversation history, we use `fetch()` + `ReadableStream` instead, which gives the same SSE parsing with POST support.

**Ollama streaming API**:
```python
response = ollama.chat(model="llama3.1", messages=messages, stream=True)
for chunk in response:
    token = chunk["message"]["content"]
    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
yield f"data: {json.dumps({'type': 'done'})}\n\n"
```

**Message history format**: Standard OpenAI-compatible list: `[{"role": "system"|"user"|"assistant", "content": "..."}]`. Full history is sent with each request; Ollama is stateless per call.

**System prompt structure for roleplay + language enforcement**:
```
You are a native {language} speaker acting as {character} in a {scenario} scenario.
ALWAYS respond in {target_language} only.
If the user's ENTIRE message is in a different language, reply only with: "{redirect_phrase}"
Do NOT redirect for isolated foreign words within an otherwise {target_language} message.
Keep responses concise and in character. Do not ask unnecessary questions.
```

**Language detection for redirection**: Handled by the LLM via system prompt instruction (per clarification: redirect only on full-message wrong language). No separate language-detection library needed.

**SSE considerations**:
- FastAPI `StreamingResponse` sets `Content-Type: text/event-stream` automatically
- Each SSE event: `data: <JSON>\n\n`
- React reads stream via `response.body.getReader()` + `TextDecoder`
- Connection closed by client after `{"type": "done"}` event received

**Alternatives considered**:
- WebSocket: Bidirectional overhead unnecessary for turn-taking UX. Adds reconnection complexity. Rejected.
- Polling: Terrible latency and UX for streaming tokens. Rejected.
- `EventSource`: Cannot POST body. Rejected in favour of `fetch()` + `ReadableStream`.

---

## Decision 4: FastAPI + React Vite — Single Port Production Setup

**Decision**: `npm run build` outputs to `backend/static/`; FastAPI mounts `StaticFiles` at `/` and serves `index.html` for all non-API routes (SPA fallback). All API routes prefixed `/api/`. In development: Vite dev server on port 5173 proxies `/api/*` to FastAPI on port 8000.

**Rationale**: Single port in production simplifies deployment (no CORS, no reverse proxy needed for a local app). The Vite proxy handles CORS-free development without changing any fetch URLs.

**vite.config.ts proxy**:
```ts
server: { proxy: { '/api': 'http://localhost:8000' } }
```

**FastAPI static mount** (production):
```python
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```
SPA fallback: FastAPI's `html=True` on `StaticFiles` serves `index.html` for unknown paths, enabling React Router client-side routing.

---

## Decision 5: SQLite Schema Strategy

**Decision**: SQLAlchemy ORM with synchronous session (not async SQLAlchemy) run inside `run_in_executor`; single SQLite file at configurable path; WAL mode enabled for concurrent reads during writes.

**Rationale**: SQLite with WAL mode handles single-user concurrent reads (chat history reads while new messages write) without contention. SQLAlchemy sync sessions are simpler to test and reason about for a single-user app. Async SQLAlchemy (aiosqlite) adds complexity with minimal benefit at this scale.

**Tables**: `conversations`, `messages`, `vocabulary_items`, `app_settings` (see data-model.md for full schema).

---

## Resolved Unknowns Summary

| Unknown | Resolution |
|---------|------------|
| faster-whisper accepts WebM? | No — FFmpeg converts WebM→WAV first |
| Piper Python library or CLI? | `piper.voice.PiperVoice` (PyPI); subprocess fallback |
| Slow playback server or client? | Client-side `<audio>.playbackRate` |
| SSE or WebSocket for LLM streaming? | SSE via `fetch()` + `ReadableStream` (POST-compatible) |
| Single port how? | FastAPI serves Vite build as static; `/api` prefix for all endpoints |
| SQLite concurrent access? | WAL mode; sync SQLAlchemy in executor |
