# Implementation Plan: Vocabulary Flashcards

**Branch**: `002-vocabulary-flashcards` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)

---

## Summary

Implement a full-featured Flashcards section for vocabulary practice, covering word library management, smart deck generation (4 algorithms + spaced repetition), 4 practice modes (Recall, Listen, Produce, Fill-in-the-Blank), a post-session summary with LLM encouragement, and an analytics dashboard. The feature is built as a compartmentalized `flashcards` domain module on top of the existing FastAPI + SQLite + React 18 stack, extending the existing `vocabulary_items` table and introducing 7 new database tables.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.4 / React 18.3 (frontend)
**Primary Dependencies**:
- Backend: FastAPI 0.111+, SQLAlchemy 2.0+, Ollama (llama3.1), piper-tts, faster-whisper, ffmpeg (subprocess)
- Frontend: React 18, TanStack Query v5, react-router-dom v6, **Recharts** (new — analytics charts)
**Storage**: SQLite with WAL mode and foreign keys enabled; schema migration via `_add_column_if_missing()` for existing tables, `create_all()` for new tables
**Testing**:
- Backend: pytest 8 + pytest-asyncio + pytest-cov (90% coverage enforced), httpx for integration
- Frontend: Vitest + Testing Library (unit), Playwright (E2E, mandatory for all UI changes)
**Target Platform**: Linux desktop (Electron-adjacent, served locally via Vite dev or static build)
**Performance Goals**: Deck generation <5s for 1,000 words; LLM contextual info first response <10s, cached <1s; session summary screen <2s; analytics refresh <5s
**Constraints**: Fully offline; single user; SQLite only; no external services
**Scale/Scope**: Up to 1,000 saved words, ~50 decks, ~500 sessions per user

---

## Constitution Check

*GATE: All items must pass before implementation begins.*

| Principle | Status | Notes |
|---|---|---|
| **Clean Code** — ≤20 line functions, intention-revealing names, no magic strings | ✅ | All service classes enforce this; enums used for all status strings |
| **SOLID — SRP** | ✅ | `ClassificationEngine`, `DeckGenerationService`, `SessionService`, `AnalyticsService`, `LlmCacheService`, `SpacedRepetitionService` each have one responsibility |
| **SOLID — OCP** | ✅ | Deck generation algorithms use the Strategy pattern; new algorithms extend without modifying existing code |
| **SOLID — LSP** | ✅ | New flashcard storage methods added to `StorageProvider` ABC; `SQLiteStorageProvider` is the only concrete — no substitution issue |
| **SOLID — ISP** | ✅ | Flashcard storage operations added as a separate `FlashcardStorageProvider` ABC; not forced onto existing storage consumers |
| **SOLID — DIP** | ✅ | All service classes receive `TTSProvider`, `LLMProvider`, `StorageProvider` via constructor injection; no direct instantiation in business logic |
| **TDD — Non-Negotiable** | ✅ | Every task begins with a failing test; classification engine, SRS, and deck algorithms are pure functions — fully unit-testable |
| **90% coverage** | ✅ | Enforced in `pyproject.toml`; new code must not drop coverage below threshold |
| **Simple UI — single primary action per screen** | ✅ | Word List: primary = Generate Deck; Practice: primary = Self-grade; Summary: primary = Practice Again |
| **Accessibility** | ✅ | Recharts provides ARIA labels; all new buttons get accessible labels; contrast and touch targets audited in checklist |
| **Compartmentalization** | ✅ | `backend/app/flashcards/` is a self-contained domain module; cross-module access only via its router and service layer; no direct imports from other domains |
| **E2E Playwright tests mandatory** | ✅ | Three new E2E spec files required: `flashcards.spec.ts`, `flashcard-practice.spec.ts`, `flashcard-analytics.spec.ts` |
| **No feature flags / if-debug guards** | ✅ | No feature flags needed; feature is self-contained |

**Complexity Tracking**: No violations. The `FlashcardStorageProvider` ABC (ISP decision) is a new interface, not a modification of the existing `StorageProvider` — this is an extension, not a violation.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-vocabulary-flashcards/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── api.md           ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Backend Source Code

