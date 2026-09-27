# Data Model: German Language Support

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

This feature adds **one table**, **two columns** and **one idempotent seed**. It rewrites no
existing row. Everything else is fixed, in-code catalogue data.

---

## 1. `PracticeLanguage` (in-code catalogue)

Module: `backend/app/practice_languages/catalog.py`, exported from `app.practice_languages`.

Frozen, slotted dataclass. `PRACTICE_LANGUAGES: Mapping[str, PracticeLanguage]` holds the entries
in display order.

| `code` | `name` | `default_voice` |
|---|---|---|
| `es` | Spanish | `es_ES-davefx-medium` |
| `de` | German | `de_DE-thorsten-medium` |

- `DEFAULT_PRACTICE_LANGUAGE = "es"` (FR-001).
- `NATIVE_LANGUAGE_NAMES = {"en": "English"}`. The native language is not selectable (spec
  Assumptions), but prompts need its name (research R2).
- `language_name(code)` looks in `PRACTICE_LANGUAGES`, then in `NATIVE_LANGUAGE_NAMES`, and raises
  `UnknownLanguage` otherwise.

**Invariants** (unit tests, research R3):

| # | Invariant |
|---|---|
| I1 | `DEFAULT_PRACTICE_LANGUAGE in PRACTICE_LANGUAGES` |
| I2 | Every language has ≥ 1 voice in `AVAILABLE_VOICES` whose `language == code` |
| I3 | Every `default_voice` exists in `AVAILABLE_VOICES` and belongs to its own language |
| I4 | Every key in `AVAILABLE_VOICES` appears in `run.sh`'s `PIPER_VOICES` (FR-017) |
| I5 | No code is both a practice language and a native-only language |
| I6 | Codes are lowercase ISO 639-1, valid as faster-whisper `language=` values |

## 2. `ConversationLanguages` (value object)

Module: `backend/app/practice_languages/naming.py`. This is the prompt-facing view of a
conversation's languages (research R2).

| Field | Type | Example |
|---|---|---|
| `target_code` | `str` | `"de"` |
| `target_name` | `str` | `"German"` |
| `native_name` | `str` | `"English"` |

- Constructed only by `ConversationLanguages.of(target_code, native_code)`. It raises
  `UnknownLanguage` for a code that is not in the catalogue. A corrupt stored value surfaces; it is
  never guessed.
- Routers pass `target_name` and `native_name` to prompt builders, and `target_code` to anything
  that stores or selects (TTS, cache slots).

## 3. `VoiceInfo` (extended)

Module: `backend/app/services/tts/voices.py`.

- New read-only property: `language` is the part of `locale` before `_` (`de_DE` → `de`).
- `AVAILABLE_VOICES` gains two entries (research R4):

| Key | Display name | Gender | Locale | Quality | Speaking rate |
|---|---|---|---|---|---|
| `de_DE-thorsten-medium` | Thorsten (Germany) | male | `de_DE` | medium | natural |
| `de_DE-kerstin-low` | Kerstin (Germany) | female | `de_DE` | low | natural |

- New helper: `voices_for(language_code) -> tuple[VoiceInfo, ...]`, in catalogue order.

## 4. `voice_choices` (new table)

ORM model: `backend/app/models/voice_choice.py` (`VoiceChoice`). It is created by `create_all()`,
and registered in `init_db()`'s model imports.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `target_language` | `VARCHAR(20)` | **PK** | A practice-language code |
| `voice_key` | `VARCHAR(200)` | NOT NULL | A `VoiceInfo.key` |
| `updated_at` | `DATETIME` (tz) | NOT NULL | Set on insert and update |

- One row per language the learner has **explicitly** chosen a voice for. No row means "use the
  default" (FR-016).
- Written only through `StorageProvider.save_voice_choice(language, voice_key)`, which upserts.
  Validation happens before this, in the settings router (contracts §2).
- **Resolution** is `voice_for(code, voice_choices) -> str`:
  - return the stored choice if `voice_choices[code]` belongs to `code`'s language (by
    `VoiceInfo.language`);
  - otherwise return `PRACTICE_LANGUAGES[code].default_voice`.

  A mismatched or unknown stored key is therefore never spoken (FR-018).

### Seed (one-time, idempotent)

`_seed_voice_choices(conn)` runs in `_migrate_db()`, after the additive columns:
1. Read `(target_language, tts_voice)` from the `app_settings` row, if one exists.
2. If `tts_voice` is a catalogue voice whose `language == target_language`, then
   `INSERT OR IGNORE INTO voice_choices (target_language, voice_key, updated_at) VALUES (…)`.

Before 006, `target_language` could only be `es`, so an upgraded install keeps its Spanish voice
(FR-024, US2-4). Later runs insert nothing new: either the row exists, or the pair does not match.

## 5. `app_settings` (semantics change, no schema change)

