# Phase 0 Research: Corrective Feedback Mode

**Branch**: `003-corrective-feedback-mode` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

This document resolves every NEEDS CLARIFICATION raised in [plan.md](plan.md) Technical Context.
Each item follows the Decision / Rationale / Alternatives format.

---

## R1 — Transcription confidence: what value, and what threshold?

**Requirement**: FR-010 mandates a confidence value per spoken message and a named threshold below
which the message is classified low-confidence. The spec explicitly defers the threshold value to
planning.

### Is a newer faster-whisper available?

Checked against PyPI: **1.2.1 is the latest release** and is what is already installed in
`backend/.venv`. The full available list tops out at 1.2.1 (previous: 1.2.0, 1.1.1, 1.1.0, 1.0.x).
So there is no upgrade that would hand us an overall confidence — aggregating per-segment signals is
the only route, not a workaround for being out of date.

**What 1.2.1 exposes**: `TranscriptionInfo` carries `language`, `language_probability`, `duration`,
`duration_after_vad`, `all_language_probs`, `transcription_options`, `vad_options` — no overall
confidence. Per-segment signals live on `Segment`: `avg_logprob` (mean log-probability per token),
`no_speech_prob`, `compression_ratio`, `temperature`, `tokens`, `start`, `end`, `text`.

### Decision: a three-step aggregate over content-bearing segments

`WhisperSTTProvider.transcribe()` returns one scalar `confidence: float | None` on
`TranscriptionResult` (defaulted to `None`, so the frozen dataclass and its existing contract test
stay valid).

**Step 1 — keep only segments that carry speech.** A segment is dropped when any of these holds:

| Drop when | Why |
|---|---|
| `segment.text.strip()` is empty | nothing was transcribed from this range |
| `segment.end - segment.start <= 0` | zero or negative duration |
| `segment.no_speech_prob > NO_SPEECH_PROB_THRESHOLD` (0.6) | Whisper's own judgement that the range is silence |

**Step 2 — catch the repetition loop before averaging.** If any retained segment has
`compression_ratio > COMPRESSION_RATIO_THRESHOLD` (2.4), the whole message is forced to
low-confidence regardless of what step 3 computes. A repetition loop ("no no no no no…") has a
*high* `avg_logprob` — the model is extremely confident in nonsense — so averaging alone would rate
it as excellent. This is precisely the FR-010a failure mode: inventing a correction for words the
learner never said.

**Step 3 — aggregate, weighting by token count.**

```
confidence = exp( Σ(avg_logprob_i × n_tokens_i) / Σ(n_tokens_i) )       over retained segments
where n_tokens_i = len(segment.tokens)
```

`avg_logprob` is already a *per-token* mean, so recombining per-segment means into a correct overall
per-token mean requires weighting by the token count each mean was taken over. `Segment.tokens` is
exposed in 1.2.1, so the exact weight is available. Exponentiating maps the result back into 0–1
probability space, which is easy to threshold and easy to assert on in tests.

**Threshold**: `LOW_CONFIDENCE_THRESHOLD = 0.55`, configurable via
`app.config.Settings.low_confidence_threshold`. A message is low-confidence when
`confidence is not None and confidence < threshold`.

### The named constants, and where their values come from

Every threshold is a published Whisper value rather than a number invented here:

| Constant | Value | Provenance |
|---|---|---|
| `NO_SPEECH_PROB_THRESHOLD` | 0.6 | Whisper's own `no_speech_threshold` default |
| `COMPRESSION_RATIO_THRESHOLD` | 2.4 | Whisper's own `compression_ratio_threshold` default |
| `LOW_CONFIDENCE_THRESHOLD` | 0.55 | see below |

0.55 sits deliberately between two reference points: Whisper's decoding-failure threshold is
`log_prob_threshold = -1.0` → `exp(-1.0) ≈ 0.37`, and clean speech in practice lands at `avg_logprob`
of −0.1 to −0.3 → 0.74–0.90. 0.55 corresponds to `avg_logprob ≈ −0.60` — well clear of clean speech,
well above outright decode failure.

**One deliberate deviation from Whisper's own logic**: Whisper declares a segment silent only when
`no_speech_prob > 0.6` **and** `avg_logprob < -1.0`. Step 1 uses the `no_speech_prob` half alone.
The conjunction would *retain* the most dangerous segment there is — silence transcribed confidently
into text — and let its high `avg_logprob` inflate the score. Filtering on `no_speech_prob` alone
routes that case into the degenerate rule below, where it belongs.

