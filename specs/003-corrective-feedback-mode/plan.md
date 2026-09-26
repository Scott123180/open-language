# Implementation Plan: Corrective Feedback Mode

**Branch**: `003-corrective-feedback-mode` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-corrective-feedback-mode/spec.md`

---

## Summary

Add a learner-level `correction_mode` setting (Off / Gentle / Strict) that decides whether the
roleplay partner corrects grammar as the learner speaks. Off leaves today's behaviour untouched.
Gentle evaluates the learner's message, then folds the corrected form into the character's own reply
as a natural recast — one turn, still fully in the target language. Strict evaluates first and, when
it finds a substantive error, produces the correction as the turn's *only* output: no character reply
is generated at all until the learner tries again.

The work lands as a new compartmentalised `backend/app/corrections/` domain module owning two tables
(`message_feedback`, `conversation_correction_state`), a mode-per-strategy design behind a single
`CorrectionStrategy` abstraction, and one new narrow LLM interface for constrained JSON output.

Because evaluation must precede generation (FR-016), a corrected turn costs two sequential model
calls. Three pieces of the plan exist to make that cost acceptable rather than hidden: a **checking
indicator** so the wait is legible, a **plain-language warning on the Settings screen** about the
cost on GPU-less hardware, and a **generous timeout that fails open** so a slow host degrades to
uncorrected conversation rather than to a stalled one. The chat screen also becomes **resume-aware**,
without which FR-022 and FR-029 are unreachable.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.4 / React 18.3 (frontend)

**Primary Dependencies**:
- Backend: FastAPI 0.135, SQLAlchemy 2.0.48, `ollama` 0.6.1 (llama3.1), `faster-whisper` 1.2.1
  (**verified latest on PyPI** — no upgrade exposes an overall confidence), piper-tts.
  **No new dependencies.**
- Frontend: React 18, react-router-dom v6, Playwright, Vitest. **No new dependencies.**

**Storage**: SQLite, WAL mode, foreign keys ON. Two new tables via `create_all()`; one additive
column on `app_settings` and two on `messages` via the existing `_add_column_if_missing()` helper in
[database.py](../../backend/app/database.py).

**Testing**: pytest 9 (backend, ≥ 90% coverage on new code), Vitest + Testing Library (component),
Playwright (E2E, mandatory for every frontend change per the constitution).

**Target Platform**: Linux desktop, fully local. Ollama and Piper on localhost; no external services.
GPU optional — and the difference it makes is surfaced to the learner rather than assumed away.

**Performance Goals**:
- Off mode adds 0 ms, 0 queries, 0 pixels (SC-002).
- A checking indicator is visible within 1 s of sending whenever mode ≠ Off (SC-004).
- Evaluation adds ≤ 4 s on a GPU-accelerated host (SC-004).
- Evaluation is abandoned at `CORRECTION_EVALUATION_TIMEOUT_SECONDS` (default 8 s, configurable) on
  any host, after which the turn completes uncorrected and indistinguishable from Off (SC-004a).

**Constraints**: fully offline; single user; correction evaluation must never block or fail a
conversation turn (FR-026); Strict correction text must be structurally incapable of reaching TTS
(FR-020).

**Scale/Scope**: single learner, conversations of tens of turns, ≤ 2 feedback rows per message.

*(No NEEDS CLARIFICATION items remain — see [research.md](research.md).)*

---

## Spec interpretations

Three points where the spec admitted more than one reading. Each is resolved here so the choice is
visible for review rather than buried in code.

1. **FR-019 and FR-022 are scoped to Strict-mode corrections.** In Gentle mode the correction *is*
   the character's reply (FR-012), so rendering it a second time as a distinct element would
   contradict the mode's stated intent that "the learner may not consciously register that they were
   corrected". Gentle corrections are still persisted with `mode="gentle"` — they are the record of
   what produced the recast, and they satisfy the Key Entities requirement that a Correction carry
   the mode it was produced under — but they are not rendered.
   **Folded back into the spec on 2026-08-26**: FR-019 and FR-022 now carry this scoping in their own
   text, so the spec no longer reads as requiring the opposite. This entry is kept for the rationale.

2. **The FR-027 repeat request is stored alongside corrections, not as a message.** It is an app
   note attached to a learner message with the same never-spoken, persists-with-the-conversation
   properties as a correction, so it shares the `message_feedback` table under
   `kind="repeat_request"` and the same `FeedbackNote` component.

3. **The Key Entities line "Learner Message … gains an indication of whether it is awaiting a retry"
   is satisfied by derivation, not by a stored column.** `awaiting_retry` is computed as
   `consecutive_corrected_attempts > 0 AND this is the conversation's last message`. Storing it
   would create a second source of truth that can disagree with the counter. See
   [research.md](research.md) R7.

