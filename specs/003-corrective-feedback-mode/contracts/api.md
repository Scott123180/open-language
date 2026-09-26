# Phase 1 API Contract: Corrective Feedback Mode

**Branch**: `003-corrective-feedback-mode` | **Date**: 2026-08-25 | **Plan**: [../plan.md](../plan.md)

Three kinds of interface change: HTTP endpoints, the SSE stream on the conversation turn, and two
internal Python ABCs that are contracts in their own right (Constitution V — extension points
declared as abstractions before implementations).

Everything here is additive. No existing field is removed or changes type, so an Off-mode client
that ignores the new fields behaves exactly as it does today (FR-002, SC-002).

---

## 1. HTTP endpoints

### 1.1 `GET /api/settings` — MODIFIED

`SettingsResponse` gains one field.

```jsonc
{
  "llm_model": "llama3.1",
  "target_language": "es",
  "native_language": "en",
  "tts_voice": "es_ES-davefx-medium",
  "suggestion_count": 1,
  "whisper_model": "base",
  "correction_mode": "off",        // NEW — "off" | "gentle" | "strict"
  "updated_at": "2026-08-25T10:00:00Z"
}
```

### 1.2 `PUT /api/settings` — MODIFIED

`UpdateSettingsRequest` gains `correction_mode: str | None`, validated
`pattern="^(off|gentle|strict)$"` (same style as `whisper_model`). Omitting it leaves the stored
value untouched; an invalid value returns `422` with FastAPI's standard validation body.

The Settings screen renders the control with a hint stating that Gentle and Strict add a
language-model pass per message, that this can cost several seconds per turn without a GPU, and that
a check taking too long is skipped so the conversation continues (research.md R11). The hint is
static client-side copy — the API does not report host capability.

Responds with the full `SettingsResponse`, which is what lets the Settings screen confirm the change
took effect (FR-005).

### 1.3 `POST /api/audio/transcribe` — MODIFIED

Response gains two fields (FR-010):

```jsonc
{
  "text": "Yo tengo veinte años",
  "detected_language": "es",
  "confidence": 0.82,           // NEW — 0.0–1.0, or null when there is no confidence information
  "is_low_confidence": false    // NEW — confidence != null && confidence < threshold
}
```

`confidence` distinguishes three states, and clients must not collapse them:

| Value | Meaning |
|---|---|
| `null` | no confidence information (no segments at all) — **not** low confidence |
| `0.0` | text present but every segment read as silence — hallucination-on-silence, low confidence |
| `0.0 < x < 1.0` | the aggregated score (research.md R1) |

The client forwards `confidence` to the next call as `transcription_confidence`, including `0.0`.
Existing error behaviour is unchanged: `400` on empty audio or empty transcript, `422` on STT
failure.

### 1.4 `POST /api/chat/{conversation_id}/message` — MODIFIED

Request gains one optional field:

```jsonc
{
  "content": "Yo tener veinte años",
  "input_source": "voice",
  "transcription_confidence": 0.41   // NEW — optional, 0.0–1.0; ignored when input_source is "keyboard"
}
```

Out-of-range values are rejected with `422` (`ge=0.0, le=1.0`). Omitted or `null` means "no
confidence information", which is never treated as low confidence (FR-010a applies only to a value
below the threshold). The SSE response is specified in §2.

### 1.5 `GET /api/corrections/conversations/{conversation_id}` — NEW

Replays everything the chat screen needs to rebuild a conversation's feedback after a reload
(FR-022, FR-029).

**200**

```jsonc
{
  "conversation_id": 42,
  "awaiting_retry": true,                     // derived; see data-model.md
  "awaiting_clarification": false,
  "consecutive_corrected_attempts": 1,
  "feedback": [
    {
      "id": 7,
      "message_id": 118,
      "kind": "correction",                   // "correction" | "repeat_request"
      "category": "conjugation",              // null for repeat_request
      "error_fragment": "Yo tener",           // null for repeat_request
      "corrected_text": "Yo tengo veinte años", // null for repeat_request
      "explanation": "\"Tener\" needs to be conjugated: with \"yo\" it becomes \"tengo\".",
      "mode": "strict",
      "rank": 0,
      "created_at": "2026-08-25T10:04:11Z"
    }
  ]
}
```

- `feedback` contains only rows the client renders — `mode="strict"` corrections and repeat requests.
  Gentle corrections are persisted but not returned, because in Gentle the correction *is* the
  character's reply ([../plan.md](../plan.md) → Spec interpretations #1).
- Ordered by `message_id`, then `rank`.
- Empty `feedback` with all-zero state is the normal response for a conversation that has never been
  corrected, including every conversation in Off mode.

**404** — `{"detail": "Conversation not found"}`

---

## 2. SSE contract: the conversation turn

