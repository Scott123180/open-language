# Interface Contracts: Conversation Difficulty Level

**Feature**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md)

All paths are under `/api`. Unless a section says otherwise, request and response shapes of existing
endpoints are unchanged. What changes is the text the model is instructed with.

---

## 1. `GET /api/settings/conversation-levels` (new)

Returns the level catalogue in order, easiest first. There are no parameters, and no availability
checks: the list is static.

**200**

```json
[
  {
    "level_id": "beginner",
    "label": "Beginner",
    "cefr_label": "A1",
    "description": "Very short, simple sentences — like talking with a young child."
  },
  { "level_id": "elementary", "label": "Elementary", "cefr_label": "A2", "description": "…" },
  { "level_id": "intermediate", "label": "Intermediate", "cefr_label": "B1", "description": "…" },
  { "level_id": "natural", "label": "Natural", "cefr_label": "No limit", "description": "…" }
]
```

| Guarantee | Test |
|---|---|
| Exactly the four levels, in `ConversationLevel` declaration order | contract test |
| `level_id` values equal the values accepted by `PUT /api/settings` | contract test (both are derived from `ConversationLevel`) |
| Never carries limits or prompt text; those are internal | contract test on the response keys |

## 2. `GET /api/settings` and `PUT /api/settings` (extended)

**`SettingsResponse`** gains:

```json
{ "conversation_level": "natural" }
```

**`UpdateSettingsRequest`** gains the optional field `conversation_level`, validated against a
pattern built from the `ConversationLevel` values (`^(beginner|elementary|intermediate|natural)$`).

| Case | Result |
|---|---|
| `{"conversation_level": "elementary"}` alone | **200**, stored, and the response shows `"elementary"`. Other settings are untouched. **No provider availability check runs** (research R8). |
| Absent or `null` | the stored level is unchanged |
| `{"conversation_level": "expert"}` | **422** (pattern validation), nothing stored |
| Database from before this feature | `GET` returns `"natural"` (FR-009) |

## 3. Roleplay endpoints (behaviour change only)

`POST /api/chat/{id}/open`, `POST /api/chat/{id}/message`, `POST /api/chat/{id}/session`

- Each reads the **current** `conversation_level` when the request arrives, and builds the standing
  prompt as `with_partner_speech_rules(build_roleplay_system_prompt(...), level)`.
- `/session` (warm-up) builds the standing prompt through the **same** function, so the session it
  warms has the fingerprint the next turn expects (research R8).
- SSE frames, status codes and error handling are unchanged.

| Guarantee | Requirement | Test level |
|---|---|---|
| At Natural, the standing prompt equals the pre-feature prompt exactly | FR-004 | unit |
| At other levels, the rules block comes after the scenario and character text, and the CRITICAL LANGUAGE RULE is still first | FR-015, spec edge case (custom prompt) | unit |
| A level change between two turns reaches the next `TurnRequest`, and the pool rebuilds the session | FR-008, SC-005 | integration (fake session provider) |
| A reply already streaming finishes at the level its request started with | spec edge case | integration |
| The opening message uses the level | FR-011, US1 AS1 | integration |
| Gentle-mode guidance still arrives unchanged in `TurnRequest.guidance` | FR-018 | integration |

## 4. Learner aids (behaviour change only)

| Endpoint | Change | Requirement |
|---|---|---|
| `POST /api/chat/{id}/suggestions` | prompt = `with_learner_text_rules(build_suggestion_prompt(...), level)` | FR-017 |
| `POST /api/learning/phrasing` | prompt = `with_learner_text_rules(build_phrasing_prompt(...), level)`, and the cache key is level-qualified (data-model §6) | FR-017, research R7 |
| `POST /api/chat/helper` | helper standing prompt = `with_learner_text_rules(build_helper_system_prompt(...), level)`, scoped to the target-language phrase | FR-017, FR-018, research R6 |
| `POST /api/learning/grammar`, `/translation`, `/word-lookup` | **no change** | FR-018 |

| Guarantee | Test level |
|---|---|
| At Natural, each aid's prompt equals its pre-feature prompt | unit |
| Learner-text rules never include the reply-length or question rules | unit (catalogue renderer) |
| A phrasing cached at Natural is not served at Beginner, and one cached at Beginner is served again at Beginner | integration |
| At Natural, a phrasing cached before this feature is still a cache hit | integration |

## 5. Frontend components

### `useConversationLevels()` (hook, `frontend/src/hooks/useConversationLevels.ts`)

Returns `{ levels: ConversationLevelOption[], isLoading, error }` from contract §1. Shared by both
controls, so it lives in the shared `hooks/` folder rather than in either screen's components.

### `ConversationLevelFieldset` (Settings screen)

| Prop | Type |
|---|---|
| `levels` | `ConversationLevelOption[]` |
| `value` | `ConversationLevelId` |
| `onChange` | `(level: ConversationLevelId) => void` |

- A `<fieldset>` with the legend "Conversation level". Each radio's label shows the label and the
  CEFR label, and its description is linked via `aria-describedby`. This matches the correction-mode
  group.
- It doesn't save anything itself. The page's Save action saves it along with everything else.

### `ConversationLevelControl` (conversation screen header)

Takes no props. It loads its own state (settings and levels) and saves its own changes.

| Behaviour | Requirement |
|---|---|
| A native `<select>` with the accessible name "Level". Options read "Beginner (A1)" … "Natural". | FR-006, SC-006 |
| The selected level's one-sentence description is the select's accessible description (`aria-describedby`, visually hidden) | FR-002 (plan.md Spec interpretation 5) |
| Shows the stored level on mount | FR-010, US2 AS4 |
| On change: level-only `PUT /api/settings`. The control is disabled while saving. A polite live region announces "Level set to {label}. It applies from the next reply." | FR-008, FR-010 |
| On failure: reverts to the previous value and shows the error with `role="alert"` | Constitution IV |
| Styled as secondary (muted text, no fill) using design-system tokens only; hit area ≥ 44 × 44 px | FR-010, Constitution IV |
| Stays enabled while a reply is streaming | spec edge case (the change applies from the next reply) |

### Playwright (`frontend/e2e/`)

| Spec file | Covers |
|---|---|
| `conversation-level.spec.ts` (new) | changing the level in the chat header sends `PUT` with only `conversation_level`; the announcement appears; a failed save reverts |
| `settings.spec.ts` (extended) | the level fieldset renders the four levels from the mocked catalogue; Save sends `conversation_level` |
| `chat.spec.ts` (extended) | the header shows the stored level; existing flows are unaffected |
| `fixtures.ts` | `mockConversationLevels`, and `conversation_level` added to the settings mock |