---

## Constitution Check

*GATE: must pass before Phase 0. Re-evaluated after Phase 1 design — result at the bottom of this
section.*

| Principle | Status | How this design satisfies it |
|---|---|---|
| **I. Clean Code** — ≤ 20-line functions, intention-revealing names, no magic values | ✅ | Every threshold and cap is a named constant (see research.md summary table), and every STT threshold carries its Whisper provenance rather than being invented. Strategy classes keep each method to a single decision. |
| **II. SOLID — SRP** | ✅ | `CorrectionEvaluator` finds errors. `CorrectionStrategy` decides what a mode does with them. `CorrectionPauseTracker` owns the Strict counters. `CorrectionStorageProvider` persists. `TranscriptionConfidence` aggregates segment signals. Five collaborators, five reasons to change. |
| **II. SOLID — OCP** | ✅ | Modes are Strategy implementations behind one ABC. A fourth mode is a new class plus a factory entry — no edit to the chat router, the evaluator, or the existing strategies. |
| **II. SOLID — LSP** | ✅ | `TranscriptionResult.confidence` is added with default `None`, so the existing frozen dataclass and its contract test remain valid and every `STTProvider` stays substitutable. All three strategies return the same `TurnPlan` shape and none narrows the contract. |
| **II. SOLID — ISP** | ✅ | `StructuredLLMProvider` is a **separate** one-method ABC, not an addition to `LLMProvider` — streaming consumers never see `chat_json`, and the corrections module never sees `chat_stream`. Persistence uses its own `CorrectionStorageProvider` ABC rather than growing the core `StorageProvider`. |
| **II. SOLID — DIP** | ✅ | Strategies receive evaluator, storage, and pause tracker via constructor injection; the router receives a strategy from `get_correction_strategy()`. No business-logic class constructs a DB session, an Ollama client, or a Whisper model. |
| **III. TDD (non-negotiable)** | ✅ | Confidence aggregation, evaluator parsing, the pause state machine, and the word-count guard are all pure functions testable ahead of any wiring. Every task in `tasks.md` will lead with its failing test. |
| **≥ 90% coverage, zero skipped tests** | ✅ | Enforced by `pyproject.toml`. The fail-open paths (timeout, `LLMError`, malformed JSON) and every confidence edge case get an explicit test rather than being left as untested branches. |
| **IV. Simple UI — one primary action per screen** | ✅ | Chat's primary action stays Send; the correction note and the checking indicator are both passive. Settings gains one three-position radio group and one explanatory hint; its primary action stays Save. Per FR-005, no correction control is added to the chat screen. |
| **IV. Immediate feedback for every action** | ✅ | **Strengthened by this revision.** A checking indicator appears within 1 s of sending whenever mode ≠ Off (SC-004), replacing the phantom empty-character-bubble the current code would show. Settings keeps its "Settings saved." confirmation (FR-005). A flagged Strict turn switches the composer to retry mode so the pause is stated, not implied by silence. |
| **IV. Plain-language messages that say what to do next** | ✅ | The Settings hint states the cost of Gentle/Strict on a GPU-less machine *and* that a slow check is skipped rather than failing — so a later missing correction reads as designed behaviour, not a bug. |
| **IV. Accessibility** | ✅ | `FeedbackNote` uses `role="note"` + `aria-label="Learning feedback"` (FR-023); the checking indicator is `aria-live="polite"`; the Settings hint is tied to its fieldset via `aria-describedby`. Warm-tinted tokens with light and dark values already exist in `index.css`. Manual contrast check is a checklist gate. |
| **V. Compartmentalization** | ✅ | `backend/app/corrections/` owns its models, schemas, prompts, services, and router, and owns both of its tables. Other modules reach it only through `app.corrections`' public exports. It does not modify `Conversation`. |
| **V. Extension points declared as abstractions first** | ✅ | `CorrectionStrategy`, `CorrectionEvaluator`, `CorrectionStorageProvider`, and `StructuredLLMProvider` are all ABCs written before their concrete implementations. |
| **V. No feature-flag/if-debug guards in domain logic** | ✅ | `correction_mode` is a user preference resolved once into a strategy object at the module boundary. No mode string is branched on inside domain logic. |
| **Playwright E2E mandatory for frontend changes** | ✅ | New `frontend/e2e/corrective-feedback.spec.ts`; `settings.spec.ts` and `chat.spec.ts` extended — the latter specifically for the resume regression. |
| **Linting (ruff, black, ESLint, Prettier)** | ✅ | No new tooling; existing config applies. |