```text
backend/app/
├── flashcards/                      ← NEW domain module
│   ├── __init__.py
│   ├── router.py                    ← FastAPI router, prefix=/flashcards
│   ├── models.py                    ← SQLAlchemy ORM: Deck, DeckCard, PracticeSession,
│   │                                   CardResult, FlashcardRatingHistory,
│   │                                   WordLlmCache, SpacedRepetitionSchedule
│   ├── schemas.py                   ← Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── classification.py        ← ClassificationEngine (pure, no I/O)
│       ├── deck_generation.py       ← DeckGenerationService + Algorithm strategies
│       ├── session.py               ← SessionService (lifecycle + card results)
│       ├── analytics.py             ← AnalyticsService (aggregated stats)
│       ├── llm_cache.py             ← LlmCacheService (get-or-create LLM content)
│       └── srs.py                   ← SpacedRepetitionService (interval management)
├── models/
│   └── vocabulary_item.py           ← EXTENDED: +classification, +manual_override, +tts_cache_path
├── routers/
│   └── vocabulary.py                ← EXTENDED: +DELETE, +PATCH classification, +filter params
├── database.py                      ← EXTENDED: import flashcards.models in init_db()
│                                       +_add_column_if_missing for new vocab columns
└── main.py                          ← EXTENDED: include flashcard router

backend/tests/
├── unit/
│   └── flashcards/
│       ├── test_classification_engine.py
│       ├── test_deck_generation.py
│       ├── test_session_service.py
│       ├── test_srs_service.py
│       └── test_analytics_service.py
├── integration/
│   └── flashcards/
│       ├── test_word_library_endpoints.py
│       ├── test_deck_endpoints.py
│       ├── test_session_endpoints.py
│       └── test_analytics_endpoints.py
└── contract/
    └── service_interfaces/
        └── test_flashcard_storage_provider.py
```

### Frontend Source Code

```text
frontend/src/
├── pages/
│   ├── Home.tsx                     ← EXTENDED: add Flashcards navigation card
│   ├── Flashcards.tsx               ← NEW: word list + filter bar + deck generation entry
│   ├── FlashcardDecks.tsx           ← NEW: My Decks list view
│   ├── FlashcardPractice.tsx        ← NEW: active session — card-by-card practice
│   ├── FlashcardSummary.tsx         ← NEW: post-session summary screen
│   └── FlashcardAnalytics.tsx       ← NEW: analytics dashboard
├── components/
│   └── flashcards/
│       ├── WordListItem.tsx          ← word row with classification badge + controls
│       ├── WordFilterBar.tsx         ← classification/date/search filters
│       ├── DeckConfigPanel.tsx       ← deck generation configuration modal/panel
│       ├── CardPrompt.tsx            ← mode-aware card front (Recall/Listen/Produce/FitB)
│       ├── CardAnswer.tsx            ← card answer side + contextual info buttons
│       ├── SelfAssessmentBar.tsx     ← Didn't Know / Guessed / Knew It buttons
│       ├── AudioControls.tsx         ← Listen + Slow Speed buttons (uses existing AudioPlayer)
│       ├── HelpOverlay.tsx           ← mode-specific help overlay
│       └── AnalyticsCharts.tsx       ← Recharts wrappers for all dashboard charts
├── services/
│   └── flashcardsApi.ts             ← NEW: typed fetch wrappers for all flashcard endpoints
└── App.tsx                          ← EXTENDED: add /flashcards/* routes

frontend/e2e/
├── flashcards.spec.ts               ← NEW: word list, filter, deck generation
├── flashcard-practice.spec.ts       ← NEW: all 4 practice modes, session flow, summary
└── flashcard-analytics.spec.ts      ← NEW: analytics dashboard
```

**Structure Decision**: Web application (Option 2). Follows the existing `backend/` + `frontend/` split. Flashcards is a new compartmentalized domain within the existing monorepo structure.

---

## Phase 0: Research

**Status**: Complete — see [research.md](research.md)

**Key decisions resolved**:
1. **Charting library** → Recharts (smallest bundle, full TypeScript, ARIA, TanStack Query compatible)
2. **Slow-speed audio** → Frontend-only via `HTMLAudioElement.playbackRate=0.6` (AudioPlayer already supports this)
3. **Flashcard TTS** → New `GET /api/flashcards/tts/{vocab_item_id}` endpoint, reuses existing `TTSProvider`
4. **LLM cache** → New `word_llm_cache` table, mirrors `LearningToolResult` get-or-create pattern
5. **Classification engine** → Pure Python service, no external library
6. **Module structure** → `backend/app/flashcards/` domain module, `FlashcardStorageProvider` ABC for ISP
7. **DB migrations** → Existing `_add_column_if_missing()` for `vocabulary_items` extensions; `create_all()` for new tables
8. **Analytics aggregation** → Server-side Python; endpoints return pre-shaped chart data
9. **Session state** → TanStack Query for server state; `useReducer` for in-session ephemeral card state

---

