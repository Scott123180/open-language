# Implementation Plan: LLM Provider Selection

**Branch**: `004-llm-provider-selection` | **Date**: 2026-09-25 (revised same day for sessions) |
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-llm-provider-selection/spec.md`

---

## Summary

The language-model seam already exists. Every feature depends on `LLMProvider` or
`StructuredLLMProvider`, and only `services/factory.py` names Ollama. This feature does four things
behind and around that seam:

1. **Provider registry.** The saved `app_settings.llm_provider` decides per request which
   implementation serves it (research R-11, R-12).
2. **Claude provider.** `ClaudeCodeLLMProvider` runs the learner's signed-in `claude -p`, so usage
   draws on their Claude plan. Every invocation is stripped to a plain chat model: no tools, no
   personal or project configuration, no saved session, a replaced system prompt, an empty working
   directory, and an environment scrubbed of anything that could switch billing to an API key
   (R-2, R-3). All of this was verified against the live CLI.
3. **Conversation sessions.** The provider contract gains `SessionCapableProvider` and
   `ConversationSession`. A new `ConversationEngine` owns "produce the next reply for this
   conversation" for roleplay and the expression helper, through a bounded, expiring
   `ConversationSessionPool`. Saved history remains the source of truth: a session is reused only
   when its synced message ids line up with storage, and is rebuilt otherwise (R-15). Measured
   payoff: Claude's later turns drop from 1.5–2.4 s to 0.7–0.8 s (R-14). Ollama stops unloading
   mid-conversation, which removes a 4–49 s stall after five idle minutes (R-13).
4. **Surfacing and docs.** Provider errors reach the learner (R-10), the learner picks Claude's
   model and effort, and the docs are repositioned to "provider-agnostic, local by default".

Reply delivery stays batched, by the learner's decision: sessions change where tokens come from, not
how they reach the screen.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.4 / React 18.3 (frontend)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0, `ollama` (now through an injected `ollama.Client`). **No new
  Python dependencies.** Claude is reached through the `claude` executable (Claude Code 2.1.283
  verified), which is an optional runtime prerequisite and not a package dependency.
- Frontend: React 18. The providers list loads with the same `useEffect` + `api.*` pattern that
  `Settings.tsx` already uses for settings and voices. **No new dependencies.**

**Storage**: SQLite. Two additive columns, `app_settings.llm_provider` and `app_settings.llm_effort`,
via `_add_column_if_missing()` ([data-model.md](data-model.md) §1). Sessions are in memory only.

**Testing**: pytest (≥ 90% coverage gate), Vitest + Testing Library, Playwright. Two shared contract
suites (provider and session) are each parametrised over both providers. A new opt-in `claude_live`
marker is deselected by default, like 003's `benchmark`.

**Target Platform**: Linux desktop, single learner. Local by default; Claude optional.

**Project Type**: Web application (FastAPI backend + Vite/React SPA on one port).

**Performance Goals** (all measured during research):

| Target | Measured |
|---|---|
| Claude, first reply of a new or rebuilt session ≤ 5 s (SC-004) | 1.2–1.4 s (plus ~0.6 s process start) |
| Claude, later session turns ≤ 2 s (SC-004) | 0.68–0.82 s |
| Ollama reply after ≤ 25 min idle ≤ 3 s (SC-004a) | 0.6–0.9 s warm; the 4.2–49 s reload is what sessions prevent |
| Claude structured correction inside the 8 s budget | 1.67 s |
| Availability check on Settings load ≤ 0.2 s | 0.13 s, no plan usage |

**Constraints**: API keys are never used or stored, `--bare` is never passed, and every Claude
invocation is preceded by a plan-sign-in pre-flight check (FR-010/010a/011);
Claude calls are fully isolated (FR-012–015); there is no silent cross-provider fallback (FR-029);
at most 3 live sessions (~240 MB each for Claude), closed by a 60 s reaper once idle for 30 min;
no `claude` process outlives the backend, or its correction budget when it is a correction
(FR-019); every reply is produced from a context equivalent to saved history (FR-S03).

**Scale/Scope**: 2 providers × (3 one-shot capabilities + sessions); about 12 one-shot LLM call
sites untouched; 3 conversational call sites moved onto the engine; 2 frontend screens (Settings,
Chat warm-up call).

*(No NEEDS CLARIFICATION items remain. See [research.md](research.md).)*

---

## Spec corrections made during planning

Research found places where the spec assumed behaviour the app doesn't have. The spec was edited,
rather than the plan quietly diverging from it:

1. **"Replies stream in progressively"**: false for both providers. Every `chat_stream` caller wraps
   it in `list(...)` (R-9). The learner then chose to keep batched delivery, and the spec's
   Assumptions now say so.
2. **"Stop the process when the learner navigates away"**: unobservable under batched delivery.
   FR-019 now requires a hard maximum duration plus stopping on early iterator close.
3. **"Ollama keeps a free-text model field"**: it was a hard-coded dropdown missing the backend
   default `llama3.1:8b` (R-12). It is now a catalogue list that preserves an unlisted saved value.
4. **"Sessions"**: the first plan treated statelessness as a Claude-only cost. Research R-13 showed
   neither provider has sessions today, and measured what each gains. Story 5 and FR-S01–S13 were
   added, and FR-019a (the effort setting) followed from the learner's question.
5. **R-5's claim that stream-json input can't carry assistant turns** was untested and wrong. The
   corrected finding (R-14) is what makes one-reply rebuilds possible.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below). Checked against
constitution v1.2.0, which added Principle VI and the 20-line function gate during this feature's
planning.*

| Principle | Status | How |
|---|---|---|
| **I. Clean Code**: ≤ 20-line functions, named constants, no magic strings | ✅ | Flags, effort levels, timeouts, pool limits, scrubbed-variable prefixes, and user messages are named constants. The Claude provider is split into single-purpose modules, and the pool's reuse/rebuild decision is a pure function over (fingerprint, synced ids, saved history) |
| **II. SOLID** | ✅ | **S**: argv building, prompt rendering, event parsing, process I/O, availability, session bookkeeping, and pooling are separate units. **O**: a third provider is a catalogue entry, a registry builder, and a session class. **L**: two contract suites run over both providers. **I**: one-shot (`LLMProvider`), structured (`StructuredLLMProvider`), and session (`SessionCapableProvider`) capabilities are three separate ABCs. **D**: `ClaudeCodeRunner`, `ollama.Client`, and the pool are injected, and routers depend on `ConversationEngine`, never on a provider class |
| **III. TDD** (non-negotiable) | ✅ | Every task in `/speckit-tasks` starts with a failing test. Subprocess behaviour is tested through NDJSON fixtures that reproduce the recorded event shapes (trimmed to parsed fields), and interactive sessions through a scripted `InteractiveProcess` fake. The default suite needs neither `claude` nor Ollama |
| **IV. Simple UI** | ✅ | Settings keeps one primary action (Save). Provider is a labelled radio group, with model below it and effort (Claude only) below that. The disabled Claude option carries a visible reason tied with `aria-describedby`. The privacy notice uses the existing warning-note pattern. Errors say what to do next (R-7). Warm-up is invisible |
| **V. Extensibility & Compartmentalization** | ✅ | Provider ids exist only in `PROVIDER_CATALOG` and `build_llm_provider()`, mirroring the 003 `build_correction_strategy()` seam. `services/conversation/` exports `ConversationEngine` and its value objects only. `claude_code/` exports one provider class and one availability checker |
| **VI. Provider Independence** (added in constitution v1.2.0) | ✅ | **Interface**: features depend on `LLMProvider` / `StructuredLLMProvider` / `SessionCapableProvider` only, and `build_llm_provider()` is the single place a provider id becomes behaviour (FR-004, FR-S13). **Local default, cloud opt-in**: Ollama is the default for fresh and upgraded installs (FR-006), Claude is used only once selected, and selecting it shows what leaves the machine (FR-026). **No credentials**: authentication is delegated to Claude Code's own sign-in, and the availability endpoint returns only a reason code, never account fields (FR-010/011, R-8). **No silent fallback**: FR-029, with actionable failure messages (FR-028, R-7) |
| **Quality gates**: coverage, lint, E2E, a11y | ✅ planned | Playwright covers provider switching, effort visibility, the disabled state, the privacy notice, and the Chat warm-up request. A manual a11y check of Settings is a task |

**Gate result: PASS.**

### Post-design re-check

| Concern raised by the design | Resolution |
|---|---|
| FR-004/SC-008 say features must not change, yet `chat.py` changes substantially | The change moves provider-agnostic conversation mechanics (building message lists, running the stream, error frames) out of the router into `ConversationEngine`. After it, a third provider touches no router. SC-008 is judged on adding a *third* provider, which this makes true |
| Gentle mode's suffix moves from the system prompt into a per-turn `guidance` field. Does 003 behaviour change? | For Ollama the session re-applies it to the system prompt for that call only, so the prompt is byte-identical to today (R-13). The 003 integration suite (`test_chat_correction_modes.py`) runs unchanged as the regression guard |
| Long-lived child processes in a web server | Bounded (3), idle-expired (30 min), closed on conversation end and on lifespan shutdown, stderr to a file. A per-key lock prevents interleaved stdin writes |
| `claude_live` tests are deselected by default. Does that violate "zero skipped tests"? | Same mechanism as 003's `benchmark` marker: deselected, not skipped, documented in `pyproject.toml` |
| The v1.2.0 function-length gate (20 lines, new or modified functions) catches three existing functions this feature modifies: `open_chat` (69 lines), `send_message` (64), and `chat_helper` (42) in `routers/chat.py` | Moving message building, streaming, and error framing into `ConversationEngine` (R-17) is what brings them under 20. Each one becomes: build a `TurnRequest`, relay the engine's frames, persist. A task per router function checks the length. `_stream_reply` (29) is deleted, since the engine replaces it. Other long functions this feature doesn't touch stay as they are, per the gate's scope |
| `ConversationSession` has 7 methods. Is that an ISP concern? | Every method is used by the pool, the interface's only client. Splitting it would give that one client two halves of one object |
| *(Added after `/speckit-analyze`.)* The function-length gate also catches `_migrate_db` in `database.py`: 19 lines today, about 25 after two more `_add_column_if_missing` calls | Made data-driven: a module-level `_ADDITIVE_COLUMNS: tuple[tuple[str, str], ...]` of `(table, column definition)` pairs, and a loop. It stays under 20 lines however many columns later features add |
| *(Added after `/speckit-analyze`.)* The gate also catches the React function components this feature modifies: `Settings` in `pages/Settings.tsx` (~362 lines) and `Chat` in `pages/Chat.tsx` (~485 lines) | Both are recorded in Complexity Tracking below. This feature does not grow either one: provider fields move out of `Settings` into `LlmProviderFields`, and `Chat` gains one line (`void api.warmSession(convId)`). Every new component, hook, and handler this feature writes is ≤ 20 lines |
| *(Added after `/speckit-analyze`.)* Flashcard word info swallowed every exception (`llm_cache.py`), so a Claude failure there would show a fixed "unavailable" text instead of a next step (SC-007, Principle VI) | `get_or_generate` lets `LLMError` reach the shared 503 handler. The fill-in-the-blank sentence path stays fail-soft (spec edge case), narrowed from `except Exception` to `except LLMError` with a warning log |
| *(Added after `/speckit-analyze`.)* A correction that times out in `asyncio.wait_for` leaves its `claude` process running (FR-019) | `stream_lines` takes a per-call timeout, and `chat_json` passes the correction budget (research R-9) |
| *(Added after `/speckit-analyze`.)* Expiry on access alone leaves idle `claude` processes alive in an untouched app (FR-S06) | A lifespan reaper calls `engine.evict_idle()` every 60 s (research R-16) |
| *(Added after `/speckit-analyze`.)* A learner who re-signs Claude Code in with an API key would be billed on that account until they reopened Settings (SC-006) | An uncached pre-flight `auth status` check runs before every one-shot request and session spawn (FR-010a, research R-8) |

**Re-check result: PASS**, with two Complexity Tracking entries (below).

---

## Project Structure

### Documentation (this feature)

```text
specs/004-llm-provider-selection/
├── spec.md              # revised three times across specify/plan
├── plan.md              # this file
├── research.md          # Phase 0: measured behaviour, R-1…R-17
├── data-model.md        # Phase 1: 2 columns, value objects, session lifecycle
├── quickstart.md        # Phase 1: validation guide
├── contracts/api.md     # Phase 1: HTTP, provider/session interfaces, claude invocation
├── checklists/requirements.md
└── tasks.md             # Phase 2: /speckit-tasks (not created here)
```

### Source Code

```text
backend/app/
├── config.py                          # + claude_executable, claude_workdir, claude_log_dir,
│                                      #   claude_request_timeout_seconds, session_max_live,
│                                      #   session_idle_ttl_minutes
├── database.py                        # + llm_provider, llm_effort columns; _migrate_db made data-driven
├── main.py                            # + LLMError handler → 503; lifespan runs the session reaper
│                                      #   and closes the engine
├── flashcards/services/llm_cache.py   # word info lets LLMError reach the handler; fill-blank catches
│                                      #   LLMError only
├── models/app_settings.py             # + llm_provider, llm_effort
├── routers/
│   ├── chat.py                        # open/message/helper → ConversationEngine; + POST /chat/{id}/session
│   ├── conversations.py               # completing a conversation ends its session
│   └── settings.py                    # + provider/effort fields, GET /settings/llm-providers, validation
├── services/
│   ├── factory.py                     # registry-backed get_llm/get_structured_llm; + get_session_provider,
│   │                                  #   get_conversation_engine, get_availability_checkers
│   ├── storage/base.py, sqlite.py     # AppSettingsRecord.llm_provider, .llm_effort
│   ├── conversation/                  # NEW domain service
│   │   ├── __init__.py                # exports ConversationEngine, TurnRequest, SessionKey, SavedTurn
│   │   ├── session.py                 # ConversationSession, SessionCapableProvider ABCs, SessionKey,
│   │   │                              #   SavedTurn, TurnRequest, SessionFingerprint
│   │   ├── sync.py                    # plan_session_use(): pure reuse/rebuild decision (R-15)
│   │   ├── pool.py                    # ConversationSessionPool: LRU, TTL, evict_idle, per-key locks, retry-once
│   │   └── engine.py                  # ConversationEngine
│   └── llm/
│       ├── base.py                    # LLMError.user_message, LLMError.can_retry
│       ├── selection_types.py         # NEW leaf module: LLMSelection, effort constants
│       ├── catalog.py                 # NEW ProviderDescriptor, ModelOption, EffortOption, PROVIDER_CATALOG
│       ├── availability.py            # NEW ProviderAvailabilityChecker ABC, ProviderAvailability, AlwaysAvailable
│       ├── registry.py                # NEW build_llm_provider, ConfiguredLLMProvider, UnknownProviderError
│       ├── selection.py               # NEW resolve_llm_selection(): partial update + validation rules
│       ├── ollama.py                  # injected ollama.Client; implements SessionCapableProvider
│       ├── ollama_session.py          # NEW OllamaSession: in-memory turns, keep_alive, empty-preload warm-up
│       └── claude_code/               # NEW package; exports ClaudeCodeLLMProvider, ClaudeCodeAvailability
│           ├── __init__.py
│           ├── command.py             # ClaudeRequest, build_claude_argv(), build_session_argv(): pure
│           ├── transcript.py          # render_prompt() → RenderedPrompt; render_rebuild_turn()
│           ├── events.py              # NDJSON → text deltas / result; classify failures
│           ├── failures.py            # FailureKind, ClaudeCodeFailure(LLMError), user messages
│           ├── runner.py              # ClaudeCodeRunner / InteractiveProcess ABCs, subprocess impls
│           │                          #   (per-call timeout), scrubbed_environment()
│           ├── availability.py        # ClaudeCodeAvailability (claude auth status --json); also the
│           │                          #   provider's pre-flight guard (FR-010a)
│           ├── session.py             # ClaudeCodeSession: long-lived process, guidance block, rebuild rule
│           └── provider.py            # ClaudeCodeLLMProvider
backend/tests/
├── contract/service_interfaces/
│   ├── test_llm_provider_implementations.py        # NEW shared one-shot suite × 2 providers
│   ├── test_conversation_session_implementations.py # NEW shared session suite × 2 providers
│   └── test_provider_availability_checker.py       # NEW
├── fixtures/claude_code/                           # NEW: *.ndjson event recordings (stream ok, json ok,
│                                                   #   schema ok, auth failed, 404 model, rate-limit
│                                                   #   rejected, garbage, 3-turn session) and
│                                                   #   auth_status_*.json (signed in, API key, signed out)
├── support/                                        # NEW test doubles: claude_fixtures, scripted_claude_runner,
│                                                   #   stateless_session_provider, engine_overrides
├── unit/test_config.py                             # NEW: new Settings fields
├── unit/test_docs_positioning.py                   # NEW: SC-009 wording check on the three docs
├── unit/services/test_factory.py                   # NEW: get_llm / get_structured_llm / get_session_provider
├── unit/services/conversation/                     # NEW: session values, sync, pool, engine
├── unit/services/llm/                              # NEW: llm_error, catalog, registry, selection,
│                                                   #   ollama session, and claude_code/ (command, runner,
│                                                   #   interactive process, failures, transcript, events,
│                                                   #   provider, session, availability)
├── integration/routers/test_settings.py            # + provider/effort, providers endpoint, 422 rules
├── integration/routers/test_chat_sessions.py       # NEW: reuse across turns, rebuild after pool reset,
│                                                   #   strict pause merge, warm endpoint, complete closes
├── integration/test_llm_error_surface.py           # NEW: SSE user_message, JSON 503
├── integration/test_lifespan.py                    # NEW: reaper started and cancelled, engine closed
└── live/test_claude_code_live.py                   # NEW @pytest.mark.claude_live: isolation, recall, timing

