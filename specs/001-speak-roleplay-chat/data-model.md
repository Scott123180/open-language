# Data Model: Speak — Role-Play Conversation Chat

**Branch**: `001-speak-roleplay-chat` | **Date**: 2026-03-17

## Entity Overview

```
Scenario (static list)
    │
    └──< Conversation (1 scenario → many conversations)
              │
              └──< Message (1 conversation → many messages, ordered)
                       │
                       └──< LearningToolResult (1 message → many cached results)

VocabularyItem  (saved by user from any message's word lookup)

AppSettings     (singleton; user preferences + model config)
```

---

## Entities

### Scenario

Source: static Python list (initial implementation); loaded via `ScenarioProvider` ABC.
Not persisted in the database — scenarios are code-defined. `scenario_id` is a stable slug.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `str` (slug) | PK, unique | e.g. `"buy-train-ticket"` |
| `title` | `str` | required, max 80 chars | Display name on scenario card |
| `description` | `str` | required, max 300 chars | Brief context shown to user |
| `ai_context_prompt` | `str` | required | Seeds the AI system prompt; includes character + setting |
| `target_language_hint` | `str \| None` | optional | If None, uses user's configured target language |

**Initial 10 scenarios** (slugs):
`buy-train-ticket`, `check-into-hotel`, `order-at-restaurant`, `call-doctors-office`,
`ask-for-directions`, `job-interview`, `rent-a-car`, `visit-pharmacy`,
`report-lost-item`, `board-airplane`

---

### Conversation

Persisted in SQLite. One row per role-play session.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `int` | PK, auto-increment | |
| `scenario_id` | `str` | required, FK → Scenario.id | Stored as slug; Scenario not in DB |
| `scenario_title` | `str` | required | Snapshot at creation time (denormalised for history display without needing Scenario loaded) |
| `target_language` | `str` | required | BCP-47 code, e.g. `"es"`, `"fr"` |
| `native_language` | `str` | required | BCP-47 code, e.g. `"en"` |
| `status` | `enum` | `active \| completed` | `active` on create; `completed` on End Chat |
| `started_at` | `datetime` | required, UTC | Set on creation |
| `ended_at` | `datetime \| None` | nullable | Set when status → `completed` |
| `llm_model` | `str` | required | Snapshot of model in use at session start |

**State transitions**:
```
[created] → active
active     → completed  (user taps End Chat)
```

Conversations are never deleted by the app (only if user manually clears history via future feature).

---

### Message

One row per turn. Persisted immediately when added (FR-024: no crash data loss).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `int` | PK, auto-increment | |
| `conversation_id` | `int` | required, FK → Conversation.id | |
| `role` | `enum` | `user \| assistant` | |
| `content` | `str` | required | The message text |
| `input_source` | `enum \| None` | `voice \| keyboard \| None` | `None` for assistant messages |
| `created_at` | `datetime` | required, UTC | Insertion order = conversation order |
| `tts_audio_path` | `str \| None` | nullable | File path to cached WAV on disk; only set for `assistant` messages |

**Ordering**: Use `created_at ASC` for display order. `id ASC` as tiebreaker.

**Audio caching**: TTS WAV files are written to a configurable temp/cache directory. Path stored here for slow-playback re-use within a session. Not guaranteed to persist across restarts (cache dir may be cleared).

---

### LearningToolResult

Cached per-message per-tool result. Fetched once from LLM, cached to avoid repeated calls.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `int` | PK, auto-increment | |
| `message_id` | `int` | required, FK → Message.id | |
| `tool_type` | `enum` | `grammar \| translation \| alternative_phrasing \| word_lookup` | |
| `input_selection` | `str \| None` | nullable | For `word_lookup` only: the selected word/phrase |
| `result` | `str` | required | LLM-generated result text |
| `created_at` | `datetime` | required, UTC | |

**Uniqueness**: `(message_id, tool_type, input_selection)` — one cached result per message per tool per selection. Duplicate requests return cached result without LLM call.

---

### VocabularyItem

Words/phrases saved by the user from inline word lookups (FR-017b). Stored for future flashcard practice.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `int` | PK, auto-increment | |
| `word` | `str` | required | The target-language word or phrase |
| `translation` | `str` | required | Translation in user's native language |
| `target_language` | `str` | required | BCP-47 code |
| `native_language` | `str` | required | BCP-47 code |
| `source_conversation_id` | `int \| None` | nullable, FK → Conversation.id | Context for future reference |
| `saved_at` | `datetime` | required, UTC | |

**Uniqueness**: `(word, target_language)` — saving the same word twice is a no-op (silently ignored or updates `saved_at`).

---

### AppSettings

Singleton row (always `id = 1`). Upserted on first launch with defaults.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `int` | PK, always `1` | Singleton |
| `llm_model` | `str` | required | Default: `"llama3.1"` |
| `target_language` | `str` | required | Default: `"es"` (Spanish) |
| `native_language` | `str` | required | Default: `"en"` (English) |
| `tts_voice` | `str` | required | Piper model name, e.g. `"es_ES-mls-medium"` |
| `suggestion_count` | `int` | required, 1–5 | Default: `1` |
| `updated_at` | `datetime` | required, UTC | |

---

## Validation Rules

| Entity | Rule |
|--------|------|
| Conversation | `ended_at` MUST be NULL when `status = active`; MUST be set when `status = completed` |
| Conversation | `target_language` and `native_language` MUST be different values |
| Message | `input_source` MUST be NULL when `role = assistant` |
| Message | `tts_audio_path` MUST be NULL when `role = user` |
| LearningToolResult | `input_selection` MUST be non-NULL when `tool_type = word_lookup` |
| LearningToolResult | `input_selection` MUST be NULL when `tool_type != word_lookup` |
| VocabularyItem | `word` MUST be non-empty after stripping whitespace |
| AppSettings | `suggestion_count` MUST be between 1 and 5 inclusive |

---

## SQLite Configuration

- **WAL mode**: `PRAGMA journal_mode=WAL` on connection open (enables concurrent reads during writes)
- **Foreign keys**: `PRAGMA foreign_keys=ON`
- **File location**: Configurable via `OPEN_LANGUAGE_DB_PATH` env var; default `~/.open-language/app.db`
