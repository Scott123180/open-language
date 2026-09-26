# Contracts: LLM Provider Selection

**Feature**: [spec.md](../spec.md) · **Data model**: [data-model.md](../data-model.md)

§1 covers the HTTP surface the frontend depends on. §2 covers the backend service interfaces the
contract tests pin. §3 covers the exact `claude` invocation, which is an external interface this
app depends on.

---

## 1. HTTP

### 1.1 `GET /api/settings/llm-providers` (new)

Returns every provider in catalogue order with its live availability. It never returns credentials,
email, org, or subscription details (FR-011).

**200**

```json
[
  {
    "provider_id": "ollama",
    "display_name": "Ollama (local)",
    "is_local": true,
    "models": [
      {"model_id": "llama3.1:8b", "label": "llama3.1:8b"},
      {"model_id": "llama3.2", "label": "llama3.2"},
      {"model_id": "mistral", "label": "mistral"}
    ],
    "default_model": "llama3.1:8b",
    "is_available": true,
    "unavailable_reason": null,
    "unavailable_message": null
  },
  {
    "provider_id": "claude",
    "display_name": "Claude (via Claude Code)",
    "is_local": false,
    "models": [
      {"model_id": "sonnet", "label": "Claude Sonnet"},
      {"model_id": "haiku", "label": "Claude Haiku (fastest)"},
      {"model_id": "opus", "label": "Claude Opus (most capable, uses more of your plan)"}
    ],
    "default_model": "sonnet",
    "effort_levels": [
      {"effort_id": "low", "label": "Low — fastest replies"},
      {"effort_id": "medium", "label": "Medium"},
      {"effort_id": "high", "label": "High — deeper, slower replies"}
    ],
    "default_effort": "low",
    "is_available": false,
    "unavailable_reason": "not_signed_in",
    "unavailable_message": "Sign in to Claude Code (run `claude` in a terminal) to use Claude."
  }
]
```

`unavailable_reason` ∈ `not_installed | not_signed_in | not_on_plan | null`.
Ollama's entry has `"effort_levels": []` and `"default_effort": null`. The UI shows the effort
control only when `effort_levels` is non-empty.

### 1.2 `GET /api/settings` (extended)

The response gains `llm_provider` and `llm_effort`. Every other field is unchanged.

```json
{ "llm_provider": "ollama", "llm_model": "llama3.1:8b", "llm_effort": "low", "...": "existing fields" }
```

### 1.3 `PUT /api/settings` (extended)

The request gains an optional `llm_provider` (`^(ollama|claude)$`) and an optional `llm_effort`
(`^(low|medium|high)$`). The partial-update and defaulting
rules are in [data-model.md §1](../data-model.md).

| Case | Status | Body |
|---|---|---|
| valid | 200 | full settings, as in 1.2 |
| `llm_provider` not in pattern | 422 | FastAPI validation error |
| model/provider mismatch | 422 | `{"detail": "<message from data-model §1>"}` |
| Claude selected while unavailable | 422 | `{"detail": "<availability message>"}` |

A 422 never changes stored settings.

### 1.4 Any endpoint that calls the language model (changed error shape)

| Endpoint kind | Before | After |
|---|---|---|
| SSE (`/api/chat/{id}/open`, `/api/chat/{id}/message`, `/api/chat/helper`) | `data: {"error": "The AI is not responding. Please try again."}` | `data: {"error": <LLMError.user_message>}`. Identical text for Ollama failures |
| JSON (`/api/learning/*`, `/api/chat/{id}/suggestions`) | 500 `{"detail": "An unexpected error occurred. Please try again."}` | **503** `{"detail": <LLMError.user_message>}` |
| JSON flashcard word info (`GET /api/flashcards/words/{id}/info/{cache_type}`) | 503 `{"detail": "LLM service unavailable. Please try again shortly."}` (a fixed text: `LlmCacheService.get_or_generate` swallows every exception and returns `None`) | **503** `{"detail": <LLMError.user_message>}`. `get_or_generate` lets `LLMError` propagate to the shared handler |

Corrections are unchanged: an `LLMError` during evaluation still fails open to an uncorrected turn
(003 FR-026). The learner sees no error.

Fill-in-the-blank sentences generated while a flashcard practice session is built stay fail-soft
(spec edge case): `LlmCacheService.get_fill_blank_sentence` still returns `None` on `LLMError`,
and the card is served without a sentence. It narrows its `except Exception` to `except LLMError`
and logs a warning, so a real bug is no longer swallowed.

The SSE frame sequence of `/open`, `/message`, and `/helper` is **unchanged** (`user_message_saved`,
`feedback`, `token`…, `done`, or `error`). Sessions change where the tokens come from, not how
they are delivered. Delivery stays batched (spec Assumptions).

### 1.5 `POST /api/chat/{conversation_id}/session` (new): warm up

Called by the chat screen when it mounts on an existing conversation (FR-S07). Starts building the
conversation's session in the background and returns straight away.

