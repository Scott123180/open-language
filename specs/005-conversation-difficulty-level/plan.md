# Implementation Plan: Conversation Difficulty Level

**Branch**: `005-conversation-difficulty-level` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-conversation-difficulty-level/spec.md`

---

## Summary

Add a learner-wide **conversation level** — Beginner (≈ A1), Elementary (≈ A2), Intermediate (≈ B1),
or Natural (no limit) — that caps how complex the roleplay partner's Spanish (or any target
language) is. The level is a set of explicit, numeric speaking rules. They are appended to the
conversation's standing prompt, and to the prompts of the three learner aids that produce
target-language text: suggestions, alternative phrasings, and the expression helper.

The design leans on two things that already exist, which keeps it small:
- **Sessions already rebuild when their standing prompt changes.** The 004 session fingerprint
  includes a digest of the standing prompt. Putting the level there means a change takes effect on
  the next reply, for live Ollama and Claude sessions alike, with **no change** to the conversation
  engine, pool, or either provider (research R2).
- **Composition, not modification.** Rules are appended by
  `with_partner_speech_rules(prompt, level)` and `with_learner_text_rules(prompt, level)` around the
  existing, untouched prompt builders. At Natural both return the prompt byte-for-byte, so FR-004
  ("Natural = today") is a unit test rather than a judgement call, and upgrading disturbs nothing
  (research R3).

New pieces:
- a small `backend/app/conversation_levels/` domain module (catalogue and rule rendering);
- one `app_settings` column;
- one read-only endpoint serving the catalogue;
- a radio group on Settings;
- a compact `<select>` in the conversation header that saves instantly.

The one real risk is **adherence by `llama3.1:8b`**, the same risk that made 003 ship experimental.
A hand-run benchmark measures it (research R9), and the spec already says what happens if it falls
short.

---

## Technical Context

**Language/Version**: Python 3.12 (backend `.venv`; `requires-python >= 3.11`), TypeScript 5.4 /
React 18.3 (frontend)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0, `ollama` client (llama3.1), the `claude -p` adapter (004). **No
  new runtime dependencies.** One **dev-only** dependency: `wordfreq` 3.1.1 (verified current on
  PyPI), used only by the hand-run benchmark for SC-003 (research R9).
- Frontend: React 18, react-router-dom v6, Vitest + Testing Library, Playwright. **No new
  dependencies.**

**Storage**: SQLite (WAL, foreign keys ON). One additive column,
`app_settings.conversation_level VARCHAR(12) NOT NULL DEFAULT 'natural'`, via `_ADDITIVE_COLUMNS`.
No new tables. The phrasing cache key becomes level-qualified without a schema change (research R7).

**Testing**:
- pytest: unit, contract and integration; ≥ 90% coverage; the `benchmark` marker for the hand-run
  adherence benchmark.
- Vitest for components and hooks.
- Playwright E2E, mandatory for the two frontend changes.

**Target Platform**: Linux desktop, local-first. Ollama by default, Claude opt-in (004).

**Project Type**: Web application (FastAPI backend + Vite/React frontend).

**Performance Goals**:
- Steady state: no added round trips. The rules block is about 150 tokens of extra prompt, which
  Ollama's keep-alive prefix cache absorbs, so the first token arrives within 10% of Natural
  (SC-008).
- The first turn after a level change pays one session rebuild (research R2). For Claude that is a
  few seconds, the same cost 004 accepts for a model change.
- A level change from the chat header is one level-only `PUT` with no availability check
  (research R8).

**Constraints**:
- FR-015: the native-language exclusion rule stays first and unchanged.
- FR-004: Natural must be byte-identical to today's prompts.
- Principle VI: feature code must not reach into providers, so the level travels only in prompt
  text through `TurnRequest`.

**Scale/Scope**: one learner; 4 levels; 6 prompt-building call sites (roleplay open, message and
warm-up; suggestions; phrasing; helper); 2 UI controls.

*No NEEDS CLARIFICATION items remain. The spec's two were resolved in its Clarifications session,
and the design questions are settled in [research.md](research.md) R1–R12.*

---

## Spec interpretations

Points where the spec admits more than one reading. Each is resolved here so the choice can be
reviewed.

1. **SC-008 is a steady-state criterion.** "Under the same conditions" is read as "same level on
   both sides of the comparison", so the one-off rebuild on the first turn after a change is
   excluded and measured separately (quickstart §5). The alternative, per-turn guidance to avoid the
   rebuild, was rejected in research R2.
2. **Gentle-mode recasts need no change to `corrections/`.** The recast restates the learner's own
   sentence, corrected. The words it adds are ones the learner just used, which FR-012(b)
   explicitly permits. The partner's surrounding reply is governed by the standing prompt like any
   other reply, which satisfies FR-018's "restatement MUST follow the level".
3. **FR-017, "the expression helper's suggested phrase"**, limits only the target-language phrase.
   The native-language explanation after it is FR-018 output and is not limited (research R6).
4. **FR-010, "confirmed immediately"**, is met by the control showing the new value and announcing
   it once the save succeeds. The save is a single local write that finishes well under a second.
   If it fails, the control reverts and shows an alert rather than keeping an unsaved value on
   screen.

---

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design; the result is at the
bottom of this section.*

| Principle | Status | How this design satisfies it |
|---|---|---|
| **I. Clean Code**: ≤ 20-line functions, intention-revealing names, no magic values | ✅ | Every limit is a named field of a `SpeechLimits` value object in one catalogue (data-model §3). The renderers are small pure functions. Four touched router functions are at or over the limit today and are brought under it; see *Function-length plan* below. |
| **II. SOLID: SRP** | ✅ | The catalogue says *what* each level allows. The renderers say *how that is phrased* to a model. The routers say *where* it applies. Storage persists one string. |
| **II. SOLID: OCP** | ✅ | No existing prompt builder is edited. Rules are composed around them (research R10). A fifth level is one catalogue entry, with no change to any caller. |
| **II. SOLID: LSP** | ✅ | No subtype contracts change. `TurnRequest`, `SessionFingerprint` and both providers are untouched. |
| **II. SOLID: ISP** | ✅ | Callers import only `with_partner_speech_rules` or `with_learner_text_rules`. Neither has to know about the other rendering or the catalogue internals. |
| **II. SOLID: DIP** | ✅ | The level reaches routers through the existing `get_app_settings` dependency. The renderers take the level as an argument and never read settings themselves. |
| **III. TDD (non-negotiable)** | ✅ | The catalogue invariants, both renderers, and the Natural byte-identity are pure and testable before any wiring. Every task in `tasks.md` will lead with its failing test. |
| **≥ 90% coverage, zero skipped tests** | ✅ | The benchmark is *deselected* by marker (existing `-m 'not benchmark …'` addopts), not skipped. That is the established 003 pattern. |
| **IV. One primary action per screen** | ✅ | Settings: the primary action stays Save, and the level is one more fieldset. Chat: the primary action stays Send, and the level `<select>` is styled secondary (FR-010). |
| **IV. Immediate feedback** | ✅ | The header control shows the new value and announces it via a polite live region. A failed save reverts with `role="alert"` (contract §5). |
| **IV. Plain-language, what-to-do-next messages** | ✅ | The announcement says when the change applies ("from the next reply"). Each level has a one-sentence plain description (FR-002). |
| **IV. Accessibility** | ✅ | A native `<select>` and radios (keyboard- and screen-reader-accessible without custom ARIA), `aria-describedby` for descriptions, a ≥ 44 px hit area, and design-system tokens only. A manual check is in quickstart §5. |
| **V. Compartmentalization** | ✅ | `app.conversation_levels` exposes a five-name public interface (research R10). Routers import only from the package root. It owns no tables and imports no other domain. |
| **V. Abstractions before implementations** | ✅ | No new extension point is needed: the level set is closed (spec Key Entities). The existing seams (session fingerprint, `get_app_settings`) are reused rather than duplicated. |
| **V. No feature-flag / if-debug guards** | ✅ | The level is a learner preference turned into rules once, at the prompt-building boundary. Nothing branches on the level string in domain logic, and Natural is data (`limits=None`), not a special case in callers. |
| **VI. Provider independence** | ✅ | No provider code changes. The level travels as prompt text through the provider-neutral `TurnRequest`. It works identically on Ollama and Claude and survives a provider switch (FR-016). No new data leaves the machine beyond what the selected provider already receives. |
| **Playwright E2E for frontend changes** | ✅ | New `conversation-level.spec.ts`; `settings.spec.ts` and `chat.spec.ts` extended; new fixtures (contract §5). |
| **Linting (ruff, black, ESLint, Prettier)** | ✅ | No tooling change. |

**Initial gate: PASS**, with two recorded Complexity Tracking items (the long React page components).

### Function-length plan (Boy Scout, quality gate)

Measured on `master` @ `19cda34`. These are the router functions this feature modifies that are at
or over 20 lines:

| Function | Today | Plan |
|---|---|---|
| `get_suggestions` ([chat.py:399](../../backend/app/routers/chat.py)) | ~35 lines | Extract `_parse_numbered_suggestions(text, count)` and build the prompt in a helper. |
| `warm_session` (chat.py:210) | ~20 | Adding the settings dependency pushes it over. Extract `_start_warming(engine, provider, key, prompt, history)`. |
| `chat_helper` (chat.py:443) | ~19 | Adding the settings dependency pushes it over. Extract `_helper_turn_request(req, stored, level)`. |
| `alternative_phrasing` ([learning.py:86](../../backend/app/routers/learning.py)) | ~19 | Adding the level key pushes it over. Extract `_phrasing_cache_key(content, level)`, which is needed anyway (research R7). |

`_roleplay_context` (11 lines) and `_standing_roleplay_prompt` (10 lines) gain a parameter and stay
well under the limit.

### Post-Phase-1 re-evaluation: **PASS**

The design added nothing that weakens a row above:
- the contracts confirm that no provider or engine file changes (Principle VI);
- the data model confirms that the only schema change is additive (storage conventions);
- the quickstart gives every Principle IV claim a concrete manual check.

Research R12 *reduces* existing debt by carrying out 004's deferred `Settings.tsx` split.

---

## Project Structure

### Documentation (this feature)

```text
specs/005-conversation-difficulty-level/
├── spec.md              # input (clarified 2026-09-26)
├── plan.md              # this file
├── research.md          # Phase 0: R1–R12
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── api.md           # Phase 1
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 (/speckit-tasks; NOT created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── conversation_levels/                # NEW domain module: no tables, no router
│   │   ├── __init__.py                     # public: ConversationLevel, DEFAULT_CONVERSATION_LEVEL,
│   │   │                                   #   LEVEL_CATALOG, with_partner_speech_rules,
│   │   │                                   #   with_learner_text_rules
│   │   ├── catalog.py                      # ConversationLevel, LevelDescriptor, SpeechLimits, LEVEL_CATALOG
│   │   └── rules.py                        # the two pure renderers (research R4, R5)
│   ├── database.py                         # + one _ADDITIVE_COLUMNS entry
│   ├── models/app_settings.py              # + conversation_level
│   ├── services/storage/base.py            # + AppSettingsRecord.conversation_level
│   ├── services/storage/sqlite.py          # + copy in _settings_to_record
│   ├── routers/settings.py                 # + field on request/response; + GET /settings/conversation-levels
│   ├── routers/chat.py                     # level into roleplay standing prompt (open/message/warm),
│   │                                       #   suggestions, helper; function-length extractions
│   └── routers/learning.py                 # phrasing prompt + level-qualified cache key
│   # NOT modified: prompts/templates.py, services/conversation/*, services/llm/*, corrections/*
├── pyproject.toml                          # + wordfreq in [dev] only
└── tests/
    ├── unit/conversation_levels/           # catalogue invariants, renderers, Natural byte-identity
    ├── contract/                           # settings + conversation-levels response shapes
    └── integration/
        ├── conversation_levels/
        │   ├── test_level_in_prompts.py    # every call site; rebuild on change; phrasing cache keys
        │   ├── evaluation_set.py           # 4 scenarios × 5 learner turns (research R9)
        │   └── test_level_benchmark.py     # @benchmark, hand-run (SC-001 – SC-004)
        └── ...                             # existing settings / chat tests extended

frontend/
├── src/
│   ├── services/api.ts                     # + ConversationLevelId, ConversationLevelOption,
│   │                                       #   getConversationLevels(), AppSettings.conversation_level
│   ├── components/settings/
│   │   ├── useConversationLevels.ts        # NEW hook (shared by both controls)
│   │   ├── ConversationLevelFieldset.tsx   # NEW (Settings screen)
│   │   ├── useSettingsForm.ts              # NEW: state/load/save moved out of Settings (research R12)
│   │   └── *Fieldset.tsx / *Field.tsx      # NEW: existing sections extracted unchanged (research R12)
│   ├── components/chat/
│   │   └── ConversationLevelControl.tsx    # NEW (header <select>, saves on change)
│   ├── pages/Settings.tsx                  # becomes a layout of section components
│   └── pages/Chat.tsx                      # + one element in the header
└── e2e/
    ├── conversation-level.spec.ts          # NEW
    ├── settings.spec.ts                    # extended
    ├── chat.spec.ts                        # extended
    └── fixtures.ts                         # + mockConversationLevels; settings mock + conversation_level
```

**Structure Decision**: the existing web-application layout (`backend/app`, `frontend/src`). The new
backend code goes in a sibling domain module, as `corrections/` did in 003. Frontend components go
in the existing `components/settings/` and `components/chat/` folders. Colocated `*.test.tsx` files
follow the existing convention and are omitted from the tree.

### Suggested phase order (for `/speckit-tasks`)

1. **Foundation**: the `conversation_levels` module (catalogue and renderers), the settings
   column, the API field and the catalogue endpoint. This blocks every story.
2. **Settings split (research R12)**: a behaviour-preserving refactor under the existing tests,
   done before any level UI so the new fieldset lands on the split page. It is independently
   droppable. Dropping it means adding the fieldset to today's `Settings` and a new Complexity
   Tracking row.
3. **US1 (P1)**: roleplay standing prompt at open, message and warm-up; the benchmark harness;
   the Settings fieldset. This is the MVP, and the benchmark is run here, before anything else is
   built on the adherence assumption.
4. **US2 (P2)**: the header `ConversationLevelControl`, the rebuild-on-change integration test, and
   E2E.
5. **US3 (P3)**: suggestions, phrasing (with the cache key) and the helper.
6. **Polish**: docs (`docs/architecture.md`, and `docs/design-system.md` if the header control adds
   a pattern), the accessibility check, and quickstart validation.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `Chat` component in `frontend/src/pages/Chat.tsx` stays over 20 lines (~518 today) while this feature modifies it | The change is one import and one `<ConversationLevelControl />` element in the header. The control loads its own state and saves itself, so `Chat` gains no state, effects or handlers. | Splitting `Chat` (streaming, recording, feedback, audio, helper) is the large refactor 004 already recorded as a follow-up ("extract `useChatStream` and `useRecorderFlow`"). Its trigger has not been reached, and it would put E2E risk unrelated to levels into this diff. It stays tracked as 004 left it. |
| After the R12 split, the `Settings` page body is still a JSX layout of about 30 lines | The page becomes declarative composition only: one `useSettingsForm()` call and an ordered list of section components, with no logic, state or handlers. | Nesting the layout inside wrapper components just to reach 20 lines would add indirection without separating any responsibility. The function-length rule exists to split *logic*, and none is left in the page. |