`POST /api/chat/{id}/message` streams `text/event-stream`. Existing frames are unchanged.

### 2.1 Off mode — byte-identical to today (SC-002)

```text
data: {"event": "user_message_saved", "message_id": 118}
data: {"token": "¡Hola"}
data: {"token": "!"}
data: {"done": true, "message_id": 119}
```

No `feedback` frame is emitted when there is no feedback, so the Off-mode byte stream is exactly what
it was before this feature. This is asserted directly by an integration test.

### 2.2 New frame: `feedback`

Emitted **only** when the turn produced at least one note, immediately after `user_message_saved` and
before any `token` frame.

```jsonc
data: {
  "event": "feedback",
  "message_id": 118,          // the learner's message the notes attach to
  "awaiting_retry": true,     // true ⇒ the scenario is paused for a retry (FR-016)
  "notes": [ /* same object shape as §1.5 "feedback" entries */ ]
}
```

### 2.3 Gentle mode — one turn, correction inside the reply

Identical to Off from the client's point of view. The recast is in the reply tokens, so no `feedback`
frame is emitted (FR-012, FR-013) and nothing pauses.

```text
data: {"event": "user_message_saved", "message_id": 118}
data: {"token": "Ah, "}
data: {"token": "tienes "}
data: {"token": "veinte años"}
data: {"done": true, "message_id": 119}
```

### 2.4 Strict mode, message flagged — correction is the whole turn

```text
data: {"event": "user_message_saved", "message_id": 118}
data: {"event": "feedback", "message_id": 118, "awaiting_retry": true, "notes": [ … ]}
data: {"done": true, "message_id": null}
```

**No `token` frames and no assistant message row.** FR-016 forbids a character reply for a flagged
turn "whether shown, withheld, or stored", so none is generated.

`message_id: null` on `done` is what makes SC-005 structural: the client only requests
`GET /api/audio/tts/{id}` for a non-null assistant `message_id`, so there is nothing to speak. This
is the FR-020 guarantee — correction text has no message id and never enters `messages.content`.

### 2.5 Strict mode, low-confidence message — repeat request

```text
data: {"event": "user_message_saved", "message_id": 118}
data: {"event": "feedback", "message_id": 118, "awaiting_retry": true,
       "notes": [{"kind": "repeat_request", "explanation": "I didn't quite catch that — could you say it again?", …}]}
data: {"done": true, "message_id": null}
```

If the repeat is *also* low-confidence, the conversation proceeds as §2.1 with no second request
(FR-027) — a bad microphone cannot stall a scenario.

### 2.6 Evaluation failure — indistinguishable from Off (FR-026)

On timeout, `LLMError`, or unparseable output, the stream is exactly §2.1: reply delivered, no
`feedback` frame, no error frame. The failure is logged server-side at `warning`, never surfaced to
the learner.

### 2.7 Client parsing rules

`readSseStream` in [api.ts](../../../frontend/src/services/api.ts) already routes `parsed.event` to
an `onEvent` callback, so `feedback` needs no change to the reader — only a new branch in
`streamChatMessage`:

| Frame | Client action |
|---|---|
| *(request sent)* | when `correction_mode !== 'off'`, enter `checking` and show the indicator (R11). **No assistant placeholder is appended.** In Off mode, unchanged from today |
| `event: "user_message_saved"` | unchanged |
| `event: "feedback"` | attach `notes` to that message; if `awaiting_retry`, switch the composer to retry mode |
| first `token` | **create** the assistant bubble here, enter `replying`, clear the indicator |
| subsequent `token` | append — unchanged |
| `done` with `message_id: number` | finalize the assistant bubble, request TTS — unchanged |
| `done` with `message_id: null` | clear the indicator and end the turn. There is no placeholder to remove, because none was created |
| `error` | unchanged |

Deferring assistant-bubble creation to the first token is what keeps a flagged Strict turn free of a
phantom character bubble that appears during evaluation and then has to be withdrawn. It also means
the no-reply turn needs no teardown path at all.

---

## 3. Internal Python contracts

Declared as ABCs before any implementation. Each gets a contract test in
`backend/tests/contract/service_interfaces/`.

### 3.1 `StructuredLLMProvider` — NEW, in `app/services/llm/base.py`

```python
class StructuredLLMProvider(ABC):
    @abstractmethod
    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        """Chat with output constrained to a JSON Schema. Returns raw JSON text.

        Raises LLMError on failure.
        """
```

A **separate** ABC rather than a method on `LLMProvider`, so streaming consumers are not forced to
depend on a JSON method they never call (ISP — research.md R4). `OllamaLLMProvider` implements both
and passes `format=schema` to `ollama.chat`.

*Contract test*: a stub returns schema-valid JSON; a stub that raises must raise `LLMError`.