| Case | Status | Body |
|---|---|---|
| warm-up scheduled, or session already live | 202 | `{"status": "warming"}` or `{"status": "live"}` |
| conversation not found | 404 | `{"detail": "Conversation not found"}` |
| conversation completed | 409 | `{"detail": "This conversation has ended."}` |

It never returns an error for provider problems. A failed warm-up is logged, and the first real turn
reports the problem with its normal message. The chat screen ignores the response.

### 1.6 `PATCH /api/conversations/{id}` with `{"status": "completed"}` (existing, extended behaviour)

Also closes the conversation's live session (FR-S12). Response unchanged.

---

## 2. Backend service interfaces

### 2.1 `LLMProvider` / `StructuredLLMProvider` (existing, unchanged signatures)

Every concrete provider must pass the **shared provider contract suite**
(`tests/contract/service_interfaces/test_llm_provider_implementations.py`), parametrised over
`OllamaLLMProvider(fake_client)` and `ClaudeCodeLLMProvider(fake_runner)`:

1. `chat(msgs) == "".join(chat_stream(msgs))` for the same scripted backend output.
2. `chat_stream` yields only non-empty `str`.
3. `chat_json(msgs, schema)` returns text that `json.loads` accepts.
4. A backend failure in any of the three methods raises `LLMError` (subclasses allowed) with a
   non-empty `user_message`.
5. `model_name` returns the model the provider was built with.

### 2.2 `LLMError` (extended)

```python
class LLMError(Exception):
    DEFAULT_USER_MESSAGE = "The AI is not responding. Please try again."
    def __init__(self, detail: str, user_message: str = DEFAULT_USER_MESSAGE,
                 can_retry: bool = True) -> None: ...
    @property
    def user_message(self) -> str: ...
    @property
    def can_retry(self) -> bool: ...   # False: a rebuilt session cannot fix it (FR-S11)
```

### 2.3 `build_llm_provider` (new; the only place a provider id becomes behaviour)

```python
def build_llm_provider(selection: LLMSelection, settings: Settings,
                       effort: str = DEFAULT_EFFORT) -> ConfiguredLLMProvider: ...
```

