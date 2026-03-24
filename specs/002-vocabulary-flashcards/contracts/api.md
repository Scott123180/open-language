# API Contract: Vocabulary Flashcards (002)

**Branch**: `002-vocabulary-flashcards` | **Date**: 2026-03-22
**Base URL**: `/api` (same as existing app endpoints)
**Router prefix**: `/flashcards`
**Tags**: `flashcards`

---

## Word Library

### `GET /api/flashcards/words`

Returns all saved vocabulary words with filtering support.

**Query Parameters**:
| Param | Type | Description |
|---|---|---|
| `classification` | `string[]` (repeatable) | Filter by status: `not_practiced`, `difficult`, `almost_learned`, `learned` |
| `date_from` | `ISO date` | Words saved on or after this date |
| `date_to` | `ISO date` | Words saved on or before this date |
| `search` | `string` | Free-text match against `word` field |

**Response 200**:
```json
[
  {
    "id": 1,
    "word": "bonjour",
    "translation": "hello",
    "target_language": "fr",
    "native_language": "en",
    "classification": "not_practiced",
    "manual_override": false,
    "saved_at": "2026-03-20T14:00:00Z",
    "source_conversation_id": 5
  }
]
```

---

### `PATCH /api/flashcards/words/{id}/classification`

Manually set a word's classification (manual override).

**Request**:
```json
{ "classification": "difficult" }
```

**Response 200**: Updated `WordListItem` object.
**Response 404**: Word not found.

---

### `DELETE /api/flashcards/words/{id}`

Delete a word from the library. Historical `card_results` are retained as orphaned records.

**Response 204**: No content.
**Response 404**: Word not found.

---

### `GET /api/flashcards/words/{id}/info/{cache_type}`

Return LLM-generated contextual information for a word. Served from cache on subsequent calls.

**Path params**: `cache_type` ∈ `meanings | usage | phrases | similar`

**Response 200**:
```json
{
  "vocabulary_item_id": 1,
  "cache_type": "meanings",
  "content": "bonjour (exclamation): a greeting used when meeting someone...",
  "from_cache": true,
  "generated_at": "2026-03-20T15:00:00Z"
}
```

**Response 503**: LLM unavailable (retry possible; session not affected).

---

### `GET /api/flashcards/tts/{vocabulary_item_id}`

Return TTS audio for a vocabulary word. Generates and caches WAV on first request.

**Response 200**: `audio/wav` binary stream.
**Response 404**: Word not found.

---

## Deck Management

### `POST /api/flashcards/decks`

Generate and persist a new deck.

**Request**:
```json
{
  "name": null,
  "size": 20,
  "word_source": "all",
  "selected_word_ids": [],
  "practice_mode": "recall",
  "algorithm": "mixed_review"
}
```

- `word_source`: `"all"` | `"filtered"` | `"selected"`
- `selected_word_ids`: Only used when `word_source == "selected"`
- `name`: Auto-generated if null (e.g., `"Deck — Mar 22, 2026"`)

**Response 201**:
```json
{
  "id": 1,
  "name": "Deck — Mar 22, 2026",
  "practice_mode": "recall",
  "algorithm": "mixed_review",
  "requested_size": 20,
  "actual_size": 18,
  "size_adjusted": true,
  "created_at": "2026-03-22T10:00:00Z",
  "cards": [
    { "position": 0, "vocabulary_item_id": 3, "word": "bonjour", "fill_blank_sentence": null }
  ]
}
```

---

### `GET /api/flashcards/decks`

List all saved decks.

**Response 200**:
```json
[
  {
    "id": 1,
    "name": "Deck — Mar 22, 2026",
    "practice_mode": "recall",
    "algorithm": "mixed_review",
    "card_count": 18,
    "created_at": "2026-03-22T10:00:00Z",
    "last_practiced_at": "2026-03-22T11:00:00Z",
    "session_count": 2,
    "last_accuracy": 0.78
  }
]
```

---

### `GET /api/flashcards/decks/{id}`

Get full deck detail including all cards.

**Response 200**: Full `DeckDetail` with card list (same shape as `POST /decks` response).
**Response 404**: Deck not found.

---

### `PATCH /api/flashcards/decks/{id}`

Update deck name.

**Request**: `{ "name": "My French Basics" }`
**Response 200**: Updated `DeckSummary`.

---

### `POST /api/flashcards/decks/{id}/refresh`

Refresh deck: replace Learned words with new eligible words using the original algorithm.

**Response 200**: Updated `DeckDetail` with new card composition.
**Response 404**: Deck not found.