### Degenerate and edge cases

| Case | What is observed | Result |
|---|---|---|
| No segments at all, no text | empty transcription | `confidence = None`; already rejected upstream by the existing 400 on empty text |
| **Text present, but every segment filtered as silence** | classic hallucination-on-silence ("Thank you for watching") | `confidence = 0.0` → **low-confidence**. Text from ranges Whisper calls silence is not trustworthy |
| `Σ n_tokens == 0` across retained segments | no tokens to weight | `confidence = None` |
| Leading/trailing silence around real speech | some segments dropped in step 1 | remaining speech decides the score — the point of step 1 |
| Repetition loop | `compression_ratio > 2.4` | forced low-confidence (step 2) |
| Mumbling, noisy room | low `avg_logprob` throughout | confidence < 0.55 → low-confidence |
| Very short utterance ("sí") | one short segment | scored normally, but `MIN_WORDS_FOR_EVALUATION` (R6) skips it before any LLM call anyway |
| Learner speaks their native language | confidence is normal — they said it clearly | not a confidence problem; the roleplay prompt owns this case |
| **Typed message** | no transcription at all | `confidence = None` → **never** low-confidence. FR-010a must never gate typed input |
| Corrupt or zero-length audio | `STTError` | existing 422 path, unchanged |

### Two signals deliberately not used

- **`segment.temperature`** — a value above 0.0 means greedy decoding failed Whisper's own quality
  checks and it retried with sampling, which is a genuine quality warning. It is not used as a gate
  because the resampled output is often fine, and gating on it would suppress corrections on
  perfectly good speech. It is logged at `debug` so it is available when tuning, rather than silently
  discarded.
- **`info.language_probability`** — unusable here by construction. [audio.py](../../backend/app/routers/audio.py)
  always passes a `language_hint` (the frontend sends the target language), which makes
  faster-whisper skip detection and report 1.0 unconditionally. Recording this so it is not
  mistaken for an available signal later.

**Alternatives considered**:
- *Duration weighting instead of token weighting* — what an earlier draft of this plan used. It is
  defensible but statistically wrong: `avg_logprob` is normalised per token, not per second, so
  duration weighting distorts the mean for segments with unusual speech rate. `Segment.tokens` makes
  the correct weight free.
- *Unweighted mean across segments* — simplest, and wrong in the same way, more severely.
- *`no_speech_prob` as the confidence value itself* — measures whether speech is present, not whether
  the words were heard right. It would miss the exact failure FR-010a guards against.
- *Word-level probabilities (`word_timestamps=True`)* — finer grained, but roughly doubles
  transcription time, and the spec needs one number per message.
- *A second decode pass at a different temperature, comparing outputs* — most accurate, far too slow
  for a per-turn budget.

---

## R2 — Where does confidence enter the conversation turn?

**Finding**: transcription and message-sending are two separate round trips today.
`POST /audio/transcribe` ([audio.py](../../backend/app/routers/audio.py)) returns text to the
browser, which then posts that text to `POST /chat/{id}/message`
([chat.py](../../backend/app/routers/chat.py)). The backend never learns that a given message came
from a given transcription.

**Decision**: the confidence value round-trips through the client. `/audio/transcribe` adds
`confidence` and `is_low_confidence` to its response; `ChatMessageRequest` gains
`transcription_confidence: float | None = None`, which the frontend forwards. The backend persists
both the value and the resulting classification on the message row.

**Rationale**: Keeps the existing two-endpoint split intact — no server-side session state tying a
transcription to a later message, no change to the recording flow. The client already forwards
`input_source`; confidence is the same kind of provenance metadata travelling the same path.

**Trust note**: the value is client-supplied and therefore spoofable. It is used only to *suppress*
correction, never to grant access to anything, and this is a single-user local application. The
backend still validates the range (0.0–1.0) and ignores a confidence supplied with
`input_source="keyboard"`.

**Alternatives considered**:
- *Server-side transcription cache keyed by a token* — adds cross-request state and a cache-eviction
  problem to buy nothing in a local single-user app.
- *Fusing transcription into `/chat/{id}/message`* — a much larger change to the recording flow and
  to `useRecorder`, out of proportion to this feature.

---

## R3 — Detecting errors: one LLM call per turn, or two?

**Requirement**: FR-006 (evaluate every learner message when mode ≠ Off), FR-016 (Strict produces no
character reply at all for a flagged turn), FR-012 (Gentle weaves the correction into the reply),
SC-004 (perceived-wait budget).

