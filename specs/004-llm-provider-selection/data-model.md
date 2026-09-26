# Data Model: LLM Provider Selection

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

Two additive columns. Everything else, including conversation sessions, is in memory or a
read-only view. There are no new tables and no credentials anywhere.

---

## 1. Persisted

### `app_settings` (existing table, extended)

| Column | Type | Null | Default | New? | Notes |
|---|---|---|---|---|---|
| `llm_provider` | `VARCHAR(20)` | NOT NULL | `'ollama'` | **new** | `'ollama'` or `'claude'` |
| `llm_model` | `VARCHAR(100)` | NOT NULL | `Settings.ollama_model` (`llama3.1:8b`) | existing | Interpreted per provider: an Ollama tag, or a Claude alias (`sonnet`/`haiku`/`opus`) |
| `llm_effort` | `VARCHAR(10)` | NOT NULL | `'low'` | **new** | `'low'`, `'medium'`, or `'high'`. Used only when the provider is Claude, and kept (not reset) when switching to Ollama and back |

**Migration**: two `_add_column_if_missing()` calls in [database.py](../../backend/app/database.py):
`"llm_provider VARCHAR(20) NOT NULL DEFAULT 'ollama'"` and `"llm_effort VARCHAR(10) NOT NULL DEFAULT 'low'"`.
SQLite fills the defaults into existing rows, so a pre-004 database comes up as Ollama with its
saved model untouched (FR-006, FR-007).

**Validation rules** (enforced in the settings service, not the column; FR-027):

| Rule | Rejection detail (422) |
|---|---|
| `llm_provider ∈ {ollama, claude}` | pattern validation on the request model |
| provider `claude` ⇒ `llm_model ∈ CLAUDE_MODEL_IDS` | "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus." |
| provider `ollama` ⇒ `llm_model` non-empty (after trimming) | "Choose a local model." |
| provider `ollama` ⇒ `llm_model ∉ CLAUDE_MODEL_IDS` | "That model belongs to Claude. Choose a local model, or switch the provider to Claude." |
| provider `claude` ⇒ Claude availability is `available` at save time | the availability `message` (see §2) |
| `llm_effort ∈ {low, medium, high}` | pattern validation on the request model |

**Partial updates** (`PUT /api/settings` is partial today and stays partial):

| Request contains | Resulting provider | Resulting model |
|---|---|---|
| neither | unchanged | unchanged |
| `llm_provider` only, different from current | new provider | **new provider's default** (FR-024) |
| `llm_provider` only, same as current | unchanged | unchanged |
| `llm_model` only | unchanged | validated against the current provider |
| both | as given | validated against the given provider |

*(Added during implementation.)* When the resulting provider and model equal the stored ones, nothing
new is being selected, so neither the model rules nor Claude's availability are re-checked. This keeps
the Settings screen saveable after Claude's sign-in lapses (the form always sends its provider and
model); requests keep failing with the sign-in message until the learner fixes it or switches (FR-029).

### `conversations.llm_model` (existing, unchanged)

Still records the model a conversation started with. For Claude conversations it holds the alias
(`sonnet`), which already tells the providers apart, so no provider column is added.

---

## 2. In-memory value objects (`backend/app/services/llm/`)

### `ProviderDescriptor` (frozen dataclass): static catalogue entry

| Field | Type | Ollama | Claude |
|---|---|---|---|
| `provider_id` | `str` | `"ollama"` | `"claude"` |
| `display_name` | `str` | `"Ollama (local)"` | `"Claude (via Claude Code)"` |
| `models` | `tuple[ModelOption, ...]` | `llama3.1:8b`, `llama3.2`, `mistral` | `sonnet`, `haiku`, `opus` |
| `default_model` | `str` | `Settings.ollama_model` | `"sonnet"` |
| `is_local` | `bool` | `True` | `False` |

`ModelOption` = `(model_id: str, label: str)`.

`PROVIDER_CATALOG: Mapping[str, ProviderDescriptor]` is the one place provider ids are listed.
Adding a provider adds one entry here and one builder in the registry (§3), and nothing else (SC-008).

### `ProviderAvailability` (frozen dataclass)

| Field | Type | Notes |
|---|---|---|
| `is_available` | `bool` | |
| `reason` | `AvailabilityReason \| None` | `None` when available |
| `message` | `str \| None` | Plain-language next step, shown under the disabled option |

`AvailabilityReason` (StrEnum): `not_installed`, `not_signed_in`, `not_on_plan`.

| Reason | Message |
|---|---|
| `not_installed` | "Install Claude Code to use Claude." |
| `not_signed_in` | "Sign in to Claude Code (run `claude` in a terminal) to use Claude." |
| `not_on_plan` | "Claude Code is signed in with an API key. Sign in with your Claude plan to use it here." |

Ollama is always `ProviderAvailability(is_available=True)`. Checking whether its daemon is running
is out of scope; request-time errors cover it as they do today.

### `RenderedPrompt` (frozen dataclass): output of `render_prompt`

| Field | Type |
|---|---|
| `system_prompt` | `str` (never empty: falls back to `DEFAULT_SYSTEM_PROMPT`) |
| `prompt` | `str` (written to stdin) |

### `ClaudeCodeFailure(LLMError)`

