# API Contracts: Speak — Role-Play Conversation Chat

**Branch**: `001-speak-roleplay-chat` | **Date**: 2026-03-17
**Base URL**: `/api` (all routes prefixed; served by FastAPI)
**Auth**: None (local-only app)
**Content-Type default**: `application/json` unless noted

---

## Scenarios

### `GET /api/scenarios/current`

Returns the currently displayed scenario (randomly selected, not the last shown).

**Response 200**:
```json
{
  "id": "buy-train-ticket",
  "title": "Buying a Train Ticket",
  "description": "You need to purchase a ticket at the station counter."
}
```

### `GET /api/scenarios/next`

Returns a different scenario from the current one (for Refresh button). The backend tracks the last-shown scenario in memory to enforce no-consecutive-repeat.

**Response 200**: Same shape as `/scenarios/current`.

---

## Conversations

### `POST /api/conversations`

Start a new conversation for the given scenario.

**Request body**:
```json
{
  "scenario_id": "buy-train-ticket"
}
```

**Response 201**:
```json
{
  "conversation_id": 42,
  "scenario_id": "buy-train-ticket",
  "scenario_title": "Buying a Train Ticket",
  "target_language": "es",
  "native_language": "en",
  "status": "active",
  "started_at": "2026-03-17T10:00:00Z"
}
```

**Errors**: `422` if `scenario_id` unknown.

---

### `GET /api/conversations`

List all conversations in reverse chronological order (history screen).

**Response 200**:
```json
[
  {
    "conversation_id": 42,
    "scenario_title": "Buying a Train Ticket",
    "status": "completed",
    "started_at": "2026-03-17T10:00:00Z",
    "ended_at": "2026-03-17T10:15:00Z"
  }
]
```

---

### `GET /api/conversations/{conversation_id}/messages`

Retrieve all messages in a conversation (ordered by `created_at ASC`).

**Response 200**:
```json
[
  {
    "message_id": 1,
    "role": "assistant",
    "content": "Buenas tardes, ¿en qué le puedo ayudar?",
    "input_source": null,
    "created_at": "2026-03-17T10:00:01Z"
  },
  {
    "message_id": 2,
    "role": "user",
    "content": "Hola, quisiera un billete a Barcelona.",
    "input_source": "voice",
    "created_at": "2026-03-17T10:00:45Z"
  }
]
```

---

### `PATCH /api/conversations/{conversation_id}`

End a conversation (sets status → `completed`).

**Request body**:
```json
{ "status": "completed" }
```

**Response 200**: Updated conversation object (same shape as POST response).

---

## Chat (AI Turn)

### `POST /api/chat/{conversation_id}/message` — SSE Stream

Send a user message and stream the AI reply as Server-Sent Events.

**Request body**:
```json
{
  "content": "Hola, quisiera un billete a Barcelona.",
  "input_source": "keyboard"
}
```

**Response**: `Content-Type: text/event-stream`

**SSE event stream**:
```
data: {"type": "user_message_saved", "message_id": 2}

data: {"type": "token", "content": "Claro"}

data: {"type": "token", "content": ", ¿para"}

data: {"type": "token", "content": " qué fecha?"}

data: {"type": "done", "message_id": 3, "full_content": "Claro, ¿para qué fecha?"}
```

- `user_message_saved`: confirms user message persisted (ID returned for UI association)
- `token`: individual LLM output token to append to the streaming bubble
- `done`: full assistant message persisted; includes `message_id` for subsequent tool calls
- `error`: `{"type": "error", "message": "..."}` — stream closes; client shows retry UI

**Notes**: Client closes the connection after receiving `done`. TTS is triggered client-side by calling `GET /api/audio/tts/{message_id}` after `done`.

---

### `POST /api/chat/{conversation_id}/open`

Generate and stream the AI's opening message for a new conversation. Same SSE format as `/message`. No request body needed (scenario context loaded from conversation record).

---

## Audio

### `POST /api/audio/transcribe`

Transcribe a recorded voice message.

**Request**: `Content-Type: multipart/form-data`
- `audio`: audio file blob (WebM/Opus preferred; WAV accepted)

**Response 200**:
```json
{
  "text": "Hola, quisiera un billete a Barcelona.",
  "detected_language": "es"
}
```