**Decision — confirmed by the user**: evaluate **before** generating, in both Gentle and Strict. A
single `CorrectionEvaluator` returns zero to two structured corrections; a `CorrectionStrategy` per
mode decides what happens next.

| Mode | Evaluator call | Reply generated? | Corrections used for |
|---|---|---|---|
| Off | none | yes | — |
| Gentle | yes | yes, same turn | appended as a recast instruction to the roleplay system prompt |
| Strict | yes | **no** when corrections found | rendered as the turn's only output |

**Rationale**: evaluate-first is the only ordering that can satisfy FR-016 — the decision not to
generate a reply must be made before any tokens are produced, or a withheld reply exists, which
FR-016 forbids ("whether shown, withheld, or stored"). Reusing the same evaluator for Gentle keeps
one detection code path, so SC-003's benchmark measures the behaviour both modes actually use, and
keeps FR-006 literally true.

**The cost, and how it is paid**: Gentle now runs two sequential LLM calls per turn. The evaluation
call emits at most a few dozen JSON tokens, so on a GPU-accelerated Ollama host it costs roughly
1–3 s. On a CPU-only host, an 8B model at 5–10 tok/s can take 8–20 s, which no amount of prompt
tuning fixes. Rather than pretend a single number covers both, the design pays this cost three ways:

1. **A relaxed, tiered budget.** SC-004 now asks for ≤ 4 s on a GPU host and, on any host, a hard
   timeout after which the turn completes uncorrected. See R5.
2. **A visible checking indicator**, so the wait is legible rather than a frozen screen. See R11.
3. **An explicit warning on the Settings screen**, so a CPU-only learner chooses the trade knowingly
   rather than discovering it. See R11.

*Superseded*: an earlier draft of this plan proposed prompt-only Gentle (one call, no evaluation) as
a fallback if the 2 s budget could not be met. That is no longer the fallback — the budget moved
instead, because dropping evaluation would contradict FR-006 and produce no correction record.

**Alternatives considered**:
- *Prompt-only Gentle* — one call and fastest, but no `Correction` record is produced, contradicting
  FR-006 and the Key Entities description of a correction carrying "the mode under which it was
  produced". Rejected, not deferred.
- *Evaluate after replying, then retract the reply in Strict* — a generated reply would exist, which
  FR-016 explicitly rules out.
- *Run evaluation and reply generation concurrently* — impossible for Strict (the reply must not be
  generated) and wasteful for Gentle (the reply prompt depends on the evaluation result).

---

## R4 — Getting structured output out of a local Ollama model

**Finding**: the installed `ollama` client is 0.6.1, which supports `format=<JSON Schema dict>` on
`ollama.chat` for constrained decoding. The existing `LLMProvider` ABC exposes only `chat_stream`
and `chat`, neither of which can pass `format`.

**Decision**: add a **separate narrow ABC** `StructuredLLMProvider` in
[llm/base.py](../../backend/app/services/llm/base.py) with a single method
`chat_json(messages, schema) -> str`. `OllamaLLMProvider` implements both ABCs;
`app/services/factory.py` gains `get_structured_llm()`. The corrections module depends on
`StructuredLLMProvider` only.

**Rationale**: Interface Segregation — streaming consumers (the roleplay turn, the expression
helper) are not forced to depend on a JSON method they never call, and the corrections module is not
forced to depend on streaming. Constrained decoding raises parse reliability enough to matter for
SC-003 (≥ 8/10 detection), because llama3.1 left to itself will wrap JSON in prose or code fences
often enough to lose correct detections to parse failures.

The parser is still defensive: strip code fences, take the first balanced `{…}` object, and on any
parse failure return zero corrections (fail open, consistent with FR-026). A prompt-only guard
("respond with JSON and nothing else") backs up the schema.

**Alternatives considered**:
- *Adding `chat_json` to `LLMProvider`* — one fewer type, but every streaming consumer inherits a
  method it has no use for. Rejected on ISP.
- *Plain `chat()` plus tolerant parsing, no schema* — what `LlmCacheService` does today, but that
  code only needs free prose. Here a parse failure silently costs a detection SC-003 counts.
- *A runtime `hasattr(llm, "chat_json")` capability check* — hidden coupling and an untyped
  contract; the constitution reserves capability checks for toggling in-development functionality.

---

## R5 — Enforcing the time budget without breaking the turn (FR-026)