| Field | Type | Notes |
|---|---|---|
| `kind` | `FailureKind` | `not_installed`, `not_signed_in`, `not_on_plan`, `usage_limit`, `model_unavailable`, `unreachable`, `unexpected_response` |
| `user_message` | `str` | from research R-7. Inherited attribute, see below |
| `can_retry` | `bool` | `False` for the account-level kinds `not_installed`, `not_signed_in`, `not_on_plan`, `usage_limit`, `model_unavailable`; `True` otherwise. Inherited attribute, see below |

### `LLMError` (existing, extended)

Gains `user_message: str`, defaulting to `"The AI is not responding. Please try again."`, which is
today's literal, and `can_retry: bool`, defaulting to `True`. `can_retry` tells the session pool
whether a rebuilt session could fix the failure (FR-S11), without the pool importing a concrete
provider. The constructor becomes
`LLMError(detail: str, user_message: str = DEFAULT, can_retry: bool = True)`, so every existing
`raise LLMError(str(e))` keeps working unchanged.

---

## 2a. Conversation sessions (`backend/app/services/conversation/`, in memory only)

### `SessionKey` (frozen dataclass)

| Field | Type | Values |
|---|---|---|
| `kind` | `SessionKind` (StrEnum) | `roleplay`, `helper` |
| `identifier` | `str` | conversation id, or helper session id |

### `SessionFingerprint` (frozen dataclass): what a session was built for

| Field | Type | Notes |
|---|---|---|
| `selection` | `LLMSelection` | provider id + model |
| `effort` | `str` | the effective effort for this provider (Ollama: always `""`) |
| `standing_prompt_digest` | `str` | SHA-256 of the standing system prompt: scenario, languages, character |

Any field differing from the live session's fingerprint forces a rebuild (FR-S04).

### `SavedTurn` (frozen dataclass): one message of saved history

| Field | Type | Notes |
|---|---|---|
| `turn_id` | `str` | `"m<message id>"` for roleplay, `"h<index>"` for helper threads |
| `role` | `str` | `user` or `assistant` |
| `content` | `str` | |

### `TurnRequest` (frozen dataclass): what a router hands the engine

| Field | Type | Notes |
|---|---|---|
| `key` | `SessionKey` | |
| `standing_prompt` | `str` | the system prompt that holds for the whole conversation |
| `history` | `tuple[SavedTurn, ...]` | full saved history **including** the learner's new message(s) |
| `guidance` | `str \| None` | per-turn only (FR-S09), e.g. Gentle mode's recast suffix |
| `opening_instruction` | `str \| None` | set only by `open`: a synthetic user turn that is never saved |

Invariant: exactly one of the following holds. Either `opening_instruction` is set and `history` has
no learner turns, or the last turn in `history` is a learner turn.

### Session state (inside each `ConversationSession`)

| Field | Type | Notes |
|---|---|---|
| `fingerprint` | `SessionFingerprint` | fixed at construction |
| `synced_turn_ids` | `list[str]` | saved turns already in the provider's context, in order |
| `last_used_at` | `datetime` | for idle expiry |
| `is_broken` | `bool` | set when a turn fails mid-stream. A broken session is never reused |

### Pool limits (named constants in `app/config.py`, env-overridable)

| Setting | Default | Source |
|---|---|---|
| `session_max_live` | `3` | SC-004d |
| `session_idle_ttl_minutes` | `30` | spec Assumptions. Also Ollama's `keep_alive` while a session is live |
| `SESSION_REAPER_INTERVAL_SECONDS` | `60` | module constant, not env-overridable. How often the lifespan reaper closes idle sessions (FR-S06, research R-16) |

### Session lifecycle

```text
            warm() / first turn
 (absent) ───────────────────────▶ live ──── turn ok ─────▶ live
     ▲                               │
     │   idle > TTL, LRU evicted,    │  fingerprint mismatch,
     │   conversation completed,     │  history diverged,
     └─── shutdown, or broken ◀──────┘  session-level failure → rebuild (one retry)
          (idle expiry fires on access
           or from the 60 s reaper)
                (close() releases the process / nothing for Ollama)
```

---

## 3. Relationships

```text
AppSettingsRecord ─(provider, model, effort)─▶ build_llm_provider() ──▶ OllamaLLMProvider(client)
                                                     │               ──▶ ClaudeCodeLLMProvider(runner, model, effort)
                                                     ▼                          │ (both are SessionCapableProviders)
                                              PROVIDER_CATALOG ◀── settings validation
                                                     ▲                          ▼
ClaudeCodeAvailability ──▶ ProviderAvailability ─────┘        ConversationEngine ─▶ ConversationSessionPool
                                                                   ▲                 └─ SessionKey → ConversationSession
                                  chat routers (roleplay, helper) ─┘                     (OllamaSession | ClaudeCodeSession)
```

## 4. State transitions

The provider setting has two states and no intermediate ones. Transitions happen only on a
successful `PUT /api/settings`. A rejected save leaves both fields unchanged (FR-027).

```text
          PUT {llm_provider: claude}   [Claude available]
 ollama ─────────────────────────────────────────────────▶ claude
   ▲                                                         │
   └──────────── PUT {llm_provider: ollama}  (always allowed)┘
```

Losing Claude availability later does **not** transition the setting (edge case, FR-029). Requests
then fail with `ClaudeCodeFailure(not_signed_in | not_installed)` until the learner fixes it or
switches. The same holds if Claude Code is re-signed in with an API key: the pre-flight check
(research R-8) refuses every request with `ClaudeCodeFailure(not_on_plan)` before anything is sent.