frontend/src/
├── services/api.ts                    # + LlmProviderOption, getLlmProviders(), warmSession(), llm_provider/llm_effort
├── components/settings/               # NEW directory
│   ├── LlmProviderFields.tsx          # provider radios, model select, effort select, availability note, privacy notice
│   └── LlmProviderFields.test.tsx
├── pages/Settings.tsx                 # uses LlmProviderFields; LLM_OPTIONS removed; corrections warning reworded
└── pages/Chat.tsx                     # fire-and-forget warmSession() on mount for existing conversations
frontend/e2e/
├── fixtures.ts                        # + provider catalogue mocks (available / unavailable)
├── settings.spec.ts                   # + switch provider, effort only for Claude, disabled Claude, notice, 422
└── chat.spec.ts                       # + warm-up request fired on resume, not on a new conversation

README.md, CLAUDE.md, docs/architecture.md   # repositioning + sessions (FR-030/031)
```

**Structure Decision**: Web application layout, as used by 001–003. `services/conversation/` is a
new domain service: it has its own vocabulary (sessions, turns, sync) and one public class, the same
shape as `corrections/`, but it lives under `services/` because it has no tables or routes of its
own. `claude_code/` is an infrastructure adapter behind existing interfaces. The Settings form
fields move into `components/settings/` because `Settings.tsx` is already 389 lines.

---

## Implementation phases (input to `/speckit-tasks`)

| Phase | Delivers | Story | Checkpoint |
|---|---|---|---|
| 1. Foundation | `LLMError.user_message`/`can_retry` + 503 handler; flashcard word info onto the handler; catalogue; registry (Ollama only); injected client + host; `llm_provider`/`llm_effort` columns + record; data-driven `_migrate_db` | US1 | Behaviour identical apart from error texts, seam real. Merge-safe |
| 2. Session core | `conversation/` ABCs, `sync`, `pool` (+ reaper), `engine`; `OllamaSession`; session contract suite (Ollama); chat routers moved onto the engine; warm endpoint; complete-closes-session | US5 (Ollama), US1 | All 001/003 integration tests pass with only their dependency-override wiring changed (assertions untouched). Ollama stays loaded mid-conversation |
| 3. Claude adapter (one-shot) | `command`, `transcript`, `events`, `failures`, `runner` (per-call timeout), `provider` (pre-flight guard, correction deadline); one-shot contract suite × 2 | US2, US3 | Isolation invariants are the first tests written |
| 4. Claude sessions | `InteractiveProcess`, `ClaudeCodeSession`, rebuild rule, guidance block; session contract suite × 2 | US5 (Claude), US3 | |
| 5. Selection & availability | `ClaudeCodeAvailability`; `resolve_llm_selection`; settings fields, providers endpoint, 422s; Claude added to the registry | US2, US4 | Claude selectable end to end |
| 6. Frontend | `LlmProviderFields`, Settings wiring, Chat warm-up, API client, E2E | US2, US4, US5 | Playwright plus manual a11y check |
| 7. Docs | README, CLAUDE.md, architecture.md (§1 "one decision", §2 context diagram, §6.1 sessions) | US6 | |
| 8. Live validation | `claude_live` suite; quickstart §2–§7 by hand | all | Spends about 50 small plan requests |

Phase 2 comes before any Claude work on purpose. It restructures the conversation path while there
is only one provider, so every existing test acts as a regression guard for the engine before a
second provider adds variables.

---

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| `Settings` component in `frontend/src/pages/Settings.tsx` stays over 20 lines (~362 today) while this feature modifies it (T087, T095) | The component is modified to load the provider list, hold `llmProvider`/`llmEffort` state, render `LlmProviderFields`, and reword one warning. The feature makes it *shorter*: the old model `<select>` and `LLM_OPTIONS` move into `LlmProviderFields` | Bringing it under 20 lines means splitting every settings section (languages, voice, speech model, corrections, suggestions) into its own component with shared form state. That is a refactor of the whole screen, unrelated to provider selection, and it would put regressions in unrelated settings inside this feature's diff. Tracked as a follow-up: split `Settings` into per-section components the next time a non-LLM setting is added |
| `Chat` component in `frontend/src/pages/Chat.tsx` stays over 20 lines (~485 today) while this feature modifies it (T052) | One line is added to the existing `restoreTranscript` helper (itself ≤ 20 lines). The `Chat` component body is not otherwise changed | Splitting `Chat` (streaming, recording, feedback, audio, helper panel) is a large refactor with its own E2E risk and nothing to do with sessions. Tracked as a follow-up: extract `useChatStream` and `useRecorderFlow` hooks from `Chat` |

The Boy Scout clause ("existing longer functions are brought within the limit when next modified")
is met for every backend function this feature touches (`open_chat`, `send_message`,
`chat_helper`, `_migrate_db`), and for every new frontend unit. The two entries above are the
only exceptions.
