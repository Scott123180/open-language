# Research: Vocabulary Flashcards (002)

**Branch**: `002-vocabulary-flashcards` | **Date**: 2026-03-22

---

## Decision 1: Frontend Charting Library

**Decision**: Recharts

**Rationale**:
- ~60–70 KB gzipped, granular imports (only ship chart types used) — critical for an offline desktop app
- Full TypeScript support with well-typed component props; no config-object layer
- Built-in ARIA labels, keyboard-navigable legends, `prefers-reduced-motion` support — satisfies constitution accessibility gate
- Accepts plain data arrays, so TanStack Query data flows directly into `<LineChart data={queryResult} />` without adapters
- `<ResponsiveContainer>` wraps any chart for fluid mobile-first layouts

**Charts needed → Recharts component**:
| Chart | Recharts Component |
|---|---|
| Accuracy trend (line) | `<LineChart>` + `<Line>` |
| Daily activity (bar) | `<BarChart>` + `<Bar>` |
| Classification over time (stacked area) | `<AreaChart>` + multiple `<Area>` |
| Classification donut | `<PieChart>` + `<Pie innerRadius>` |
| Mode performance (grouped bar) | `<BarChart>` + multiple `<Bar>` |

**Alternatives considered**:
- Chart.js / react-chartjs-2: Heavier (~200 KB), config-object API less natural for React/TypeScript
- Victory: Good TypeScript, but ~2× Recharts bundle size for equivalent features
- Nivo: Beautiful defaults, but significantly larger bundle and SSR-only accessibility features
- Visx: Most flexible, but low-level primitives requiring substantial boilerplate for simple charts

---

## Decision 2: Slow-Speed Audio Playback

**Decision**: Frontend-only via `HTMLAudioElement.playbackRate`

**Rationale**:
The existing `AudioPlayer` component already accepts a `playbackRate` prop and passes it to the `useAudio` hook, which sets `audio.playbackRate` on the native `HTMLAudioElement`. No backend changes are required. The "Slow Speed" button in flashcard practice simply toggles from `playbackRate=1.0` to `playbackRate=0.6`.

**0.6× is within the browser-supported range** (modern browsers support 0.0625–16.0). No pitch distortion occurs at this rate on all major engines (Chrome, Firefox, WebKit).

**Alternatives considered**:
- FFmpeg `atempo` filter on backend: Would require a new query parameter on the TTS endpoint and backend audio processing per word, adding latency and cache complexity. Rejected because the frontend already solves this for free.
- `pydub` speed_change: Same rejection reasoning as FFmpeg; also `pydub` is not a declared dependency.

---

## Decision 3: Flashcard TTS Endpoint

**Decision**: New endpoint `GET /api/flashcards/tts/{vocabulary_item_id}` — separate from the existing message-based TTS endpoint.

**Rationale**:
The existing `GET /audio/tts/{message_id}` caches audio per `Message` and stores the path via `storage.set_tts_path()`. Vocabulary words are not messages — they have no `message_id`. A new endpoint reuses the existing `TTSProvider.synthesize()` service but caches audio at `~/.open-language/tts_cache/vocab_{id}.wav`.

**Implementation**: The endpoint reads the word text from `VocabularyItem`, calls `tts.synthesize(word, path)`, caches the path in a new `vocab_tts_cache` column on `vocabulary_items` (or a separate cache file), and returns `FileResponse`.

---

## Decision 4: Word LLM Content Cache

**Decision**: New `WordLlmCache` SQLAlchemy model, following the existing `LearningToolResult` get-or-create pattern.

**Rationale**:
The `get_or_create_learning_result()` method on `StorageProvider` demonstrates the exact pattern needed: check for existing cache entry, call compute if missing, persist and return. The new `WordLlmCache` table is keyed by `(vocabulary_item_id, cache_type, language)` and stores the JSON/text content and generation timestamp.

Cache invalidation on language change: At the service layer, when the user's language config changes, all `WordLlmCache` records for the affected language are deleted.

---

## Decision 5: Classification Engine

**Decision**: Pure Python service class `ClassificationEngine` with no external library dependencies.

**Rationale**:
The classification rules are fully deterministic and defined in the spec with explicit thresholds (rolling last-5, consecutive-3 Knew, etc.). A simple service class with a `recalculate(ratings: list[Rating]) -> WordClassification` method is testable in isolation, has no external dependencies, and can be exercised exhaustively in unit tests. No ML or probabilistic library is needed.

**SRS stage model**:
```
Stage 1: 7 days
Stage 2: 14 days
Stage 3: 30 days
Stage 4: 30 days (monthly, repeating)
```
Stage advances on `KNEW_IT`, holds on `GUESSED`, resets to Stage 1 on `DIDNT_KNOW`.

---

## Decision 6: Flashcard Module Compartmentalization

**Decision**: New `backend/app/flashcards/` domain module with its own router, service layer, models, and public interface.

**Rationale**:
The constitution requires each feature domain to be encapsulated with a clearly defined public interface. The existing structure (`routers/`, `models/`, `services/`) is already organized by type. The flashcards domain is large enough to warrant its own sub-package at `app/flashcards/` containing:
- `router.py` — FastAPI router (exported as the public interface)
- `services/` — `ClassificationEngine`, `DeckGenerationService`, `SessionService`, `AnalyticsService`
- `models.py` — SQLAlchemy ORM models for flashcard entities
- `schemas.py` — Pydantic request/response models

The existing `app/routers/vocabulary.py` extends for flashcard word management (delete, filter, classify) since `VocabularyItem` is the existing entity.

---

## Decision 7: Database Migration Strategy

**Decision**: Follow existing `_migrate_db()` pattern — new flashcard tables are created automatically via `Base.metadata.create_all()` when new models are imported in `init_db()`. No migration library needed.

**Rationale**:
The existing codebase uses a lightweight manual approach: new tables are created on app startup via `create_all()`; new columns on existing tables are added via `ALTER TABLE ... ADD COLUMN` with exception-swallowing for idempotency. The flashcard entities are all new tables, so `create_all()` handles them automatically. The one change to an existing table (`vocabulary_items` — adding classification and tts_cache columns) uses the existing `_add_column_if_missing()` helper.

---

## Decision 8: Frontend State Management for Sessions

**Decision**: TanStack Query for server state; React `useState`/`useReducer` for in-session card state (no global store).

**Rationale**:
Active practice sessions are ephemeral UI state (current card index, accumulated ratings, timer). This is not server state — it lives in the component tree until session end, when it is flushed to the API. TanStack Query handles all read/write operations against the API. No additional state library (Zustand, Redux) is needed.

---

## Decision 9: Analytics Aggregation Location

**Decision**: Aggregations computed server-side in Python service; raw session data stored in DB; analytics endpoints return pre-aggregated JSON.

**Rationale**:
Chart data (accuracy per session, cards per day, classification distribution over time) involves joining and grouping across multiple tables. Python + SQLite aggregation is simpler and more efficient than pushing raw session data to the frontend and aggregating in JavaScript. The analytics service returns shaped data ready for Recharts components.
