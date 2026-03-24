# Data Model: Vocabulary Flashcards (002)

**Branch**: `002-vocabulary-flashcards` | **Date**: 2026-03-22

---

## Existing Table: `vocabulary_items` (extended)

The existing table gains new columns to support classification and TTS caching.

```sql
-- Existing columns (unchanged)
id                    INTEGER PRIMARY KEY AUTOINCREMENT
word                  VARCHAR(500) NOT NULL
translation           VARCHAR(500) NOT NULL
target_language       VARCHAR(20) NOT NULL
native_language       VARCHAR(20) NOT NULL
source_conversation_id INTEGER NULL REFERENCES conversations(id) ON DELETE SET NULL
saved_at              DATETIME NOT NULL

-- New columns (added via _add_column_if_missing)
classification        VARCHAR(20) NOT NULL DEFAULT 'not_practiced'
  -- Enum: 'not_practiced' | 'difficult' | 'almost_learned' | 'learned'
manual_override       BOOLEAN NOT NULL DEFAULT FALSE
  -- True = user has manually set classification; reset to FALSE after next session
tts_cache_path        VARCHAR(500) NULL
  -- Cached WAV file path for this word's TTS audio

-- Existing unique constraint preserved
UNIQUE(word, target_language)  -- uq_vocabulary_word_lang
```

**Merge behavior on re-save**: If `(word, target_language)` already exists, update `source_conversation_id` and `saved_at` to the latest values; preserve `classification`, `manual_override`, and all history.

---

## New Table: `flashcard_rating_history`

Stores the rolling per-word rating history used by `ClassificationEngine`. Max 5 entries per word (older entries pruned on insert).

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
vocabulary_item_id INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE CASCADE
rating           VARCHAR(20) NOT NULL
  -- Enum: 'knew_it' | 'guessed' | 'didnt_know'
rated_at         DATETIME NOT NULL
session_id       INTEGER NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE

INDEX idx_rating_history_vocab (vocabulary_item_id, rated_at DESC)
```

**Classification algorithm inputs**: For each word, select the 5 most recent rows ordered by `rated_at DESC`. Apply priority rules from FR-009.

---

## New Table: `decks`

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
name             VARCHAR(200) NOT NULL
practice_mode    VARCHAR(30) NOT NULL
  -- Enum: 'recall' | 'listen' | 'produce' | 'fill_blank'
algorithm        VARCHAR(30) NOT NULL
  -- Enum: 'not_practiced' | 'difficult' | 'previously_guessed' | 'mixed_review'
requested_size   INTEGER NOT NULL
  -- The user-configured deck size (may differ from actual card count)
created_at       DATETIME NOT NULL
last_practiced_at DATETIME NULL
```

---

## New Table: `deck_cards`

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
deck_id          INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE
vocabulary_item_id INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE SET NULL
  -- SET NULL: if word is deleted, card record is retained as orphaned (analytics safe)
position         INTEGER NOT NULL
  -- 0-based card order within the deck
fill_blank_sentence VARCHAR(1000) NULL
  -- Pre-generated sentence for fill-in-the-blank mode; NULL for other modes

UNIQUE(deck_id, position)
INDEX idx_deck_cards_deck (deck_id)
```

---

## New Table: `practice_sessions`

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
deck_id          INTEGER NOT NULL REFERENCES decks(id) ON DELETE SET NULL
  -- SET NULL: if deck is deleted, session records are retained (analytics safe)
practice_mode    VARCHAR(30) NOT NULL
algorithm        VARCHAR(30) NOT NULL
started_at       DATETIME NOT NULL
ended_at         DATETIME NULL
total_cards      INTEGER NOT NULL
cards_reviewed   INTEGER NOT NULL DEFAULT 0
knew_it_count    INTEGER NOT NULL DEFAULT 0
guessed_count    INTEGER NOT NULL DEFAULT 0
didnt_know_count INTEGER NOT NULL DEFAULT 0
completed        BOOLEAN NOT NULL DEFAULT FALSE
  -- TRUE = user finished all cards; FALSE = exited early

INDEX idx_sessions_deck (deck_id)
INDEX idx_sessions_started (started_at DESC)
  -- Used by analytics streak and daily-activity queries
```

---

## New Table: `card_results`

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
session_id       INTEGER NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE
vocabulary_item_id INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE SET NULL
  -- SET NULL: if word is deleted, result retained as orphaned