**Response 400**: `{"detail": "Audio too short or silent"}` if transcription yields empty text.

---

### `GET /api/audio/tts/{message_id}`

Synthesize (or return cached) TTS audio for an assistant message.

**Response 200**: `Content-Type: audio/wav` — raw WAV bytes.
**Response 404**: Message not found or is a user message.

**Notes**: Response is cached to disk after first synthesis. Subsequent calls return cached file. Slow playback is handled client-side via `<audio>.playbackRate`.

---

## Learning Tools

All learning tool endpoints are idempotent — repeated calls return the cached result if one exists.

### `POST /api/learning/grammar`

**Request**:
```json
{ "message_id": 2 }
```

**Response 200**:
```json
{
  "message_id": 2,
  "tool_type": "grammar",
  "result": "Your sentence is mostly correct. Consider using 'quisiera' instead of 'quiero' for a more polite register.",
  "cached": false
}
```

---

### `POST /api/learning/translate`

**Request**:
```json
{ "message_id": 2 }
```

**Response 200**:
```json
{
  "message_id": 2,
  "tool_type": "translation",
  "result": "Hello, I'd like a ticket to Barcelona.",
  "cached": false
}
```

---

### `POST /api/learning/phrasing`

**Request**:
```json
{ "message_id": 2 }
```

**Response 200**:
```json
{
  "message_id": 2,
  "tool_type": "alternative_phrasing",
  "result": "Alternative: 'Me gustaría comprar un billete para Barcelona, por favor.'",
  "cached": false
}
```

---

### `POST /api/learning/word-lookup`

**Request**:
```json
{
  "message_id": 2,
  "selection": "quisiera"
}
```

**Response 200**:
```json
{
  "message_id": 2,
  "tool_type": "word_lookup",
  "selection": "quisiera",
  "result": "quisiera — I would like (subjunctive of 'querer'; polite request form)",
  "cached": false
}
```

---

## Vocabulary

### `POST /api/vocabulary`

Save a word/phrase from a word-lookup result.

**Request**:
```json
{
  "word": "quisiera",
  "translation": "I would like",
  "source_conversation_id": 42
}
```

**Response 201**:
```json
{
  "vocabulary_item_id": 7,
  "word": "quisiera",
  "translation": "I would like",
  "saved_at": "2026-03-17T10:01:00Z"
}
```

**Response 200** (already exists — idempotent): Same shape, `saved_at` updated.

---

### `GET /api/vocabulary`

List all saved vocabulary items, most recently saved first.

**Response 200**:
```json
[
  {
    "vocabulary_item_id": 7,
    "word": "quisiera",
    "translation": "I would like",
    "target_language": "es",
    "saved_at": "2026-03-17T10:01:00Z"
  }
]
```

---

## Assistance Features

### `POST /api/chat/{conversation_id}/suggestions`

Generate suggested reply(ies) for the current conversation state. Count determined by `AppSettings.suggestion_count`.

**Response 200**:
```json
{
  "suggestions": [
    "Para el próximo viernes, por favor."
  ]
}
```

---

### `POST /api/chat/helper` — SSE Stream

Send a message to the expression-helper side conversation. Separate from main role-play context. Returns SSE stream identical to `/chat/{conversation_id}/message`.

**Request body**:
```json
{
  "content": "How do I say 'I need a window seat'?",
  "helper_session_id": "abc123"
}
```

`helper_session_id`: Client-generated UUID maintained for the session duration. Server keeps helper conversation history in memory (not persisted).

---

## Settings

### `GET /api/settings`

**Response 200**:
```json
{
  "llm_model": "llama3.1",
  "target_language": "es",
  "native_language": "en",
  "tts_voice": "es_ES-mls-medium",
  "suggestion_count": 1
}
```

### `PUT /api/settings`

**Request body**: Any subset of the settings fields above.

**Response 200**: Full updated settings object.

---

## Error Shape (all endpoints)

```json
{
  "detail": "Human-readable error message telling the user what to do next."
}
```

HTTP status codes used: `200`, `201`, `400`, `404`, `422`, `500`.
`500` errors include a `detail` field with a plain-language explanation; stack traces are never exposed.
