# Phase 1 Data Model: Corrective Feedback Mode

**Branch**: `003-corrective-feedback-mode` | **Date**: 2026-08-25 | **Plan**: [plan.md](plan.md)

Two new tables owned by the `corrections` domain module, three additive columns on existing tables.
No existing column changes type, and no existing row is rewritten — feature 003 is purely additive,
so an existing database upgrades in place and Off mode reads exactly as it did before (FR-002).

---

## Entity map

```text
conversations (existing, UNMODIFIED)
   │ 1
   ├──────── 0..1  conversation_correction_state      ← NEW: the Strict pause (FR-018/027/029)
   │ 1
   └──────── 0..*  messages (existing, +2 columns)
                      │ 1
                      └── 0..2  message_feedback      ← NEW: corrections + repeat requests

app_settings (existing, +1 column)  ← correction_mode: the learner-level preference (FR-001/002/003)
```

---

## NEW: `message_feedback`

One app note attached to exactly one learner-authored message. Covers both the spec's **Correction**
entity and the FR-027 repeat request, discriminated by `kind` (see [plan.md](plan.md) → Spec
interpretations #2).

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | INTEGER PK | no | autoincrement | |
| `message_id` | INTEGER FK → `messages.id` | no | — | `ON DELETE CASCADE`, indexed |
| `kind` | VARCHAR(20) | no | — | `correction` \| `repeat_request` |
| `category` | VARCHAR(20) | yes | NULL | correction only: `conjugation` \| `agreement` \| `word_choice` \| `word_order` |
| `error_fragment` | TEXT | yes | NULL | correction only: the learner's words that were wrong |
| `corrected_text` | TEXT | yes | NULL | correction only: the fixed sentence (FR-014) |
| `explanation` | TEXT | no | — | correction: what was wrong, in the native language (FR-015). repeat_request: the ask-to-repeat text |
| `mode` | VARCHAR(10) | no | — | `gentle` \| `strict` — the mode that produced it |
| `rank` | INTEGER | no | 0 | 0 or 1; ordering by impact on comprehension (FR-008) |
| `created_at` | DATETIME(tz) | no | `now(UTC)` | |

**ORM**: `MessageFeedback` in `backend/app/corrections/models.py`, with `FeedbackKind`,
`ErrorCategory`, and `CorrectionMode` as `str`-valued `enum.Enum` mapped through SQLAlchemy
`Enum(...)`, matching the `MessageRole` / `InputSource` pattern in
[models/message.py](../../backend/app/models/message.py).

### Validation rules

| Rule | Source |
|---|---|
| At most 2 rows with `kind='correction'` per `message_id` | FR-008 |
| At most 1 row with `kind='repeat_request'` per `message_id` | FR-027 |
| A message never carries both kinds — a low-confidence message is never corrected | FR-010a |
| `kind='correction'` ⇒ `category`, `error_fragment`, `corrected_text` all non-null | FR-014 |
| `kind='repeat_request'` ⇒ those three are null and `mode='strict'` | FR-028 |
| `explanation` is non-empty after stripping | FR-014 |
| `rank` is 0 for the first correction, 1 for the second | FR-008 |
| Rows attach only to messages with `role='user'` | FR-019 |

Enforced in the service layer and asserted in `tests/unit/corrections/`. The two-correction cap is
additionally enforced in the evaluator's parser, so it holds even when the model returns more
(research.md R6).

### Lifecycle

Insert-only. Rows are never updated and never deleted except by cascade when the conversation is
deleted. FR-004 — a mode change must not alter feedback already in the transcript — is satisfied
because no code path rewrites an existing row.

---

## NEW: `conversation_correction_state`

The Strict pause, one row per conversation, created lazily on the first Strict evaluation. Owned by
the corrections module so the core `Conversation` model stays untouched (research.md R7).

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `conversation_id` | INTEGER PK, FK → `conversations.id` | no | — | `ON DELETE CASCADE`; PK is the FK (strict 1:1) |
| `consecutive_corrected_attempts` | INTEGER | no | 0 | 0..2, capped by `MAX_CONSECUTIVE_CORRECTED_ATTEMPTS` |
| `awaiting_clarification` | BOOLEAN | no | false | true while an FR-027 repeat request is outstanding |
| `updated_at` | DATETIME(tz) | no | `now(UTC)` | `onupdate` |

**Derived, not stored**: `awaiting_retry = consecutive_corrected_attempts > 0 AND the conversation's
last message has role='user'`. Computed in `CorrectionPauseTracker` and returned by the API; never
persisted, so it cannot disagree with the counter it comes from.

### State machine (`CorrectionPauseTracker`)

Evaluated once per learner message, in Strict mode only. Gentle and Off never read or write this row.

| Current state | Incoming learner message | Action | Next state |
|---|---|---|---|
| attempts = 0..1, not awaiting clarification | low-confidence | ask to repeat; **no reply**; no correction | attempts unchanged, `awaiting_clarification = true` |
| any, `awaiting_clarification = true` | low-confidence again | no repeat request, no correction, **reply normally** | `awaiting_clarification = false` (FR-027: at most once per message) |
| any, `awaiting_clarification = true` | normal confidence | clear the flag, then evaluate as usual | `awaiting_clarification = false`, then the rows below |
| attempts = 0..1 | correctable error found | emit correction; **no reply** (FR-016) | attempts + 1 |
| attempts = 0..1 | no correctable error | reply normally | attempts = 0 |
| **attempts = 2** | anything | skip evaluation entirely; **reply normally** (FR-018) | attempts = 0 |
| any | mode changed to Off or Gentle | that mode's strategy never reads this row; the pause is inert | unchanged until Strict resumes |

The final row is the FR-018 cap: after two consecutive corrected attempts the third message is
answered whatever it contains, including a brand-new error, because the counter counts *attempts*
rather than matching errors to one another. This is what makes SC-006 (no deadlocks) structural
rather than probabilistic.

The "mode changed to Off" row implements the spec's edge case: FR-004 makes the change take effect
from the next message, so that message is answered normally, which is indistinguishable from the
pause having been cleared.

---

## MODIFIED: `app_settings` (+1 column)

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `correction_mode` | VARCHAR(10) | no | `'off'` | `off` \| `gentle` \| `strict` |

Migration: `_add_column_if_missing(conn, "app_settings", "correction_mode VARCHAR(10) NOT NULL
DEFAULT 'off'")`. The `NOT NULL DEFAULT 'off'` is what makes FR-002 true for existing installations —
every database that predates this feature comes back Off.

Propagates to `AppSettingsRecord`, `_settings_to_record()`, `SettingsResponse`,
`UpdateSettingsRequest` (validated `pattern="^(off|gentle|strict)$"`, mirroring how
`whisper_model` is constrained), and the frontend `AppSettings` type.

---

## MODIFIED: `messages` (+2 columns)

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `transcription_confidence` | REAL | yes | NULL | 0.0–1.0, aggregated per research.md R1. NULL for typed messages and for assistant messages |
| `is_low_confidence` | BOOLEAN | yes | NULL | classification at the time of the turn; NULL when confidence is NULL |

Both are additive and nullable, so every existing row stays valid and `MessageRecord` gains two
optional fields without breaking any consumer.

**How the value is produced**: `app/services/stt/confidence.py` filters out segments carrying no
speech (empty text, non-positive duration, `no_speech_prob > 0.6`), forces low-confidence when any
retained segment shows a repetition loop (`compression_ratio > 2.4`), and otherwise returns
`exp(Σ(avg_logprobᵢ × n_tokensᵢ) / Σ n_tokensᵢ)` over the retained segments. Token-count weighting is
used because `avg_logprob` is already a per-token mean. Full derivation and provenance of every
threshold: research.md R1.

**Three distinct meanings are stored, not two**:

| Stored | Meaning | Corrected? |
|---|---|---|
| `confidence = NULL` | no confidence information — typed input, or no segments at all | **yes**, evaluated normally |
| `confidence = 0.0` | text present but every segment looked like silence — hallucination-on-silence | no (FR-010a) |
| `confidence < 0.55` | genuinely unclear speech | no (FR-010a) |

The NULL row is load-bearing: typed input has no confidence and must never be gated by FR-010a. The
rule is `is_low_confidence = confidence is not None and confidence < threshold`, so NULL falls
through to normal evaluation while 0.0 does not.

**Why store the classification and not just derive it**: `LOW_CONFIDENCE_THRESHOLD` is configurable.
Storing the boolean keeps the historical record of *why a message was not corrected* stable if the
threshold is later tuned — the transcript should not silently re-interpret itself.

A confidence supplied alongside `input_source="keyboard"` is ignored and stored as NULL (research.md
R2) — the value is client-supplied, and this closes the only way it could be misused.

---

## Domain value objects (not persisted)

In `backend/app/corrections/` — the vocabulary the strategies speak, kept separate from the ORM so
domain logic never touches a SQLAlchemy session.

```text
CorrectionMode(str, Enum)      OFF | GENTLE | STRICT
FeedbackKind(str, Enum)        CORRECTION | REPEAT_REQUEST
ErrorCategory(str, Enum)       CONJUGATION | AGREEMENT | WORD_CHOICE | WORD_ORDER

FeedbackDraft   (frozen dataclass)  a note the strategy decided on, before persistence:
                                    kind, category, error_fragment, corrected_text,
                                    explanation, mode, rank

TurnPlan        (frozen dataclass)  one mode's decision for one turn:
                                    feedback: tuple[FeedbackDraft, ...]
                                    generate_reply: bool           ← False only for a flagged Strict turn
                                    reply_prompt_suffix: str|None  ← the Gentle recast instruction

PauseSnapshot   (frozen dataclass)  consecutive_corrected_attempts, awaiting_clarification,
                                    awaiting_retry (derived)
```

`TurnPlan` is the whole reason the chat router does not branch on mode strings: it receives one plan
object and acts on it identically regardless of which strategy produced it (Constitution V — no mode
guards inside domain logic).

---

## Requirements coverage

| Requirement | Where it is satisfied |
|---|---|
| FR-001, FR-003 | `app_settings.correction_mode`, persisted |
| FR-002 | `NOT NULL DEFAULT 'off'`; `OffCorrectionStrategy` touches neither new table |
| FR-004 | `message_feedback` is insert-only; mode is read per turn |
| FR-008 | ≤ 2 `correction` rows per message; `rank` orders them |
| FR-010, FR-010a | `messages.transcription_confidence`, `messages.is_low_confidence` |
| FR-014, FR-015 | `error_fragment`, `corrected_text`, `explanation` |
| FR-016 | `TurnPlan.generate_reply = False` ⇒ no assistant row is written at all |
| FR-018 | `consecutive_corrected_attempts` + the cap row of the state machine |
| FR-020 | Feedback lives outside `messages.content`; TTS reads only `content` |
| FR-022, FR-029 | Both tables are durable; `GET /corrections/conversations/{id}` replays them |
| FR-024, FR-025 | `learning_tool_results` is untouched — separate table, separate mechanism |
| FR-027, FR-028 | `kind='repeat_request'` + `awaiting_clarification` |

---

## Migration summary

Added to `_migrate_db()` in [database.py](../../backend/app/database.py):

```text
app_settings  + correction_mode VARCHAR(10) NOT NULL DEFAULT 'off'
messages      + transcription_confidence REAL
messages      + is_low_confidence BOOLEAN
```

`app.corrections.models` is imported in `init_db()` so `create_all()` creates `message_feedback` and
`conversation_correction_state`, following the `app.flashcards.models` precedent. Both new tables are
created by `create_all()`, not by `ALTER TABLE`, so no migration statement is needed for them.