**Decision**: the evaluator call runs in the default executor wrapped in
`asyncio.wait_for(..., timeout=CORRECTION_EVALUATION_TIMEOUT_SECONDS)`, default **8.0 s**,
configurable via `app.config.Settings.correction_timeout_seconds` (env
`OPEN_LANGUAGE_CORRECTION_TIMEOUT_SECONDS`). On `TimeoutError`, `LLMError`, or any parse failure, the
strategy returns an empty correction list and the turn proceeds exactly as it would in Off mode —
reply generated, no correction, no error surfaced to the learner.

**Why 8 s and not 2 s**: the original 2 s came from the spec's first-draft SC-004 and would have
timed out essentially every CPU-only evaluation, making Gentle and Strict silently useless on
non-GPU hardware — the failure would be invisible, since failing open looks exactly like "no errors
found". 8 s is long enough for a short JSON completion on a slow CPU host to actually land, and short
enough that a genuinely hung call does not strand the turn. The setting exists so a fast GPU host can
tighten it and a very slow host can loosen it.

**Rationale for failing open**: a missed correction costs one learning moment; a blocked turn costs
the conversation. Turning every evaluator failure mode into the same benign outcome is what FR-026
asks for, and SC-004a makes it a testable property rather than an implementation detail.

**Known limitation**: `asyncio.wait_for` abandons the coroutine, but the executor thread running the
blocking Ollama call keeps running to completion in the background. With a single local user this is
bounded and harmless; it is documented rather than engineered around. Timeouts are logged at
`warning` so a systematically slow evaluator is visible rather than silent.

---

## R6 — Cheap pre-filters before spending an LLM call

**Decision**: the evaluator is skipped entirely, returning zero corrections, when any of these holds:

| Guard | Constant | Requirement |
|---|---|---|
| Mode is Off | — | FR-002, SC-002 |
| Message classified low-confidence | `LOW_CONFIDENCE_THRESHOLD` | FR-010a |
| Fewer than 2 words after stripping punctuation | `MIN_WORDS_FOR_EVALUATION = 2` | Edge case: "sí", "gracias", "mm" |
| Strict pause already at the cap | `MAX_CONSECUTIVE_CORRECTED_ATTEMPTS = 2` | FR-018 |

Everything else — the whole-message-in-native-language case, missing diacritics, regionally valid
variation, merely unidiomatic phrasing — is handled by explicit negative instructions in the
evaluation prompt (FR-007), not by code. The prompt also caps the response at two corrections
(`MAX_CORRECTIONS_PER_MESSAGE = 2`, FR-008) and the parser truncates to that cap regardless of what
the model returns.

**Rationale**: the word-count guard is the only structural filter that is unambiguous. A
language-detection guard for the native-language case would duplicate logic the roleplay prompt
already owns and would misfire on cognates and loanwords; the evaluator prompt is the right place
for a judgement call. Enforcing the two-correction cap in the parser as well as the prompt means
FR-008 holds even when the model ignores the instruction.

These guards also matter for latency: every one of them is a turn that costs zero seconds instead of
up to the R5 budget.

---

## R7 — Where the Strict pause state lives

**Requirement**: FR-018 (count consecutive corrected attempts, cap at two), FR-027 (ask to repeat at
most once per message), FR-029 (both survive reopening the conversation).

**Decision**: a table owned by the corrections module, `conversation_correction_state`, keyed
one-to-one on `conversation_id`. It holds `consecutive_corrected_attempts` and
`awaiting_clarification`. The `conversations` table is **not** modified.

`awaiting_retry` is not stored — it is derived as
`consecutive_corrected_attempts > 0 AND the conversation's last message is a learner message`.

**Rationale**: Constitution V requires each feature domain to own its data behind its own interface.
Adding correction columns to the core `Conversation` model would put corrections state under another
module's ownership and force every consumer of `ConversationRecord` to carry fields it does not use.
A one-to-one side table keeps the whole feature additive and removable. Deriving `awaiting_retry`
instead of storing it removes a field that can disagree with the counters it is computed from.

**Alternatives considered**:
- *Columns on `conversations`* — fewer joins, but cross-module ownership; rejected on Constitution V.
- *Storing `awaiting_retry` on the message row* — convenient for rendering, but denormalised state
  that can go stale against the counter.
- *In-memory state à la `HelperSessionStore`* — fails FR-029 outright; the pause must survive a
  process restart.

---

## R8 — Resuming a conversation (blocks FR-022 and FR-029)