| Column | Before 006 | From 006 |
|---|---|---|
| `target_language` | Stored `"es"`; never exposed in the UI; unvalidated | **The practice language** (FR-001–FR-003). Validated against `PRACTICE_LANGUAGES` on write. |
| `tts_voice` | The voice | **Legacy**. Read only by the seed (§4). Never written or read by application code again. The ORM field stays, with a comment, because the schema is additive-only. |
| `native_language` | `"en"` | Unchanged |

## 6. `AppSettingsRecord` (changed)

Module: `backend/app/services/storage/base.py`.

- **Removed**: `tts_voice: str`.
- **Added**: `voice_choices: Mapping[str, str]`, defaulting to an empty mapping. It holds the
  learner's explicit choices from `voice_choices`, keyed by language code.
- `SQLiteStorageProvider._settings_to_record` loads it with one query.

`StorageProvider` gains one abstract method:

```python
@abstractmethod
def save_voice_choice(self, target_language: str, voice_key: str) -> None:
    """Remember the learner's voice for one language (upsert)."""
```

## 7. `decks` and `practice_sessions` (one new column each)

Added through `_ADDITIVE_COLUMNS` in `backend/app/database.py`:

```text
("decks",             "target_language VARCHAR(20) NOT NULL DEFAULT 'es'")
("practice_sessions", "target_language VARCHAR(20) NOT NULL DEFAULT 'es'")
```

- SQLite applies the `DEFAULT` to every existing row when the column is added. That is FR-021:
  existing decks and history belong to Spanish.
- The ORM fields (`Deck.target_language`, `PracticeSession.target_language`) are `nullable=False`
  with **no Python default**. Every insert must name a language, and a missing one fails with an
  integrity error. It never silently becomes Spanish.
- `DeckRecord` and `SessionRecord` gain `target_language: str`.
- A session's language is copied from its deck in `create_session` and never changes. It survives
  deck deletion (`deck_id` is set to NULL, the language is not).

### What gets its language by join (no column)

| Table | Language comes from |
|---|---|
| `deck_cards` | `decks` (via `deck_id`) |
| `card_results` | `practice_sessions` (via `session_id`) |
| `session_classification_snapshots` | `practice_sessions` (via `session_id`) |
| `flashcard_rating_history`, `spaced_repetition_schedule` | `vocabulary_items` (via `vocabulary_item_id`) |
| `word_llm_cache` | already keyed by `language` |

## 8. `FlashcardStorageProvider` (signatures extended)

A **required, keyword-only** `language: str` is added to every method that lists, counts or
creates. There is no default, so every caller must decide.

| Method | Filter or effect |
|---|---|
| `list_words(*, language, …)` | `VocabularyItem.target_language == language` |
| `list_decks(*, language)` | `Deck.target_language == language` |
| `create_deck(…, *, language)` | Sets `Deck.target_language` |
| `create_session(…)` | Copies `target_language` from the deck (no new parameter) |
| `get_sessions_since(cutoff, *, language)` | `PracticeSession.target_language == language` |
| `get_card_results_since(cutoff, *, language)` | Joined to `practice_sessions`, filtered |
| `get_classification_counts(*, language)` | Words of that language only |
| `get_classification_snapshots_since(cutoff, *, language)` | Joined to `practice_sessions`, filtered |

These stay unscoped (by id): `get_word`, `get_deck`, `get_deck_cards`, `get_session`, and every
update or delete by id. `delete_llm_cache_for_language` is unchanged.

**Services**:
- `AnalyticsService(storage, language)` passes its language to every storage call, including
  `streak`, `_recently_learned`, `hardest_words` and `_count_sessions_this_week`.
- `SessionService` reads `session.target_language` for the classification snapshot and the streak,
  never the setting.

## 9. `conversations` and `vocabulary_items` (no schema change)

- `Conversation.target_language` is set from `app_settings.target_language` at creation (existing
  code) and never changes (FR-006). There is no update path, and none is added.
- `VocabularyItem.target_language` and `native_language` are now taken from the **source
  conversation**, falling back to the practice language only when no `source_conversation_id` is
  given (FR-019). A `source_conversation_id` that does not exist is a **404**.
- `UNIQUE(word, target_language)` already makes the same spelling in two languages two words, each
  with its own classification, SRS schedule, rating history and LLM cache (FR-023).

## 10. State and lifecycle summary

```text
practice language (app_settings.target_language)
   │ read once, when a conversation is created
   ▼
conversation.target_language ──── fixed for life ────► every prompt, the STT hint, the TTS voice,
   │                                                      and the language of any word saved from it
   ▼
vocabulary_items.target_language ──► the word's TTS voice, word-info prompts, LLM-cache slot

practice language ──(explicit ?language=)──► the flashcard lists, analytics, and new decks
deck.target_language ──(copied at start)──► practice_sessions.target_language
   ──► the snapshot and streak at session end
```

Nothing in this diagram flows backwards. Changing the practice language never rewrites a
conversation, word, deck or session (FR-025).