**Initial gate: PASS.**
**Post-Phase-1 re-evaluation: PASS.** The revision strengthened the Principle IV rows rather than
weakening any: making the evaluation wait visible and stating its cost on the Settings screen are
both direct applications of "immediate, clear feedback for every user action".

---

## Project Structure

### Documentation (this feature)

```text
specs/003-corrective-feedback-mode/
├── spec.md              # input
├── plan.md              # this file
├── research.md          # Phase 0 output — R1..R11
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Backend source

```text
backend/app/
├── corrections/                          ← NEW domain module
│   ├── __init__.py                       ← public interface: CorrectionMode, TurnPlan,
│   │                                        FeedbackDraft, build_correction_strategy, router
│   ├── config.py                         ← named constants (see research.md summary table)
│   ├── models.py                         ← MessageFeedback, ConversationCorrectionState
│   ├── schemas.py                        ← Pydantic request/response models
│   ├── prompts.py                        ← evaluation prompt, JSON schema, recast instruction,
│   │                                        repeat-request text
│   ├── router.py                         ← GET /corrections/conversations/{id}
│   └── services/
│       ├── __init__.py
│       ├── evaluator.py                  ← CorrectionEvaluator ABC + LlmCorrectionEvaluator
│       ├── strategies.py                 ← CorrectionStrategy ABC + Off / Gentle / Strict
│       ├── pause_tracker.py              ← CorrectionPauseTracker (FR-018, FR-027, FR-029)
│       ├── storage.py                    ← CorrectionStorageProvider ABC
│       └── sqlite_storage.py             ← SQLiteCorrectionStorageProvider
│
├── services/llm/base.py                  ← MODIFIED: + StructuredLLMProvider ABC
├── services/llm/ollama.py                ← MODIFIED: implements chat_json via format=<schema>
├── services/stt/base.py                  ← MODIFIED: TranscriptionResult.confidence (default None)
├── services/stt/confidence.py            ← NEW: segment filtering + token-weighted aggregate (R1)
├── services/stt/whisper.py               ← MODIFIED: calls the aggregator
├── services/factory.py                   ← MODIFIED: get_structured_llm, get_correction_storage,
│                                            get_correction_strategy
├── services/storage/base.py              ← MODIFIED: AppSettingsRecord.correction_mode
├── services/storage/sqlite.py            ← MODIFIED: map the new settings column
├── models/app_settings.py                ← MODIFIED: correction_mode column
├── models/message.py                     ← MODIFIED: transcription_confidence, is_low_confidence
├── config.py                             ← MODIFIED: low_confidence_threshold,
│                                            correction_timeout_seconds
├── routers/settings.py                   ← MODIFIED: expose/validate correction_mode
├── routers/audio.py                      ← MODIFIED: return confidence + is_low_confidence
├── routers/chat.py                       ← MODIFIED: strategy dispatch in send_message
├── database.py                           ← MODIFIED: register tables + 3 additive migrations
└── main.py                               ← MODIFIED: include the corrections router
```

Confidence aggregation lives in its own `stt/confidence.py` rather than inside `whisper.py` so it can
be unit-tested against synthetic segments with no model, no audio, and no GPU — which is what makes
the edge-case table in research.md R1 testable at all.

**Untouched on purpose**: `routers/learning.py` and `models/learning_tool_result.py`. The on-demand
Grammar / Translate / Phrasing tools are a separate mechanism with separate storage, so FR-024 and
FR-025 hold by construction — automatic corrections cannot pre-fill or suppress them. Tests assert
this rather than assuming it.

### Backend tests

```text
backend/tests/
├── contract/service_interfaces/
│   ├── test_correction_storage_provider.py    ← NEW
│   ├── test_structured_llm_provider.py        ← NEW
│   └── test_stt_provider.py                   ← MODIFIED: confidence field contract
├── unit/corrections/
│   ├── test_evaluator.py                      ← NEW: JSON parsing, cap, fail-open
│   ├── test_strategies.py                     ← NEW: Off / Gentle / Strict TurnPlan behaviour
│   ├── test_pause_tracker.py                  ← NEW: FR-018 / FR-027 state machine
│   └── test_prompts.py                        ← NEW
├── unit/services/
│   ├── test_transcription_confidence.py       ← NEW: the full R1 edge-case table
│   └── test_whisper_stt.py                    ← MODIFIED: provider wires the aggregator in
├── integration/corrections/
│   ├── test_correction_endpoints.py           ← NEW
│   ├── test_chat_correction_modes.py          ← NEW: the three modes end to end over SSE
│   ├── test_correction_resilience.py          ← NEW: timeout / LLMError / bad JSON
│   └── test_correction_benchmark.py           ← NEW: the SC-003 detection benchmark against the
│                                                 real model, deselected by default
├── integration/routers/test_transcribe.py     ← MODIFIED: confidence + is_low_confidence
├── integration/routers/test_settings.py       ← MODIFIED: correction_mode round-trip
└── unit/test_database.py                      ← MODIFIED: the three additive migrations
```

`test_correction_benchmark.py` is separate and `@pytest.mark.benchmark`-deselected because it calls
Ollama: SC-003 is a claim about detection quality, which only the real model can substantiate, and
that makes it too slow and too non-deterministic for the default suite. The hermetic suite covers the
same 20 sentences against a scripted stub to prove the pipeline surfaces whatever the evaluator
reports — which is a different claim, and is labelled as one.

### Frontend source

```text
frontend/
├── src/components/chat/
│   ├── FeedbackNote.tsx                  ← NEW
│   ├── FeedbackNote.test.tsx             ← NEW
│   ├── TurnStatusIndicator.tsx           ← NEW: "Checking your sentence…" (R11)
│   └── TurnStatusIndicator.test.tsx      ← NEW
├── src/pages/Chat.tsx                    ← MODIFIED: hydrate on mount (R8); turn status
│                                            idle|checking|replying; assistant placeholder created
│                                            on first token rather than on send **when mode ≠ Off**,
│                                            Off keeping today's send-time placeholder (R10, R11);
│                                            feedback SSE event; retry-aware composer
├── src/components/chat/MessageBubble.test.tsx ← MODIFIED: children-slot rendering
├── src/pages/Settings.tsx                ← MODIFIED: correction-mode radio group + performance hint
├── src/pages/Settings.test.tsx           ← MODIFIED
├── src/components/chat/MessageBubble.tsx ← MODIFIED: render feedback via the children slot
├── src/services/api.ts                   ← MODIFIED: types, confidence round-trip, feedback fetch
└── e2e/
    ├── corrective-feedback.spec.ts       ← NEW
    ├── chat.spec.ts                      ← MODIFIED: resume regression (R8)
    ├── settings.spec.ts                  ← MODIFIED
    └── fixtures.ts                       ← MODIFIED: feedback SSE helper + mock data