---

### `DELETE /api/flashcards/decks/{id}`

Delete a deck. Session history is retained as orphaned records.

**Response 204**: No content.
**Response 404**: Deck not found.

---

## Practice Sessions

### `POST /api/flashcards/sessions`

Start a new practice session for a deck.

**Request**: `{ "deck_id": 1 }`

**Response 201**:
```json
{
  "id": 42,
  "deck_id": 1,
  "practice_mode": "recall",
  "total_cards": 18,
  "started_at": "2026-03-22T11:00:00Z"
}
```

---

### `POST /api/flashcards/sessions/{id}/cards/{position}`

Record the result for a single card.

**Request**:
```json
{
  "rating": "knew_it",
  "response_type": "typed",
  "user_response": "hello"
}
```

- `rating`: `"knew_it"` | `"guessed"` | `"didnt_know"`
- `response_type`: `"spoken"` | `"typed"` | `null` (flip without response)

**Response 200**: `{ "cards_reviewed": 5 }`
**Response 404**: Session or card position not found.

---

### `POST /api/flashcards/sessions/{id}/end`

End a session (complete or early exit). Triggers silent classification recalculation.

**Request**: `{ "completed": true }`

**Response 200**:
```json
{
  "session_id": 42,
  "completed": true,
  "cards_reviewed": 18,
  "total_cards": 18,
  "knew_it_count": 12,
  "guessed_count": 4,
  "didnt_know_count": 2,
  "duration_seconds": 480,
  "current_streak": 5
}
```

---

### `GET /api/flashcards/sessions/{id}/summary`

Get full session summary (includes words needing work).

**Response 200**:
```json
{
  "session_id": 42,
  "completed": true,
  "cards_reviewed": 18,
  "total_cards": 18,
  "knew_it_count": 12,
  "guessed_count": 4,
  "didnt_know_count": 2,
  "duration_seconds": 480,
  "current_streak": 5,
  "words_needing_work": [
    { "id": 7, "word": "merci", "translation": "thank you", "rating": "didnt_know" }
  ]
}
```

---

### `GET /api/flashcards/sessions/{id}/encouragement`

Get LLM-generated encouragement message based on session performance.

**Response 200**:
```json
{ "message": "Great work! You nailed 12 out of 18 words — keep it up!" }
```

**Response 503**: LLM unavailable (frontend shows a default message).

---

### `POST /api/flashcards/sessions/{id}/missed-deck`

Generate a mini-deck containing only the words rated `didnt_know` in this session.

**Response 201**: `DeckDetail` for the new mini-deck.
**Response 400**: No `didnt_know` words in this session.

---

## Analytics

### `GET /api/flashcards/analytics`

Return all analytics data in a single response.

**Query Parameters**:
| Param | Type | Default | Description |
|---|---|---|---|
| `range` | `string` | `"7d"` | `"7d"` \| `"30d"` \| `"all"` |

**Response 200**:
```json
{
  "at_a_glance": {
    "total_words": 142,
    "words_learned": 38,
    "current_streak": 5,
    "sessions_this_week": 3
  },
  "accuracy_trend": [
    { "session_id": 40, "date": "2026-03-20", "accuracy": 0.72 },
    { "session_id": 42, "date": "2026-03-22", "accuracy": 0.78 }
  ],
  "daily_activity": [
    { "date": "2026-03-20", "cards_reviewed": 20 },
    { "date": "2026-03-21", "cards_reviewed": 0 },
    { "date": "2026-03-22", "cards_reviewed": 18 }
  ],
  "classification_over_time": [
    { "date": "2026-03-20", "not_practiced": 90, "difficult": 20, "almost_learned": 15, "learned": 17 }
  ],
  "classification_now": {
    "not_practiced": 88, "difficult": 18, "almost_learned": 18, "learned": 18
  },
  "hardest_words": [
    { "id": 7, "word": "merci", "encounters": 8, "success_rate": 0.25 }
  ],
  "recently_learned": [
    { "id": 12, "word": "bonjour", "learned_at": "2026-03-22T10:00:00Z" }
  ],
  "mode_performance": [
    { "mode": "recall", "accuracy": 0.82 },
    { "mode": "listen", "accuracy": 0.68 },
    { "mode": "produce", "accuracy": 0.55 },
    { "mode": "fill_blank", "accuracy": 0.73 }
  ]
}
```

---

## Error Response Format

All error responses follow the existing FastAPI convention:

```json
{ "detail": "Human-readable error message telling the user what to do." }
```