## Phase 1: Design & Contracts

**Status**: Complete

### Artifacts Produced

| Artifact | Path | Status |
|---|---|---|
| Data model | [data-model.md](data-model.md) | ✅ Complete |
| API contract | [contracts/api.md](contracts/api.md) | ✅ Complete |
| Quickstart | [quickstart.md](quickstart.md) | ✅ Complete |

### Key Design Decisions

#### `FlashcardStorageProvider` ABC (ISP compliance)

The existing `StorageProvider` ABC exposes vocabulary, conversation, message, and settings operations. The flashcard feature requires ~15 new storage methods. Adding them to `StorageProvider` would violate ISP by forcing non-flashcard consumers (e.g., the chat router) to depend on an interface they don't use.

**Decision**: Define a separate `FlashcardStorageProvider(ABC)` in `backend/app/flashcards/services/storage.py`. `SQLiteStorageProvider` implements both ABCs via Python's multiple inheritance. The flashcard router receives `FlashcardStorageProvider` via dependency injection.

#### Classification Engine Design

`ClassificationEngine` is a pure function service — no I/O, no DB access. It receives a `list[Rating]` (the last 5 ratings for a word) and returns a `WordClassification`. This makes it fully unit-testable without mocking.

Priority rule evaluation order (from FR-009):
1. 3+ consecutive `KNEW_IT` → `LEARNED` (highest priority)
2. `LEARNED` → `DIDNT_KNOW` → `DIFFICULT` (regression check at classification level)
3. 2+ `DIDNT_KNOW` in last 5 → `DIFFICULT`
4. ≥3 of last 5 are `GUESSED` or `KNEW_IT`, ≥1 `GUESSED`, no 3+ consecutive `KNEW_IT` → `ALMOST_LEARNED`
5. Otherwise → `NOT_PRACTICED` (fewer than 5 ratings and no pattern matched)

#### Deck Generation Strategy Pattern

`DeckGenerationService` holds a registry of `AlgorithmStrategy` objects (one per algorithm). Each strategy implements `select(pool: list[ScoredWord], size: int) -> list[ScoredWord]`. The service selects the appropriate strategy by algorithm name, randomizes within each priority tier, and applies fallback chaining.

New algorithms can be added by registering a new strategy — no modification of existing code (OCP).

#### Session Flow & Classification Trigger

Session lifecycle:
1. `POST /sessions` → creates `PracticeSession` with `completed=False`
2. `POST /sessions/{id}/cards/{pos}` → creates `CardResult`, appends to `FlashcardRatingHistory` for the word
3. `POST /sessions/{id}/end` → sets `ended_at`, marks `completed`, then calls `SessionService.recalculate_classifications()` which updates every word that appeared in this session

Classification recalculation is triggered on **every** session end (complete or early exit), for all rated cards.

#### Analytics Queries

The `AnalyticsService` runs 6 SQLAlchemy queries against the session and card result tables:
- **Accuracy trend**: `SELECT session_id, started_at, knew_it_count / cards_reviewed FROM practice_sessions WHERE started_at > cutoff`
- **Daily activity**: `SELECT date(started_at), SUM(cards_reviewed) FROM practice_sessions GROUP BY date`
- **Classification over time**: Snapshots classification distribution at each session end (requires `classification_history` capture or derived from `flashcard_rating_history` replay — see note below)
- **Classification now**: COUNT per classification from `vocabulary_items`
- **Hardest words**: `SELECT vocabulary_item_id, COUNT(*), SUM(rating='knew_it')/COUNT(*) FROM card_results GROUP BY vocab ORDER BY success_rate ASC LIMIT 20`
- **Mode performance**: `SELECT practice_mode, AVG(knew_it_count/cards_reviewed) FROM practice_sessions GROUP BY mode`

**Note on classification over time chart**: Computing the exact classification distribution at each historical point by replaying rating history is expensive for large libraries. The pragmatic approach is to store a snapshot of classification counts at session end in a lightweight `session_classification_snapshot` table (5 integer columns). This is added to the data model as a simple append table that `SessionService` populates after recalculation.

---

## Constitution Check (Post-Design)

All gates still pass. No violations introduced in Phase 1 design.

The `FlashcardStorageProvider` ABC decision (ISP compliance) adds one new interface file and leverages Python's existing multiple-inheritance capability on `SQLiteStorageProvider` — this is additive, not a modification of the existing `StorageProvider`.

Recharts is an additive frontend dependency with no side effects on existing components.

---

## Next Step

Run `/speckit.tasks` to generate the phased, dependency-ordered task list.
