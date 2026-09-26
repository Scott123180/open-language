# Phase 1 Validation Guide: Corrective Feedback Mode

**Branch**: `003-corrective-feedback-mode` | **Date**: 2026-08-25 | **Plan**: [plan.md](plan.md)

How to prove the feature works end to end once `/speckit-implement` has run. Each scenario maps to a
user story or success criterion in [spec.md](spec.md). Details of shapes and fields live in
[contracts/api.md](contracts/api.md) and [data-model.md](data-model.md) — this file is the run guide.

---

## Prerequisites

| Requirement | Check |
|---|---|
| Python venv at `backend/.venv` | `backend/.venv/bin/python --version` → 3.12.x |
| Backend deps installed | `backend/.venv/bin/pip install -e "backend[dev]"` |
| Frontend deps installed | `cd frontend && npm install` |
| Playwright browser | `cd frontend && npx playwright install chromium` |
| Ollama running with llama3.1 | `ollama list` shows `llama3.1` — needed for manual scenarios only |

Automated tests stub the LLM and STT providers, so **no Ollama, Piper, or GPU is needed to run the
test suites** — including every confidence edge case, which runs against synthetic segments. Ollama
is required only for the manual walkthroughs in §3.

If manual runs on a CPU-only host time out before producing corrections, raise the budget rather than
concluding the feature is broken:
`OPEN_LANGUAGE_CORRECTION_TIMEOUT_SECONDS=20 backend/.venv/bin/uvicorn app.main:app --port 8000`.

---

## 1. Automated suites

