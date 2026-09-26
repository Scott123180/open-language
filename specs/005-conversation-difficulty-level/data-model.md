# Data Model: Conversation Difficulty Level

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

This feature adds **one column** and **no tables**. Everything else is fixed, in-code catalogue data.

---

## 1. `ConversationLevel` (in-code enumeration)

Module: `backend/app/conversation_levels/catalog.py`, exported from `app.conversation_levels`.

| Value | Order | Label | CEFR label |
|---|---|---|---|
| `beginner` | 0 | Beginner | A1 |
| `elementary` | 1 | Elementary | A2 |
| `intermediate` | 2 | Intermediate | B1 |
| `natural` | 3 | Natural | No limit |

- A `StrEnum`. Its string values are the stored and wire values.
- `DEFAULT_CONVERSATION_LEVEL = ConversationLevel.NATURAL` (FR-009).
- The order is the declaration order. Nothing sorts by label.
- The set is closed (spec Key Entities: learners cannot define levels).

## 2. `LevelDescriptor` (value object, one per level)

Frozen, slotted dataclass. `LEVEL_CATALOG: Mapping[ConversationLevel, LevelDescriptor]` holds all
four in order.

| Field | Type | Notes |
|---|---|---|
| `level` | `ConversationLevel` | |
| `label` | `str` | Shown in both controls |
| `cefr_label` | `str` | "A1", "A2", "B1", "No limit" (FR-002) |
| `description` | `str` | One plain-language sentence (FR-002), e.g. Beginner: "Very short, simple sentences — like talking with a young child." |
| `limits` | `SpeechLimits \| None` | `None` exactly when `level is NATURAL` (FR-004) |

**Invariant** (validated in `__post_init__`): `limits is None` ⇔ `level == NATURAL`. A Natural
descriptor with limits, or a limited level without them, cannot be constructed.

## 3. `SpeechLimits` (value object)

The limits of spec FR-003 as data. The renderers turn it into instruction text (research R4, R5).

| Field | Type | Beginner | Elementary | Intermediate | Used for |
|---|---|---|---|---|---|
| `max_sentences_per_reply` | `int` | 2 | 3 | 4 | partner only |
| `max_words_per_sentence` | `int` | 8 | 12 | 20 | partner + learner text |
| `sentence_joining` | `str` | one idea per sentence | simple connectors only (and, but, because) | at most one subordinate clause | partner + learner text |
| `tenses` | `str` | present tense only | present, simple past, near future ("going to" + verb) | all common indicative tenses; subjunctive only in fixed everyday phrases | partner + learner text |
| `vocabulary_rank` | `int` | 500 | 1,500 | 3,000 | partner + learner text |
| `idioms` | `str` | none | none | common, widely understood idioms only | partner + learner text |
| `questions` | `str` | one easy yes/no or either/or question | one simple open question | as the conversation needs | partner only |

**Invariants**: all integers are positive. `max_words_per_sentence` and `vocabulary_rank` strictly
increase from Beginner to Intermediate. A catalogue unit test pins this, since SC-003 depends on it.

## 4. Rule rendering (pure functions, public)

| Function | Returns | At Natural |
|---|---|---|
| `with_partner_speech_rules(prompt: str, level: ConversationLevel) -> str` | `prompt`, a blank line, and the partner-speech rules block | `prompt` unchanged, byte for byte (R3) |
| `with_learner_text_rules(prompt: str, level: ConversationLevel) -> str` | `prompt`, a blank line, and the learner-text rules block | `prompt` unchanged, byte for byte |

- Both are pure: no I/O and no settings lookup. The caller passes the level.
- The partner block always carries the precedence line, the ceiling rule (FR-005), the two
  exceptions (FR-012), answer-the-substance (FR-013), and simplify-on-request (FR-014).
- Neither block mentions the native language, so FR-015's rule stays the only statement about it.
- The learner-text block is worded for any caller. It limits "the target-language words the learner
  will say or read" and states that explanations in any other language are not limited. That one
  wording serves suggestions, phrasings, and the helper, whose phrase is limited while its
  explanation is not (research R6). No renderer takes a caller-specific parameter.

## 5. `AppSettings` / `AppSettingsRecord`: one new field

| Layer | Change |
|---|---|
| `app_settings` table | `conversation_level VARCHAR(12) NOT NULL DEFAULT 'natural'`, added via a new entry at the end of `_ADDITIVE_COLUMNS` in [database.py](../../backend/app/database.py) |
| `AppSettings` ORM model | `conversation_level: Mapped[str]`, `String(12)`, default `DEFAULT_CONVERSATION_LEVEL.value` |
| `AppSettingsRecord` | `conversation_level: str = "natural"`, placed with the other defaulted fields |
| `_settings_to_record` | copies the field |
| `update_settings` | unchanged (generic `setattr`) |

- **Validation** happens at the API boundary: the pattern is derived from the `ConversationLevel`
  values (contract §2). Stored values are therefore always valid, and prompt-building call sites
  convert with `ConversationLevel(record.conversation_level)`, so a corrupt value raises rather than
  being guessed at.
- **Migration**: existing databases gain the column with `'natural'`, so behaviour is unchanged on
  upgrade (FR-009, R3).
- **Not stored**: the level is not recorded on `conversations` or `messages` (spec Assumptions: one
  learner-wide setting; R8).

## 6. Phrasing cache key (no schema change)

`learning_tool_results.input_selection` for `tool_type = alternative_phrasing`:

| Level | `input_selection` |
|---|---|
| Natural | the message content, unchanged (existing rows stay valid) |
| Other levels | `"[level:<value>] "` followed by the message content |

The key is built by one private helper in `routers/learning.py` (research R7). The other tool types
are unchanged.

## 7. Session state (no model change, behaviour noted)

`SessionFingerprint.standing_prompt_digest` already covers the standing prompt. Because the level's
rules are part of that prompt, a level change produces a new digest, and `plan_session_use` returns
`Rebuild` on the next roleplay or helper turn. No new state and no transition logic are added. This
is how FR-008 is met (research R2).

```text
level = Beginner ──turn──▶ session S1 (digest d_B)
learner changes level to Elementary
next turn: expected digest d_E ≠ d_B ──▶ Rebuild: close S1, open S2 on saved history, reply at Elementary
```