rating           VARCHAR(20) NOT NULL
  -- Enum: 'knew_it' | 'guessed' | 'didnt_know'
response_type    VARCHAR(10) NULL
  -- Enum: 'spoken' | 'typed' | NULL (card flipped without responding)
user_response    TEXT NULL
  -- User's typed or transcribed spoken response
rated_at         DATETIME NOT NULL

INDEX idx_card_results_session (session_id)
INDEX idx_card_results_vocab (vocabulary_item_id)
```

---

## New Table: `word_llm_cache`

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
vocabulary_item_id INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE CASCADE
cache_type       VARCHAR(20) NOT NULL
  -- Enum: 'meanings' | 'usage' | 'phrases' | 'similar' | 'fill_blank'
language         VARCHAR(20) NOT NULL
  -- Target language code; cache is invalidated per language on config change
content          TEXT NOT NULL
  -- JSON or plain text LLM response
generated_at     DATETIME NOT NULL

UNIQUE(vocabulary_item_id, cache_type, language)
  -- One cache entry per word × type × language combination
```

---

## New Table: `spaced_repetition_schedule`

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
vocabulary_item_id INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE CASCADE
  UNIQUE  -- One schedule row per word
interval_stage   INTEGER NOT NULL DEFAULT 1
  -- Stage 1=7d, Stage 2=14d, Stage 3=30d, Stage 4=30d (monthly)
last_practiced_at DATETIME NULL
next_due_at      DATETIME NULL
  -- NULL = word has never been scheduled (not yet Learned)

UNIQUE(vocabulary_item_id)
```

**Stage transition rules** (applied at session end for each Learned word in the session):
- Rating `knew_it` → `interval_stage = min(interval_stage + 1, 4)`; `next_due_at = now + interval_days[stage]`
- Rating `guessed` → stage unchanged; `next_due_at` unchanged (hold)
- Rating `didnt_know` → `interval_stage = 1`; `next_due_at = now + 7 days`

**Interval days by stage**: `{1: 7, 2: 14, 3: 30, 4: 30}`

---

## Entity Relationship Summary

```
vocabulary_items (1) ──< (N) flashcard_rating_history
vocabulary_items (1) ──< (N) deck_cards
vocabulary_items (1) ──< (N) card_results
vocabulary_items (1) ──< (N) word_llm_cache
vocabulary_items (1) ──  (1) spaced_repetition_schedule

decks (1) ──< (N) deck_cards
decks (1) ──< (N) practice_sessions

practice_sessions (1) ──< (N) card_results
practice_sessions (1) ──< (N) flashcard_rating_history  [via session_id]

conversations (1) ──< (N) vocabulary_items  [existing, via source_conversation_id]
```

---

## Python ORM Model Summary

All new models live in `backend/app/flashcards/models.py` and extend the existing `Base` from `app.database`. They are imported in `app/database.py`'s `init_db()` so `create_all()` creates their tables on startup.

| ORM Class | Table |
|---|---|
| `VocabularyItem` (extended) | `vocabulary_items` |
| `FlashcardRatingHistory` | `flashcard_rating_history` |
| `Deck` | `decks` |
| `DeckCard` | `deck_cards` |
| `PracticeSession` | `practice_sessions` |
| `CardResult` | `card_results` |
| `WordLlmCache` | `word_llm_cache` |
| `SpacedRepetitionSchedule` | `spaced_repetition_schedule` |

---

## Pydantic Schema Summary

All request/response schemas live in `backend/app/flashcards/schemas.py`.

| Schema | Used By |
|---|---|
| `WordListItem` | `GET /api/flashcards/words` response |
| `WordFilterParams` | `GET /api/flashcards/words` query params |
| `DeckConfigRequest` | `POST /api/flashcards/decks` request |
| `DeckSummary` | `GET /api/flashcards/decks` response |
| `DeckDetail` | `GET /api/flashcards/decks/{id}` response |
| `SessionStartRequest` | `POST /api/flashcards/sessions` request |
| `CardResultRequest` | `POST /api/flashcards/sessions/{id}/cards/{pos}` request |
| `SessionSummary` | `GET /api/flashcards/sessions/{id}/summary` response |
| `LlmCacheResponse` | `GET /api/flashcards/words/{id}/info/{type}` response |
| `AnalyticsSummary` | `GET /api/flashcards/analytics` response |
| `EncouragementResponse` | `GET /api/flashcards/sessions/{id}/encouragement` response |