```

**Structure Decision**: Option 2 (web application), matching the existing `backend/` + `frontend/`
split. The new backend code follows the `backend/app/flashcards/` precedent from feature 002 —
a self-contained domain package with its own models, schemas, router, and `services/` directory
behind a storage ABC — because that pattern already satisfies Constitution V here and keeps this
feature additive and removable.

---

## Phase 1 design at a glance

The full contract is in [contracts/api.md](contracts/api.md) and the schema in
[data-model.md](data-model.md). The turn flow, which is the heart of the feature:

```text
POST /chat/{id}/message  { content, input_source, transcription_confidence? }
  │
  ├─ save learner message (persisting confidence + low-confidence classification)
  ├─ SSE: user_message_saved          → client shows "Checking your sentence…" when mode ≠ Off
  │
  ├─ strategy = build_correction_strategy(app_settings.correction_mode)
  ├─ plan = await strategy.plan_turn(…)      # ≤ 8 s, fails open to an Off-mode turn
  │
  ├─ persist plan.feedback → message_feedback
  ├─ SSE: feedback          (emitted only when plan.feedback is non-empty)
  │
  ├─ if not plan.generate_reply:            # Strict, flagged
  │     SSE: done { message_id: null }      # no assistant row, nothing for TTS to fetch
  │     return                              # client clears the indicator; no bubble was ever made
  │
  └─ stream the reply with plan.reply_prompt_suffix appended to the system prompt
        SSE: token…  →  save assistant message  →  TTS  →  SSE: done { message_id }
             ↑ client creates the assistant bubble here, on the first token