- `LLMSelection` = `(provider_id: str, model: str)`, defined in the leaf module
  `services/llm/selection_types.py` together with the effort constants. Effort is a separate
  argument rather than a field, because `SessionFingerprint` holds the selection and the effective
  effort separately (Ollama's is always `""`).
- `ConfiguredLLMProvider` = a `Protocol` that is both an `LLMProvider` and a `StructuredLLMProvider`
- An unknown `provider_id` raises `UnknownProviderError(LLMError)`. That can't happen via the API,
  but a hand-edited DB could cause it.

`factory.get_llm` and `factory.get_structured_llm` both delegate here. No other module imports a
concrete provider.

### 2.4 `ProviderAvailabilityChecker` (new ABC)

```python
class ProviderAvailabilityChecker(ABC):
    @abstractmethod
    def check(self) -> ProviderAvailability: ...
```

Implementations are `AlwaysAvailable` (Ollama) and `ClaudeCodeAvailability(command_runner)`.
Served through `factory.get_availability_checkers() -> Mapping[str, ProviderAvailabilityChecker]`,
so tests override it with `app.dependency_overrides`.

### 2.5 `ClaudeCodeRunner` (new ABC; the subprocess boundary)

```python
class ClaudeCodeRunner(ABC):
    @abstractmethod
    def stream_lines(self, argv: Sequence[str], stdin_text: str,
                     timeout_seconds: float) -> Iterator[str]:
        """Yield stdout lines. Kill the process when timeout_seconds elapses or the generator
        closes. Raise ClaudeCodeFailure(not_installed) if the executable is missing.
        A non-zero exit code alone does not raise: the caller classifies from the lines."""
```

`timeout_seconds` is per call (research R-9): `chat` and `chat_stream` pass
`Settings.claude_request_timeout_seconds` (120 s), and `chat_json` passes
`Settings.correction_timeout_seconds` (8 s), so a correction that exceeds its budget has its
process killed rather than left running (FR-019).

The production implementation is `SubprocessClaudeCodeRunner(executable, workdir, environ)`. Unit
tests inject a `ScriptedClaudeCodeRunner` that replays recorded NDJSON fixtures for both methods.
The provider never touches `subprocess` directly (DIP).

A second method serves sessions. Its stderr goes to `log_path`, never a pipe (research R-14):

```python
    @abstractmethod
    def spawn_interactive(self, argv: Sequence[str], log_path: Path) -> InteractiveProcess: ...

class InteractiveProcess(ABC):
    def send_line(self, line: str) -> None: ...
    def read_lines_until_result(self, timeout_seconds: float) -> Iterator[str]: ...
    @property
    def is_alive(self) -> bool: ...
    def close(self) -> None: ...     # terminate, then kill after a grace period; idempotent
```

### 2.6 Conversation sessions (new)

```python
class ConversationSession(ABC):
    """A provider's live hold on one conversation. The saved history is the source of truth."""
    @property
    @abstractmethod
    def fingerprint(self) -> SessionFingerprint: ...
    @property
    @abstractmethod
    def synced_turn_ids(self) -> Sequence[str]: ...
    @abstractmethod
    def warm(self) -> None: ...                                  # no model reply, no plan usage
    @abstractmethod
    def reply(self, pending: Sequence[SavedTurn], guidance: str | None) -> Iterator[str]: ...
    @abstractmethod
    def reply_to_opening(self, instruction: str) -> Iterator[str]: ...
    @abstractmethod
    def acknowledge(self, turn_id: str) -> None: ...             # the saved id of the reply just produced
    @abstractmethod
    def close(self) -> None: ...                                 # idempotent

class SessionCapableProvider(ABC):                               # ISP: separate from LLMProvider
    @abstractmethod
    def session_fingerprint(self, standing_prompt: str) -> SessionFingerprint: ...
    @abstractmethod
    def open_session(self, standing_prompt: str, history: Sequence[SavedTurn]) -> ConversationSession: ...
```

**Session contract suite** (`test_conversation_session_implementations.py`, parametrised over
`OllamaSession` with a fake client and `ClaudeCodeSession` with a scripted runner):

1. A fresh session opened on history H, then `reply(pending)`, sends the provider exactly one
   generation request containing all of H and the pending turns.
2. After `acknowledge(id)`, `synced_turn_ids` ends with every pending id followed by `id`.
3. A second `reply` on a live session sends **only** the new pending turns (Claude: one stdin line)
   or the full list from memory (Ollama). Either way, no earlier turn is re-generated.
4. `guidance` appears in exactly that turn's request, and is absent from the next turn's standing
   instructions.
5. `warm()` produces no reply and no plan usage (Claude: the process is spawned with nothing written
   to stdin).
6. `close()` is idempotent, and after it `reply` raises `LLMError`.
7. A mid-turn failure marks the session broken and raises `LLMError` with a `user_message`.

### 2.7 `ConversationSessionPool` and `ConversationEngine` (new)

```python
class ConversationEngine:
    def __init__(self, pool: ConversationSessionPool) -> None: ...
    def stream_turn(self, provider: SessionCapableProvider, request: TurnRequest) -> Iterator[str]: ...
    def acknowledge(self, key: SessionKey, turn_id: str) -> None: ...
    def warm(self, provider: SessionCapableProvider, key: SessionKey, standing_prompt: str,
             history: Sequence[SavedTurn]) -> None: ...
    def is_live(self, key: SessionKey) -> bool: ...   # query for the warm endpoint's status
    def end(self, key: SessionKey) -> None: ...
    def evict_idle(self) -> None: ...                # called by the lifespan reaper every 60 s
    def close(self) -> None: ...                     # closes every session; lifespan shutdown
```

The pool implements the reuse/rebuild table in [research.md R-15](../research.md) and the limits,
locking, single retry, and reaper in R-16. The engine is served by
`factory.get_conversation_engine()` (lru-cached, one per process). The FastAPI lifespan starts the
reaper task after start-up, then on shutdown cancels it and calls `close()`.

---

## 3. External: the `claude` invocation

Built by the pure function `build_claude_argv(request: ClaudeRequest) -> list[str]`, which unit tests
assert on directly.

```text
<executable> -p
  --safe-mode --tools "" --disable-slash-commands --no-session-persistence
  --model <alias> --effort <low|medium>
  --system-prompt <rendered system prompt>
  [ --output-format stream-json --verbose --include-partial-messages ]   # chat_stream
  [ --output-format json ]                                               # chat
  [ --output-format json --json-schema <compact JSON> ]                  # chat_json
```

A **session** process uses the same base plus
`--effort <learner's level> --input-format stream-json --output-format stream-json --verbose --include-partial-messages`,
with the standing system prompt extended by the provider's turn-guidance paragraph (research R-14).
Its stderr goes to `<claude_log_dir>/session-<kind>-<identifier>.log`, not a pipe and not the working
directory.

**Pre-flight** (FR-010a, research R-8): before every one-shot invocation and every session spawn,
the provider runs `<executable> auth status --json` through the same runner and environment. Unless
it reports `loggedIn: true` with `authMethod: "claude.ai"`, the request is refused with
`ClaudeCodeFailure(not_installed | not_signed_in | not_on_plan)` and no prompt is sent.

**Invariants** (each one is a unit test, and each applies to one-shot and session argv alike):
- `--bare` never appears.
- `--tools` is always followed by `""`.
- `--system-prompt` is always present with non-empty text.
- The prompt is never in argv. It goes to stdin.
- `cwd` is the app-owned workdir, which the app never writes to, so it stays empty. The environment has no `ANTHROPIC_*`, `CLAUDE_CODE_*`,
  `CLAUDECODE`, `CLAUDE_PID`, or `CLAUDE_EFFORT` keys.

**Output parsing** relies only on these fields (research R-4, R-7): `type`,
`event.delta.type`, `event.delta.text`, `message.error`, `rate_limit_info.status`, `is_error`,
`result`, `structured_output`, and `api_error_status`. Unknown event types are ignored, so new
Claude Code event types don't break parsing.
