# Quickstart: Vocabulary Flashcards (002)

**Branch**: `002-vocabulary-flashcards` | **Date**: 2026-03-22

This guide covers how to run, test, and extend the Flashcards feature during development.

---

## Prerequisites

The existing dev environment must be working. If it's not, set it up first:

```bash
# Backend venv
python3 -m venv backend/.venv
source backend/.venv/bin/activate
cd backend && pip install -e ".[dev]"

# Frontend
cd frontend && npm install
```

---

## Running the App

```bash
# Start both backend and frontend (existing script)
./run.sh
```

Or individually:
```bash
# Backend (from repo root)
source backend/.venv/bin/activate
uvicorn app.main:app --reload --app-dir backend

# Frontend (from repo root)
cd frontend && npm run dev
```

The Flashcards section is accessible at `http://localhost:5173/flashcards`.

---

## Running Tests

### Backend unit + integration tests

```bash
cd backend
source .venv/bin/activate

# All tests with coverage
.venv/bin/pytest

# Flashcards module only
.venv/bin/pytest tests/ -k "flashcard"

# Single test file
.venv/bin/pytest tests/unit/flashcards/test_classification_engine.py -v
```

Coverage threshold is 90% (enforced in `pyproject.toml`).

### Frontend unit tests (Vitest)

```bash
cd frontend
npm run test          # run once
npm run test:watch    # watch mode
npm run test:coverage # with coverage
```

### Frontend E2E tests (Playwright)

```bash
cd frontend

# First time only — install browser
npx playwright install chromium

# Run all E2E tests (starts dev server automatically)
npm run test:e2e

# Debug a specific spec
npm run test:e2e:debug -- e2e/flashcards.spec.ts
```

All API calls in E2E tests are intercepted via `page.route()` — no live backend required.

---

## Key File Locations

### Backend

| Path | Purpose |
|---|---|
| `backend/app/flashcards/` | Flashcards domain module (new) |
| `backend/app/flashcards/router.py` | FastAPI router — all `/api/flashcards/*` endpoints |
| `backend/app/flashcards/models.py` | SQLAlchemy ORM models (new tables) |
| `backend/app/flashcards/schemas.py` | Pydantic request/response schemas |
| `backend/app/flashcards/services/classification.py` | `ClassificationEngine` — pure classification logic |
| `backend/app/flashcards/services/deck_generation.py` | `DeckGenerationService` — algorithm selection |
| `backend/app/flashcards/services/session.py` | `SessionService` — session lifecycle + card results |
| `backend/app/flashcards/services/analytics.py` | `AnalyticsService` — aggregated stats |
| `backend/app/flashcards/services/llm_cache.py` | `LlmCacheService` — LLM content get-or-create |
| `backend/app/flashcards/services/srs.py` | `SpacedRepetitionService` — interval management |
| `backend/app/database.py` | Import new models here so `create_all()` creates tables |
| `backend/app/main.py` | Include flashcard router here |

### Backend Tests

| Path | Purpose |
|---|---|
| `backend/tests/unit/flashcards/` | Unit tests for all service classes |
| `backend/tests/integration/flashcards/` | Integration tests for all API endpoints |
| `backend/tests/contract/service_interfaces/` | Contract tests for new service ABCs |

### Frontend

| Path | Purpose |
|---|---|
| `frontend/src/pages/Flashcards.tsx` | Top-level Flashcards section entry point |
| `frontend/src/pages/FlashcardPractice.tsx` | Active session card-by-card UI |
| `frontend/src/pages/FlashcardSummary.tsx` | Post-session summary screen |
| `frontend/src/pages/FlashcardAnalytics.tsx` | Analytics dashboard |
| `frontend/src/components/flashcards/` | Reusable flashcard components |
| `frontend/src/services/flashcardsApi.ts` | All API calls for flashcard endpoints |
| `frontend/e2e/flashcards.spec.ts` | E2E tests — word list and deck generation |
| `frontend/e2e/flashcard-practice.spec.ts` | E2E tests — practice session flow |
| `frontend/e2e/flashcard-analytics.spec.ts` | E2E tests — analytics dashboard |

---

## Adding a New Practice Mode

1. Add the new mode enum value to `PracticeMode` in `backend/app/flashcards/models.py`
2. Add the mode's card rendering logic in `frontend/src/components/flashcards/CardPrompt.tsx`
3. Add a mode-specific help text entry in `frontend/src/components/flashcards/HelpOverlay.tsx`
4. Add/update E2E test in `frontend/e2e/flashcard-practice.spec.ts`
5. Run `npm run test:e2e` — must pass with zero failures

---

## Adding a New Deck Generation Algorithm

1. Add the algorithm enum value to `GenerationAlgorithm` in `backend/app/flashcards/models.py`
2. Implement a new `select_words()` strategy in `backend/app/flashcards/services/deck_generation.py`
3. Follow the `Strategy` pattern — each algorithm is a callable that receives the eligible word pool and returns an ordered list
4. Add unit tests in `backend/tests/unit/flashcards/test_deck_generation.py`

---

## Environment Notes

- All LLM, TTS, and STT services run locally — no internet required
- SQLite database lives at `~/.open-language/app.db` (auto-created on first start)
- TTS audio cache lives at `~/.open-language/tts_cache/`
- New flashcard tables are created automatically on `app.main` startup via `init_db()`