**Finding — pre-existing gap**: [Chat.tsx](../../frontend/src/pages/Chat.tsx) calls
`api.streamChatOpen(convId)` unconditionally on mount and never loads existing messages.
[History.tsx](../../frontend/src/pages/History.tsx) has no link into `/chat/:id`. So a browser
refresh on an in-progress conversation today discards the visible transcript and appends a second
opening message to a conversation that already had one.

FR-022 and FR-029 both require that reopening a conversation shows earlier corrections and preserves
an open Strict pause. Neither is reachable, let alone testable, while this holds.

**Decision — confirmed in scope by the user**: this feature includes making the chat screen
resume-aware. `Chat.tsx` fetches `GET /conversations/{id}/messages` on mount and calls
`/chat/{id}/open` **only** when that returns an empty list. The corrections attached to the hydrated
messages come from `GET /corrections/conversations/{id}` in the same load, and the composer enters
retry mode when that response reports `awaiting_retry`.

**Rationale**: it is the minimum change that makes FR-022 and FR-029 real rather than nominal, it is
squarely inside this feature's stated scope ("Conversation reloaded later" is a listed edge case),
and it fixes duplicate opening messages as a side effect. Persisting the state without a way to
reach it would mean shipping two requirements that no test could exercise.

**Scope note**: this is the one place the plan changes behaviour outside the correction feature. It
is a bug fix that FR-022/FR-029 depend on, not an expansion of the feature's ambitions. It brings its
own regression risk on an existing screen, so `chat.spec.ts` gains a resume case alongside the new
feature's E2E spec.

---

## R9 — Presenting an app note that is never spoken

**Requirement**: FR-019 (distinct element attached to the learner's message, not character
dialogue), FR-020 (never sent to TTS — covering both the Strict correction and the FR-027 repeat
request), FR-023 (contrast and an accessible label).

**Decision**: one React component, `FeedbackNote`, rendering both kinds of app note, discriminated
by a `kind` field (`correction` | `repeat_request`). It renders inside `MessageBubble`'s existing
`children` slot beneath the learner's own bubble.

TTS safety is structural rather than conditional: `GET /audio/tts/{message_id}` synthesises
`message.content`, and feedback lives in a separate table that is never written into `content` and
has no message id of its own. There is no code path by which a note can reach Piper. The test for
SC-005 asserts that no TTS request is issued for a flagged Strict turn — the `done` event for such a
turn carries `message_id: null`, so the client has nothing to request audio for.

**Styling** (per [docs/design-system.md](../../docs/design-system.md), tokens from `index.css`):
`--color-warning` for the left rule and heading, `--color-surface-raised` background,
`--color-text` for body copy, `--radius-lg`, `--shadow-sm`. Deliberately not `--color-primary`,
which is the learner's own bubble colour, and not `--color-error`, which reads as a failure rather
than as teaching. `role="note"` with `aria-label="Learning feedback"` states that it is not
dialogue. Both palettes are defined in `index.css` already, so dark mode needs no new tokens.

**Alternatives considered**:
- *A system-role message in the transcript* — would need a third `MessageRole`, would flow into LLM
  history, and would be a TTS target. Rejected on all three counts.
- *A toast or modal* — fails FR-022 (must persist in the transcript) and interrupts the flow.
- *Separate components per kind* — near-identical markup and duplicated accessibility handling for
  two variants that differ by one field.

---

## R10 — Keeping Off mode byte-identical (FR-002, SC-002)

**Decision**: `OffCorrectionStrategy` is a null object. It performs no database read of correction
state, makes no LLM call, writes no rows, and emits no additional SSE event. The chat router's Off
path is the code path that exists today plus one dependency injection and one strategy dispatch.

The SSE `feedback` event is emitted **only** when there is at least one note, so an Off-mode stream
is byte-for-byte what it is today. The frontend treats a missing `feedback` event as "no feedback",
so no client-side branch is added to the Off path either. Both R11 client changes — the checking
indicator and the deferred assistant placeholder — are gated on `correction_mode !== 'off'`, so Off
keeps its "zero visual change" guarantee as well as its byte-identical stream.

**Verification**: an integration test asserts that with `correction_mode="off"` the LLM stub records
exactly one call for a turn and the SSE frame sequence matches the pre-feature sequence exactly.

---

## R11 — Making the evaluation wait legible (SC-004)