Run each as its own command (per the repo's shell rules — no chaining).

```bash
# Backend: full suite with the constitution's 90% coverage gate
backend/.venv/bin/pytest --cov=app --cov-report=term-missing

# Backend: this feature only
backend/.venv/bin/pytest backend/tests/unit/corrections backend/tests/integration/corrections -v

# Backend: contract tests for the four new/modified ABCs
backend/.venv/bin/pytest backend/tests/contract -v

# Lint and format — must be clean before merge
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/black --check backend/app backend/tests
```

```bash
# Frontend component tests
cd frontend && npm test

# Frontend E2E — mandatory for this feature (constitution)
cd frontend && npm run test:e2e

# Just this feature's E2E spec
cd frontend && npx playwright test e2e/corrective-feedback.spec.ts
```

**Expected**: zero failures, zero skips, coverage on new backend code ≥ 90%.

---

## 2. Scenario checks

Each row is one automated check. "Where" names the suite that owns it.

### User Story 1 — Strict mode corrects and pauses (P1)

| # | Given / When | Then | Where |
|---|---|---|---|
| 1.1 | mode = strict; learner sends `"Yo tener veinte años"` | SSE carries a `feedback` frame with `kind:"correction"`, a `corrected_text`, and `awaiting_retry:true` | `test_chat_correction_modes.py` |
| 1.2 | a Strict correction is open; learner sends a corrected retry | the character replies to the retry, and the full prior history is in the LLM prompt | `test_chat_correction_modes.py` |
| 1.3 | mode = strict; learner sends a correct sentence | no `feedback` frame; stream identical to Off | `test_chat_correction_modes.py` |
| 1.4 | a flagged Strict turn | `done` carries `message_id: null`; **no assistant row exists** for that turn | `test_chat_correction_modes.py` |
| 1.5 | a flagged Strict turn in the browser | the correction renders under the learner's bubble; **no `/api/audio/tts/` request is issued** (SC-005) | `corrective-feedback.spec.ts` |

Check 1.4 is the FR-016 test: it asserts the *absence* of a stored assistant message, not just the
absence of streamed tokens — "whether shown, withheld, or stored".

### User Story 2 — Gentle mode corrects without stopping (P2)

| # | Given / When | Then | Where |
|---|---|---|---|
| 2.1 | mode = gentle; learner sends a sentence with an error | one turn: reply tokens stream, no `feedback` frame, no pause | `test_chat_correction_modes.py` |
| 2.2 | same | the roleplay system prompt contains the recast instruction, carrying the corrected form | `test_chat_correction_modes.py` |
| 2.3 | mode = gentle | the recast instruction never asks for native-language output; the target-language rule stays first in the prompt (FR-011, SC-007) | `test_prompts.py` |
| 2.4 | mode = gentle; correct sentence | ordinary reply; no correction row written | `test_chat_correction_modes.py` |

FR-011/SC-007 ("zero native-language words in the reply") cannot be asserted deterministically
against a real model. What is asserted is the prompt contract — the correction instruction never
requests native language and never displaces the existing `CRITICAL LANGUAGE RULE`. The observed
behaviour is verified manually in §3.

### User Story 3 — Restraint (P3)

| # | Given / When | Then | Where |
|---|---|---|---|
| 3.1 | evaluator returns 4 findings | at most 2 are persisted and surfaced, ordered by `rank` (FR-008) | `test_evaluator.py` |
| 3.2 | message is `"sí"` / `"gracias"` | evaluation is skipped entirely; zero LLM calls | `test_evaluator.py` |
| 3.3 | message is low-confidence, mode = gentle | ordinary reply, no correction, no pause (FR-028) | `test_chat_correction_modes.py` |
| 3.4 | message is low-confidence, mode = strict | repeat request; `awaiting_retry:true`; no correction (FR-027) | `test_chat_correction_modes.py` |
| 3.5 | the repeat is *also* low-confidence | conversation proceeds normally; no second request | `test_pause_tracker.py` |
| 3.6 | prompt contract | the evaluation prompt names diacritics, regional variation, and unidiomatic-but-correct phrasing as **not** correctable (FR-007) | `test_prompts.py` |

### Edge cases and resilience

| # | Given / When | Then | Where |
|---|---|---|---|
| 4.1 | mode = strict; two corrected attempts in a row | the third message is answered normally whatever it contains, including a brand-new error (FR-018, SC-006) | `test_pause_tracker.py` |
| 4.2 | evaluator exceeds the configured timeout (`correction_timeout_seconds`, default 8 s) | reply delivered, no correction, no error shown (FR-026) | `test_correction_resilience.py` |
| 4.3 | evaluator raises `LLMError` | same as 4.2 | `test_correction_resilience.py` |
| 4.4 | evaluator returns prose instead of JSON | same as 4.2 | `test_correction_resilience.py` |
| 4.5 | mode changed mid-conversation | applies from the next message; existing feedback rows unchanged (FR-004) | `test_chat_correction_modes.py` |
| 4.6 | mode switched to Off while a Strict pause is open | next message answered normally; pause effectively cleared | `test_chat_correction_modes.py` |
| 4.7 | conversation reopened while awaiting a retry | `GET /corrections/conversations/{id}` returns `awaiting_retry:true` and the earlier notes (FR-029) | `test_correction_endpoints.py` |
| 4.8 | conversation reopened in the browser | earlier corrections are visible; the composer is still in retry mode | `corrective-feedback.spec.ts` |
| 4.8a | **regression (R8)**: reload a conversation that already has messages | the transcript is restored and `/chat/{id}/open` is **not** called — no duplicate opening message | `chat.spec.ts` |
| 4.8b | open a conversation with no messages | `/chat/{id}/open` is called exactly as before | `chat.spec.ts` |
| 4.9 | mode = off | SSE frame sequence is byte-identical to pre-feature; exactly one LLM call per turn (SC-002) | `test_chat_correction_modes.py` |
| 4.10 | any mode | Grammar / Translate / Phrasing tools still work on a corrected message and are not pre-filled by it (FR-024, FR-025) | `test_correction_endpoints.py` |

### Confidence computation (research.md R1)

All of these run against synthetic `Segment` objects — no model, no audio, no GPU — in
`test_transcription_confidence.py` unless noted.

| # | Given | Then |
|---|---|---|
| 5.1 | two segments, `avg_logprob` −0.2 over 40 tokens and −1.5 over 4 tokens | result is the **token-weighted** exponentiated mean; asserting against the unweighted mean fails |
| 5.2 | segments identical except for duration | result is unchanged — duration is not a weight |
| 5.3 | a segment with `no_speech_prob = 0.9` between two clean segments | that segment is excluded; the score matches the two clean segments alone |
| 5.4 | a segment with empty `text` | excluded |
| 5.5 | a segment with `end == start` | excluded |
| 5.6 | **text present, every segment `no_speech_prob > 0.6`** | `confidence == 0.0` → low-confidence (hallucination-on-silence) |
| 5.7 | any retained segment with `compression_ratio = 3.1` | forced low-confidence **despite** a high `avg_logprob` (repetition loop) |
| 5.8 | no segments at all | `confidence is None` |
| 5.9 | retained segments whose `tokens` lists are all empty | `confidence is None`, not a division error |
| 5.10 | `confidence is None` | classified **not** low-confidence → evaluated normally |
| 5.11 | `confidence == 0.0` | classified low-confidence → not evaluated |
| 5.12 | a clean single segment, `avg_logprob = -0.2` | `confidence ≈ 0.82`, above the 0.55 threshold |
| 5.13 | a mumbled segment, `avg_logprob = -0.9` | `confidence ≈ 0.41`, below the threshold |
| 5.14 | typed message with a confidence supplied by the client | ignored, stored `NULL`, never gated (`test_chat_correction_modes.py`) |
| 5.15 | confidence outside 0.0–1.0 in the request | `422` (`test_chat_correction_modes.py`) |
| 5.16 | `WhisperSTTProvider` transcribes | it delegates to the aggregator rather than computing inline (`test_whisper_stt.py`) |

Checks 5.6 and 5.7 are the two that matter most for FR-010a: both are cases where the transcript
*looks* confident and is wrong, which is exactly how a correction gets invented for words the learner
never said.

### Perceived wait and the checking indicator (SC-004, research.md R11)

| # | Given / When | Then | Where |
|---|---|---|---|
| 6.1 | mode = gentle; message sent | "Checking your sentence…" appears within 1 s, `aria-live="polite"` | `corrective-feedback.spec.ts` |
| 6.2 | first reply token arrives | the indicator clears and the assistant bubble appears | `corrective-feedback.spec.ts` |
| 6.3 | **flagged Strict turn** | **no assistant bubble is ever created** — not even briefly | `corrective-feedback.spec.ts` |
| 6.4 | mode = off; message sent | no indicator; the screen behaves exactly as before (SC-002) | `corrective-feedback.spec.ts` |
| 6.5 | evaluation times out | indicator clears, reply streams, no correction, no error banner (SC-004a) | `test_correction_resilience.py` + E2E |
| 6.6 | Settings screen | the correction-mode control carries the GPU/performance hint, linked by `aria-describedby` | `settings.spec.ts` |

Check 6.3 is a regression guard on R11's core point: asserting the bubble never appears, not merely
that it is gone by the end of the turn.

---

## 3. Manual walkthrough

Needs Ollama with llama3.1 running. Two terminals.

```bash
backend/.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

### 3a. Strict mode (User Story 1, SC-001, SC-005)

1. Settings → set **Correction mode** to **Strict** → Save. Confirm "Settings saved." appears.
2. Home → start any scenario. Time the round trip from chat to settings and back — under 15 s (SC-001).
3. Type `Yo tener veinte años`.
4. **Expect**: a correction note under your own message naming the conjugation error, giving
   `Yo tengo veinte años`, and asking you to try again. **No character reply.** No audio plays.
5. Type `Yo tengo veinte años`. The character now replies, in context.
6. Refresh the page. The transcript and the correction are still there (FR-022).

### 3b. Strict mode does not trap you (SC-006)

Continuing from 3a: send three sentences each containing a *different* error. The first two are
corrected; the third is answered normally. This is FR-018's cap — it counts attempts, not repeats of
one error.

### 3b-2. The wait is legible (SC-004, R11)

Still in Strict mode, on whatever hardware you actually run:

1. Send a sentence with an error and watch the moment after you press Send.
2. **Expect**: "Checking your sentence…" appears promptly under your message. You should never see
   an empty character bubble with a blinking cursor during the check, and on a flagged turn no
   character bubble should appear at all.
3. Note the wall-clock time from Send to the correction appearing. On a GPU host this should be
   inside 4 s. On a CPU-only host, expect noticeably longer — and if it passes the timeout, the
   character simply replies uncorrected, which is the designed behaviour, not a failure.
4. Settings → confirm the note under Correction mode explains this before you hit it.

### 3c. Gentle mode (User Story 2, SC-007)

1. Settings → **Gentle** → Save.
2. Send `Yo tener veinte años`.
3. **Expect**: one reply, in character, containing `tienes` or `tengo` woven in naturally. No note,
   no pause, no English anywhere.
4. Send several more sentences with errors and read every reply for native-language words — SC-007
   allows zero.

### 3d. Off mode (SC-002)

1. Settings → **Off** → Save.
2. Hold a normal conversation with deliberate errors. Nothing is corrected, nothing is added, no
   checking indicator appears, and the turn feels no slower than before the feature existed.

### 3d-2. Resume (FR-022, FR-029, R8)

1. In Strict mode, get a correction so the conversation is paused awaiting a retry.
2. Reload the page.
3. **Expect**: the full transcript is restored, the correction is still under your message, the
   composer is still in retry mode, and **no second opening message** has been appended. Before this
   feature, a reload discarded the transcript and re-greeted you.

### 3e. Low-confidence speech (FR-027)

1. Settings → **Strict**.
2. Record a message with heavy background noise or mumbling.
3. **Expect**: "I didn't quite catch that — could you say it again?" as an app note, not spoken in
   the character's voice, and no grammar correction.
4. Mumble again. The conversation now proceeds normally rather than asking twice.

### 3f. Accessibility check (FR-023, constitution gate)

- Tab to the correction note — it is announced as a note labelled "Learning feedback", not as
  dialogue.
- Toggle Settings → Theme → Dark. The note stays legible; check its contrast in both themes.
- Confirm the note is visually distinct from the character's bubble at a glance (FR-019).

---

## 4. Merge checklist

- [ ] `backend/.venv/bin/pytest --cov=app` — zero failures, zero skips, ≥ 90% on new code
- [ ] `backend/.venv/bin/ruff check` and `black --check` — clean
- [ ] `cd frontend && npm test` — zero failures
- [ ] `cd frontend && npm run test:e2e` — zero failures (mandatory for frontend changes)
- [ ] §3f accessibility check done by hand in both themes
- [ ] `docs/architecture.md` updated with the `corrections` domain module
- [ ] No hardcoded hex colours in `FeedbackNote.tsx` — tokens only (`docs/design-system.md`)
- [ ] Off mode verified byte-identical (check 4.9), not just assumed
- [ ] Reload of a conversation with messages does not call `/open` (check 4.8a) — the R8 regression
- [ ] No phantom assistant bubble on a flagged Strict turn (check 6.3)
- [ ] Timeout measured on the target host and `CORRECTION_EVALUATION_TIMEOUT_SECONDS` tuned if needed