### 3.2 `CorrectionEvaluator` — NEW, in `app/corrections/services/evaluator.py`

```python
class CorrectionEvaluator(ABC):
    @abstractmethod
    def evaluate(self, request: EvaluationRequest) -> tuple[CorrectionFinding, ...]:
        """Return 0..MAX_CORRECTIONS_PER_MESSAGE findings, ordered by impact.

        Never raises: every failure returns an empty tuple (FR-026).
        """
```

`EvaluationRequest` bundles learner text, target language, native language, and the preceding
character line — keeping the signature to one argument (clean-code rule: prefer 0–2 arguments).

*Contract*: never raises; never returns more than the cap; returns empty for a message under
`MIN_WORDS_FOR_EVALUATION` words.

### 3.3 `CorrectionStrategy` — NEW, in `app/corrections/services/strategies.py`

```python
class CorrectionStrategy(ABC):
    @abstractmethod
    async def plan_turn(self, context: TurnContext) -> TurnPlan:
        """Decide what this mode does with this learner message."""
```

Implementations: `OffCorrectionStrategy`, `GentleCorrectionStrategy`, `StrictCorrectionStrategy`.
`build_correction_strategy(mode, …)` in `app/corrections/__init__.py` is the only place a mode string
is turned into behaviour; no consumer branches on the mode again (Constitution V).

*Contract*: all three return a `TurnPlan`; `Off` returns
`TurnPlan((), generate_reply=True, reply_prompt_suffix=None)` without any I/O — no LLM call, no query
(SC-002); only `Strict` may return `generate_reply=False`.

### 3.4 `CorrectionStorageProvider` — NEW, in `app/corrections/services/storage.py`

```python
class CorrectionStorageProvider(ABC):
    def save_feedback(self, message_id: int, drafts: Sequence[FeedbackDraft]) -> list[FeedbackRecord]: ...
    def list_feedback(self, conversation_id: int) -> list[FeedbackRecord]: ...
    def get_pause_state(self, conversation_id: int) -> PauseSnapshot: ...
    def set_pause_state(self, conversation_id: int, attempts: int, awaiting_clarification: bool) -> PauseSnapshot: ...
```

Its own ABC rather than four more methods on the core `StorageProvider`, so existing consumers are
not made to depend on correction persistence (ISP, matching the `FlashcardStorageProvider` precedent
from feature 002).

*Contract*: `get_pause_state` on an unknown conversation returns a zeroed snapshot rather than
raising or creating a row; `save_feedback` is insert-only; `list_feedback` is ordered by
`(message_id, rank)`.

### 3.5 `TranscriptionResult` — MODIFIED, in `app/services/stt/base.py`

```python
@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    detected_language: str | None
    confidence: float | None = None   # NEW — defaulted, so every existing STTProvider stays valid
```

The default is what preserves LSP: the existing contract test and `StubSTTProvider` continue to pass
unmodified.

---

## 4. Frontend API surface (`frontend/src/services/api.ts`)

```ts
// MODIFIED
export interface AppSettings { /* … */ correction_mode: 'off' | 'gentle' | 'strict' }

// NEW
export type FeedbackKind = 'correction' | 'repeat_request'
export interface FeedbackNoteData {
  id: number
  message_id: number
  kind: FeedbackKind
  category: string | null
  error_fragment: string | null
  corrected_text: string | null
  explanation: string
  mode: 'gentle' | 'strict'
  rank: number
  created_at: string
}
export interface ConversationFeedback {
  conversation_id: number
  awaiting_retry: boolean
  awaiting_clarification: boolean
  consecutive_corrected_attempts: number
  feedback: FeedbackNoteData[]
}
export const getConversationFeedback: (conversationId: number) => Promise<ConversationFeedback>

// MODIFIED — returns confidence
export const transcribeAudio: (blob: Blob, language?: string) =>
  Promise<{ text: string; detected_language: string | null; confidence: number | null; is_low_confidence: boolean }>

// MODIFIED — accepts confidence, reports feedback, and tolerates a null reply id
export const streamChatMessage: (
  conversationId: number,
  content: string,
  inputSource: 'voice' | 'keyboard',
  onUserSaved: (messageId: number) => void,
  onToken: (t: string) => void,
  onDone: (data: { message_id: number | null }) => void,   // ← null on a flagged Strict turn
  onError: (e: string) => void,
  onFeedback?: (data: { message_id: number; awaiting_retry: boolean; notes: FeedbackNoteData[] }) => void,
  transcriptionConfidence?: number,
) => Promise<void>
```

`onFeedback` and `transcriptionConfidence` are appended as optional parameters so existing call sites
compile unchanged. `onDone`'s `message_id` widening to `number | null` is the one breaking type
change, and it is deliberate: it forces every call site to handle the no-reply turn rather than
silently requesting TTS for `null`.