**Finding — the current placeholder is wrong for this feature**: `Chat.tsx`'s `appendUserMessage`
immediately appends `{role: 'assistant', content: '', isStreaming: true}`, and `MessageBubble`
renders that as an empty character bubble with a blinking cursor. The one real status line,
`"Connecting…"` at [Chat.tsx:337](../../frontend/src/pages/Chat.tsx#L337), is guarded by
`messages.length === 0` and so never renders after the opening message.

With evaluate-first this breaks in two ways. During evaluation the learner sees an empty *character*
bubble, implying the character is about to speak — and on a flagged Strict turn no character reply
is ever coming, so that bubble then has to be removed. A phantom bubble appears and vanishes.

**Decision**: introduce an explicit turn status in `Chat.tsx` — `idle | checking | replying` — and,
**when `correction_mode !== 'off'`**, stop appending the assistant placeholder on send.

| Status | When | What the learner sees |
|---|---|---|
| `checking` | message sent, mode ≠ Off, no `feedback` or first token yet | a status line under the learner's message: "Checking your sentence…", `aria-live="polite"` |
| `replying` | first `token` frame arrives | mode ≠ Off: the assistant bubble is appended *then*, with the existing blinking cursor. Off: the bubble already exists from send and simply fills, exactly as today |
| `idle` | `done` received | as today |

In Gentle and Strict the assistant placeholder is created on the first token rather than on send. A
flagged Strict turn therefore never creates one, so there is nothing to remove and no flicker — the
`done` frame with `message_id: null` simply ends the turn with the correction as its only output,
which is exactly what FR-016 describes.

**Off mode keeps the send-time placeholder.** Deferring it there too would be simpler code, but the
placeholder is visible behaviour the learner sees on every turn today, and SC-002 promises Off mode
"zero visual change". The mode check that already gates the checking indicator (R10) gates this as
well, so Off is one branch, not a rewrite. `frontend/e2e/corrective-feedback.spec.ts` asserts both
halves: the deferral in Gentle/Strict, and its absence in Off.

**How the client knows to show it**: `Chat.tsx` already calls `api.getSettings()` on mount for
target and native language; it reads `correction_mode` from the same response. No new SSE frame and
no new request, and Off mode takes the untouched path (R10).

**Why not an SSE `evaluating` frame**: it would be more precise, but it adds a frame to the protocol
for information the client can already derive, and it would need suppressing in Off mode to protect
SC-002. Deriving from the known mode is simpler and keeps the Off stream provably unchanged.

**Settings-screen warning (user-requested)**: the correction-mode control carries a note beneath it —
Gentle and Strict run an extra language-model pass over each message before the character answers;
on a machine without a GPU this can add several seconds per turn, and a check that takes too long is
skipped so the conversation continues. This states the cost *and* the fail-open behaviour, so a
skipped correction later does not read as a bug. Written as a hint tied to the fieldset via
`aria-describedby`, in `--color-text-muted`, so it informs without competing with the control
(Constitution IV — secondary content visually subordinate).

---

## Summary of named constants

All live in `backend/app/corrections/config.py`, except the settings-backed ones. The STT thresholds
live with the STT provider, since they describe transcription quality rather than correction policy.

| Constant | Value | Source requirement |
|---|---|---|
| `LOW_CONFIDENCE_THRESHOLD` | 0.55 (setting) | FR-010 |
| `NO_SPEECH_PROB_THRESHOLD` | 0.6 | FR-010 (Whisper default) |
| `COMPRESSION_RATIO_THRESHOLD` | 2.4 | FR-010a (Whisper default) |
| `CORRECTION_EVALUATION_TIMEOUT_SECONDS` | 8.0 (setting) | FR-026, SC-004 |
| `MAX_CORRECTIONS_PER_MESSAGE` | 2 | FR-008 |
| `MAX_CONSECUTIVE_CORRECTED_ATTEMPTS` | 2 | FR-018 |
| `MIN_WORDS_FOR_EVALUATION` | 2 | Edge case: fragmentary input |
| `MAX_REPEAT_REQUESTS_PER_MESSAGE` | 1 | FR-027 |

The two marked "(setting)" are not module constants: they are pydantic `Settings` fields in
`backend/app/config.py`, spelled `low_confidence_threshold` and `correction_timeout_seconds`, and
overridable as `OPEN_LANGUAGE_LOW_CONFIDENCE_THRESHOLD` and
`OPEN_LANGUAGE_CORRECTION_TIMEOUT_SECONDS`. The SCREAMING_CASE names above are how this document
refers to the *values*; the snake_case names are what appears in code.

**All NEEDS CLARIFICATION items from Technical Context are resolved.**