```

`TurnPlan` is the single value that carries a mode's decision:

| Field | Off | Gentle | Strict (clean) | Strict (flagged) |
|---|---|---|---|---|
| `feedback` | `()` | corrections, `mode="gentle"` | `()` | corrections or repeat request |
| `generate_reply` | `True` | `True` | `True` | `False` |
| `reply_prompt_suffix` | `None` | recast instruction | `None` | `None` |
| pause counter | untouched | untouched | reset to 0 | +1 (capped at 2) |

---

## Complexity Tracking

The Constitution Check passes with no principle violations. Two decisions are recorded here because
they widen the blast radius beyond the corrections module. **Both are confirmed in scope.**

| Decision | Why needed | Simpler alternative rejected because |
|---|---|---|
| **Chat screen becomes resume-aware** — hydrate from `GET /conversations/{id}/messages`, call `/chat/{id}/open` only when the conversation is empty | FR-022 and FR-029 require corrections and an open Strict pause to survive reopening. `Chat.tsx` currently always calls `/open` and never loads history, so a refresh discards the transcript and appends a second opening message. Without this, both requirements are untestable through the UI. | Persisting the state and leaving it unreachable would ship two requirements no test can exercise. The regression risk on an existing screen is covered by a new resume case in `chat.spec.ts`. See [research.md](research.md) R8. |
| **Two sequential LLM calls per corrected turn** (evaluate, then reply) | FR-016 forbids a generated-then-withheld reply, so evaluation must precede generation; FR-006 requires Gentle to evaluate too. Sharing one evaluator across both modes means SC-003's benchmark measures the detection path both modes actually use. | Prompt-only Gentle is one call and faster, but produces no `Correction` record, contradicting FR-006 and the Key Entities definition — **rejected outright, not deferred**. The latency it would have saved is instead handled honestly: a relaxed tiered budget (SC-004), a visible checking indicator, a Settings-screen warning about GPU-less hosts, and a fail-open timeout. See [research.md](research.md) R3, R5, R11. |

---

## Artifacts generated by this plan

| Artifact | Path |
|---|---|
| Phase 0 research | [research.md](research.md) |
| Phase 1 data model | [data-model.md](data-model.md) |
| Phase 1 API contract | [contracts/api.md](contracts/api.md) |
| Phase 1 validation guide | [quickstart.md](quickstart.md) |

**Spec amended by this revision**: SC-004 was rewritten from a flat 2-second budget to a tiered one
(indicator within 1 s, ≤ 4 s on GPU, fail-open timeout on any host), and SC-004a was added to make
"an abandoned evaluation is indistinguishable from Off" a testable property. The original 2 s figure
would have timed out nearly every CPU-only evaluation while looking exactly like "no errors found" —
silently disabling the feature on GPU-less hardware.

**Spec amended again on 2026-08-26** following `/speckit-analyze`: FR-006 gained its three
evaluation-skip exceptions, FR-019 and FR-022 were scoped to Strict-mode corrections (folding this
plan's "Spec interpretations" #1 back into the spec), and FR-013 now defers to FR-028 rather than
restating it. No behaviour changed — the spec now says what the plan already did. The same pass added
the missing test tasks for FR-004, FR-021, FR-024, FR-025, FR-026 and SC-004a, and corrected the
Off-mode carve-out on the assistant placeholder (R10/R11). See the amendment note in
[spec.md](spec.md).

**Next command**: `/speckit-tasks` to generate the dependency-ordered `tasks.md`.
