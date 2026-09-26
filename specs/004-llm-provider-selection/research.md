# Research: LLM Provider Selection

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-09-25

All findings marked **measured** come from live `claude -p` runs on the development machine
(Claude Code 2.1.283, signed in to a Pro plan, `authMethod: "claude.ai"`), made with the probe script
described at the end of this document. Nothing here is taken from memory of the CLI's behaviour.

---

## R-1 · Drive Claude Code directly, not through the Agent SDK

**Decision**: The provider spawns the `claude` executable with `subprocess.Popen` and reads its
newline-delimited JSON output. No new Python dependency.

**Rationale**:
- The existing `LLMProvider` contract is synchronous (`Iterator[str]`, `str`), and every caller runs
  it inside `run_in_executor`. A blocking `Popen` reading stdout line by line fits that exactly.
- Anthropic's Agent SDK (`claude-agent-sdk`) is async-first and spawns the same CLI underneath.
  Using it would mean running an event loop inside an executor thread to satisfy a sync interface,
  which adds a dependency and a layer without changing what runs.
- Owning the argv means the isolation flags (R-3) are visible in one pure function and are
  asserted by unit tests. They are not hidden behind SDK defaults that may change between
  releases.

**Alternatives considered**:
- *Agent SDK*: rejected for the sync/async mismatch and the added dependency. Worth revisiting if
  the app ever moves to native async streaming (see R-9).
- *`anthropic` SDK with an API key*: out of scope per the spec. Usage must draw on the learner's plan.

---

## R-2 · Authentication stays with Claude Code, and the environment is scrubbed

**Decision**: The subprocess inherits the backend's environment **minus** every variable starting
`ANTHROPIC_` or `CLAUDE_CODE_`, plus `CLAUDECODE`, `CLAUDE_PID`, and `CLAUDE_EFFORT`.
`CLAUDE_CONFIG_DIR` is deliberately kept, so a learner who relocated their config still works.
`--bare` is never passed.

**Rationale** (FR-010, FR-011, SC-006):
- An inherited `ANTHROPIC_API_KEY` makes Claude Code bill the API account instead of the plan.
  Scrubbing it is the only way to guarantee plan billing whatever the backend's shell has set.
- **Measured**: a backend launched from inside a Claude Code session inherits ten `CLAUDE_CODE_*` /
  `CLAUDECODE` variables, including a messaging socket and token for the parent session. The child
  process must not attach to the learner's interactive session.
- `--bare` looked like the natural isolation flag, but its help text says it makes "Anthropic auth
  strictly ANTHROPIC_API_KEY or apiKeyHelper … (OAuth and keychain are never read)". It would
  bypass the plan entirely.

**Alternatives considered**: an allowlisted environment (only `PATH`, `HOME`, `LANG`, …). Rejected
because Claude Code also reads proxy, XDG, and certificate variables that vary per machine. A
denylist of the two known-dangerous families is both safer and less brittle.

---

## R-3 · Isolation flags

**Decision**: Every invocation uses this fixed base:

```text
claude -p --safe-mode --tools "" --disable-slash-commands --no-session-persistence
       --model <alias> --effort <level> --system-prompt <text>
```

run with `cwd` set to an empty directory owned by the app (`~/.open-language/claude-workdir/`). The
prompt is written to **stdin**, never passed as an argument.

| Requirement | Flag / mechanism | Measured result |
|---|---|---|
| FR-012 no tools | `--tools ""` | `init` event reports `"tools": []`, `"mcp_servers": []`. Asked to list files and read `~/.bashrc`, Claude replied that it has no tools |
| FR-013 no personal/project config | `--safe-mode` + empty `cwd` | No CLAUDE.md or memory loaded. Asked to quote any instruction files, Claude reported none |
| FR-013 no skills | `--disable-slash-commands` | Belt and braces: with no tools the Skill tool is already absent |
| FR-014 replace default prompt | `--system-prompt` | 399–496 input tokens per request (the default coding prompt is several thousand) |
| FR-015 no session history | `--no-session-persistence` | No project directory created under `~/.claude/projects/` for any probe run |
| Conversation text off the process list | prompt on stdin | `ps` shows flags and the system prompt only |

`--system-prompt` is **always** passed. When the app's messages contain no system message, the
provider supplies `DEFAULT_SYSTEM_PROMPT` ("You are a helpful assistant inside a language-learning
app. Reply with text only."). Omitting the flag would let Claude Code's own coding-agent prompt
back in.

**Residual context (accepted)**: even with all of the above, Claude Code attaches a system reminder
with the account email, working directory, platform, and date (**measured**, isolation probe). It
cannot be turned off without `--bare` (R-2). Because the working directory is the empty app-owned
directory, it reveals nothing, and Anthropic already has the email. Recorded in the spec's
Assumptions.

---

## R-4 · Output formats per capability

**Decision**:

| Capability | Output flags | What the provider reads |
|---|---|---|
| `chat_stream` | `--output-format stream-json --verbose --include-partial-messages` | Each line whose `type == "stream_event"` and `event.delta.type == "text_delta"` yields `event.delta.text`. The final `type == "result"` line decides success or failure |
| `chat` | `--output-format json` | The single result object's `result` string |
| `chat_json` | `--output-format json --json-schema '<schema>'` | The result object's `structured_output`, re-serialised with `json.dumps` so the method returns raw JSON text as the contract requires |

**Measured**:
- Stream on Sonnet: the first `text_delta` arrived at 1.42 s and the process finished at 2.36 s. The
  deltas are ordinary Anthropic Messages API stream events wrapped in `{"type":"stream_event"}`.
- JSON schema on Sonnet: a 2-item correction array came back schema-valid in `structured_output` in
  1.67 s. Claude Code implements this internally as a forced tool call (`num_turns: 2`,
  `stop_reason: "tool_use"`), which the provider does not need to care about.
- `result` also carries the same JSON as a string, but `structured_output` is the field Claude Code
  validates, so it is the one read.

---

## R-5 · Translating the app's message list

**Decision**: A pure function `render_prompt(messages) -> RenderedPrompt(system_prompt, prompt)`:

1. All `system` messages, in order, are joined with a blank line into `system_prompt`.
2. If exactly one non-system message remains and it is from the user, its content is the prompt
   **verbatim**. This covers the learning tools, flashcard explanations, titles, suggestions, and
   corrections, which all send a single user message, so their prompts reach Claude exactly as
   they reach Ollama.
3. Otherwise the turns are rendered as a transcript:

   ```text
   <conversation>
   <turn role="assistant">…</turn>
   <turn role="user">…</turn>
   </conversation>
   Write the assistant's next turn only: the words themselves, with no tag, label, or quotation marks.
   ```

**Rationale**: A one-shot `claude -p` accepts one prompt, so a transcript is the faithful way to
carry history in a *stateless* call. It also handles histories that open with the assistant's line
(edge case) with no special-casing.

> **Correction (session research, R-14)**: an earlier draft claimed that `--input-format stream-json`
> accepts only user messages. That claim was untested and is **wrong**: assistant turns are accepted
> as context. What *is* true is that every seeded **user** line triggers its own generation, which
> is why rebuilt sessions still use this transcript for their first turn (R-14).

**Measured**: a four-turn train-station roleplay rendered this way produced a clean, in-character
Spanish reply with no tags, labels, or quotes, in 1.46 s at `--effort low`.

**Alternatives considered**: interleaving turns as `User: … / Assistant: …` lines. Rejected because
the model sometimes continues with a spurious `User:` line. XML-ish tags have an unambiguous close.

---

## R-6 · Model list and effort

**Decision**: Claude models are the CLI's tier aliases, so the list tracks the newest model in
each tier without app releases:

| Id sent to `--model` | Label | Note |
|---|---|---|
| `sonnet` *(default)* | Claude Sonnet | **measured** → `claude-sonnet-5` |
| `haiku` | Claude Haiku (fastest) | **measured** → `claude-haiku-4-5` |
| `opus` | Claude Opus (most capable, uses more of your plan) | not probed, to save plan usage. An unknown-model response is handled (R-7) |

Effort: **learner-selectable for conversation sessions** (Low, Medium, or High, default Low; spec
FR-019a). One-shot calls use fixed levels: `low` for `chat` and `chat_stream`, `medium` for
`chat_json`. Levels above High (`xhigh`, `max`) are not offered.

**Rationale**: At default effort, Haiku spent 191 thinking tokens on a one-sentence café reply.
Conversation turns gain nothing from extended thinking, and `--effort low` brought a multi-turn
reply to 1.46 s. Corrections are the one place where judgement matters, because false flagging
is the reason 003 shipped as experimental, so they get `medium`. Both levels are named constants,
and the correction benchmark from 003 (`-m benchmark`) is the tool for revisiting them.

**Alternatives considered**: full model ids (`claude-sonnet-5`). Rejected because they go stale
and the aliases are documented CLI input.

---

## R-7 · Failure classification

**Decision**: `ClaudeCodeFailure` (an `LLMError` subclass) carries a `user_message`. The provider
classifies:

| Signal | Classification | User message (FR-028) |
|---|---|---|
| `FileNotFoundError` spawning `claude` | not installed | "Claude Code isn't installed on this computer. Install it, or switch to the local model in Settings." |
| assistant message `error == "authentication_failed"` | not signed in | "Claude Code isn't signed in. Run `claude` in a terminal and sign in, or switch to the local model in Settings." |
| `rate_limit_event.rate_limit_info.status == "rejected"`, or assistant `error == "rate_limit"` | usage limit | "You've reached your Claude plan's usage limit. Switch to the local model in Settings until it resets." |
| result `api_error_status == 404` | model unavailable | "That Claude model isn't available on your plan. Choose a different Claude model in Settings." |
| exceeded `CLAUDE_REQUEST_TIMEOUT_SECONDS`, or any other `is_error: true` | unreachable | "Claude couldn't be reached. Try again, or switch to the local model in Settings." |
| stdout not parseable, or no `result` line | unexpected response | "Claude sent a response the app couldn't read. Try again. If it keeps happening, update Claude Code or switch to the local model." |

**Measured**:
- Signed out (`CLAUDE_CONFIG_DIR` pointed at an empty directory): the call exited 1 after 45 ms
  with no plan usage. The assistant message carried `"error": "authentication_failed"` and the
  result had `is_error: true` and `result: "Not logged in · Please run /login"`.
- Unknown model: exit 1, `api_error_status: 404`, with a stderr line `[claude-code:unrecognized_model]`.
- Every successful stream ends with a `rate_limit_event` whose `status` is `"allowed"`.

**Not measured**: the usage-limit path. Reaching a real plan limit to observe it would burn the
learner's allowance. The `status: "rejected"` signal is inferred from the event's shape. If a real
limit event doesn't match, it falls through to "unreachable", which still names a next step. Unit
tests pin the classifier to fixtures reproducing both observed shapes (auth failure and 404), plus a
constructed rejected-rate-limit fixture.

---

## R-8 · Availability check

**Decision**: `claude auth status --json`, run with the same scrubbed environment. It is available
only when `loggedIn` is true **and** `authMethod == "claude.ai"`. Only those two fields are read;
email, org, and subscription fields are discarded and never leave the function (FR-011, spec Key
Entities).

| Outcome | Reason code |
|---|---|
| `FileNotFoundError` | `not_installed` |
| `loggedIn: false` (**measured**, exit 1) | `not_signed_in` |
| `loggedIn: true`, `authMethod` ≠ `claude.ai` | `not_on_plan` |
| otherwise | available |

**Measured**: 0.13 s and no model call, so no plan usage (FR-021). That's cheap enough to run
uncached on every `GET /api/settings/llm-providers` and on every settings save that selects Claude.

---

## R-9 · Cancellation and the batched-delivery trade-off

**Finding**: All three `chat_stream` call sites (`routers/chat.py:102`, `:286`, `:382`) wrap the
iterator in `list(...)` inside `run_in_executor`. Replies are therefore collected in full before
the first SSE frame is sent, for Ollama too. `docs/architecture.md` records this as a deliberate
trade-off. So:
- "The reply streams progressively" was not achievable for either provider without changing the
  routers, and the spec was corrected.
- A learner navigating away does not close the iterator, so no provider can observe the abandonment.

**Decision**: `ClaudeCodeRunner` kills its process when (a) the hard timeout
`CLAUDE_REQUEST_TIMEOUT_SECONDS = 120` elapses, or (b) the stream generator is closed early
(`GeneratorExit` → `finally: process.kill()`). (b) is correct for any future caller that consumes
incrementally. (a) is what bounds wasted plan usage today (FR-019).

**Alternatives considered**: removing the `list(...)` batching to get true streaming. It's out of
scope because it changes router behaviour for both providers, and the architecture document owns
that decision.

---

## R-10 · Getting provider errors to the learner

**Finding**: Provider error text never reaches the learner today. Chat SSE sends the fixed "The AI
is not responding. Please try again." (3 sites). Learning-tool and flashcard endpoints don't catch
`LLMError`, so it hits the global handler and becomes a 500 "An unexpected error occurred".

**Decision**:
- `LLMError` gains a `user_message` attribute defaulting to the existing sentence, "The AI is not
  responding. Please try again.". Callers keep catching `LLMError` only (FR-005).
- The three chat sites send `exc.user_message` instead of the literal. They are provider-agnostic,
  so changing them breaks neither FR-004 nor SC-008: after this, a third provider changes nothing
  in them.
- A new `@app.exception_handler(LLMError)` in `main.py` returns **503** `{"detail": exc.user_message}`.
  The frontend already throws `Error(body.detail)` (`services/api.ts:99`, `:149`), so the learning
  panels show the message with no frontend change. This also fixes today's misleading 500 for Ollama.

---

## R-11 · Ollama host fix

**Finding**: `OllamaLLMProvider` calls the module-level `ollama.chat`, which always targets
`localhost:11434`. `Settings.ollama_url` is read nowhere.

**Decision**: The provider takes an injected `ollama.Client`. The provider registry builds
`ollama.Client(host=settings.ollama_url)`. The `chat`/`chat_stream`/`chat_json` bodies are
unchanged apart from `self._client.chat(...)`. This also makes the provider unit-testable without
patching the module (DIP).

---

## R-12 · Ollama model list and the `llama3.1:8b` mismatch

**Finding**: The Settings screen offers a hard-coded `['llama3.1', 'llama3.2', 'mistral']`, but the
backend default and fresh-install value is `llama3.1:8b`, which is not in the list. A fresh install
therefore renders a select whose value matches no option.

**Decision**: Both providers' model lists move to a backend `PROVIDER_CATALOG`, served by
`GET /api/settings/llm-providers`. The Ollama list becomes `llama3.1:8b` (default), `llama3.2`, and
`mistral`. The frontend adds the saved model as an extra option when it isn't in the list, so
existing installs that saved `llama3.1` keep their value (spec Assumptions).

Validation (FR-027): Claude accepts only its catalogue ids. Ollama accepts any non-empty name
**except** a Claude catalogue id, because installed local models vary.

---

## R-13 · What a "session" is worth for Ollama

**Finding: neither provider has sessions today.** `chat.py` rebuilds the full message list from the
database on every turn (`chat.py:265-267`). Ollama's chat API is stateless. The perceived continuity
comes from the database, not from the model server.

**Measured** (Ollama 0.30.11, `llama3.1:8b`, GPU host; 4-turn roleplay, 272→429 prompt tokens):

| Case | Model load | Prompt processing | Wall |
|---|---|---|---|
| Cold, model not in the OS page cache | 26.9 s | 22.1 s | **49.3 s** |
| Cold, model file in the page cache (after `keep_alive: 0`) | 4.2 s | — | **4.2 s** |
| Warm, stable prefix, turns 2–4 | 0.3 s | 0.07–0.09 s | 0.9–1.4 s |
| Warm, system prompt *changing* each turn | 0.3 s | 0.08–0.10 s | 0.8–0.9 s |

**Conclusions**:
- Re-sending history costs ~0.1 s on this GPU, whether or not the prefix changes. KV-cache reuse is
  not worth designing around for Ollama.
- The real cost is **unloading**. Ollama's default `keep_alive` is 5 minutes, so a learner who
  pauses to think, look something up, or practise pronunciation pays 4–49 s on their next turn.
- An **empty preload** (`generate(model, prompt="", keep_alive=…)`) is a sufficient warm-up: the
  first turn afterwards took 0.85 s, against 0.60 s after a 1-token warm-up.

**Decision**: an Ollama session keeps the message list in memory, passes
`keep_alive = SESSION_IDLE_TTL` (30 min) on every call, and warms up with an empty preload. Per-turn
guidance is appended to the system prompt for that call only, which is exactly how Gentle mode works
today. Measured to cost nothing, and it preserves the prompt behaviour 003 was tuned against.

---

## R-14 · What a "session" is worth for Claude

**Decision**: a Claude session is one long-lived process per conversation:

```text
claude -p <R-3 isolation flags> --model <alias> --effort <level> --system-prompt <standing>
       --input-format stream-json --output-format stream-json --verbose --include-partial-messages
```

Each turn writes one `{"type":"user","message":{"role":"user","content":…}}` line to stdin and reads
events until that turn's `result` line. `--no-session-persistence` stays: the conversation lives in
the process, not on disk (FR-015 unchanged).

**Measured** (Sonnet, `--effort low`, 3-turn train-station roleplay in one process):

| Turn | First delta | Complete | Cache read / write (tokens) |
|---|---|---|---|
| 1 | 0.75 s | 1.37 s | 0 / 527 |
| 2 | 0.42 s | **0.82 s** | **527** / 138 |
| 3 | 0.48 s | **0.68 s** | **665** / 119 |

Against 1.46–2.36 s per stateless call. The cache reads confirm that earlier turns aren't
re-processed. An idle session process holds **237 MB RSS**.

**Seeding history (rebuild)**, measured:
- An assistant line sent before the first user line is accepted as context. Seeded with an
  assistant greeting "Soy Lucía" and then asked "¿Cómo te llamas?", Claude answered "Me llamo Lucía".
- **Every seeded user line triggers its own generation.** Seeding `[assistant, user, assistant]`
  then the real user turn produced two results: one throwaway reply to the seeded user line, then
  the real one.

**Rebuild rule** (FR-S05, one reply per rebuild):
- History with no learner turns (only the opening line): seed the assistant line(s) natively, then
  send the new turn.
- Anything else: the first turn of the rebuilt process is a single user message containing the R-5
  transcript of the saved history plus the new turn. Every later turn is native. Cost: exactly the
  one reply the learner is waiting for.

**Per-turn guidance**: a live process's system prompt is fixed at spawn, and
`--system-prompt-snapshot` records it once. Guidance therefore travels inside that turn's user
message as a `<turn_guidance>` block. The standing system prompt gets a provider-added paragraph
telling Claude to follow such blocks for that reply only and never to mention them. The block stays
in the process's context afterwards (it cannot be removed), which is why the paragraph scopes it to
its own turn (FR-S09). A rebuilt session doesn't contain old guidance, since the database never
stored it. That matches Ollama, where guidance is never in history.

**Stderr**: a long-lived process's stderr must be drained, or a full pipe blocks it. Redirect to a
per-session log file under the workdir, truncated on spawn. No pipe.

---

## R-15 · Session bookkeeping: the database stays the source of truth

**Decision**: a session records the **ids of the saved messages it has taken in**
(`synced_ids`) and a **fingerprint** of what it was built from: provider, model, effort, standing
system prompt, and session kind. For each turn the pool gets the saved history (ids, roles, texts)
and decides:

| Condition | Action |
|---|---|
| No live session, or fingerprint differs | rebuild from saved history (R-13/R-14 rules) |
| `synced_ids` is a prefix of the saved ids, and every remaining message is from the learner | reply using the remaining messages. Several pending learner messages (Strict pause + retry) are merged into one user turn for Claude, or sent as consecutive user messages for Ollama, as today |
| anything else (an assistant message it didn't produce, a deleted message, reordering) | rebuild |

After the reply is saved, the engine tells the session the new assistant message's id. Opening a
roleplay sends the app's synthetic opening instruction, which is not a saved message. The session
simply never records an id for it, so the next turn still lines up.

Expression-helper threads live in `HelperSessionStore`, not the database. Their turns get positional
ids (`h0`, `h1`, …), and the same rules apply.

**Why ids and not content**: two identical learner messages ("Sí.") must not be mistaken for each
other, and it keeps the comparison cheap.

---

## R-16 · Pool, concurrency, retry, and warm-up

**Decision**: `ConversationSessionPool`, one per process, keyed by `SessionKey(kind, id)`:
- Bounded LRU (max 3) with 30-minute idle expiry. The same eviction semantics as
  `HelperSessionStore` (checked on access), plus `close()` on every evicted session.
- A per-key `threading.Lock` held for the whole turn (FR-S10). Different keys proceed in parallel.
- On session-level failure (process exited, unparseable output, timeout), close, rebuild, and retry
  **once**. `ClaudeCodeFailure` kinds `usage_limit`, `not_signed_in`, `not_installed`, and
  `model_unavailable` are raised immediately (FR-S11).
- `warm(key, snapshot)` builds the session and calls `session.warm()` in a background executor. For
  Ollama that is the empty preload. For Claude it is spawning the process, which then waits on stdin,
  with no model call and no plan usage.
- If a turn's token iterator is closed before its `result` line, the session can't be reused
  mid-turn, so it is closed and discarded. The next turn rebuilds it.
- On shutdown (FastAPI lifespan), close all sessions so no `claude` process outlives the backend.

The chat screen calls `POST /api/chat/{id}/session` when it mounts on an existing conversation
(FR-S07). New conversations don't need it, because `open` makes the first call straight away.

---

## R-17 · Where session logic lives

**Decision**: a new service `ConversationEngine` (`app/services/conversation/`) owns "produce the
next reply for a conversation". The routers stop building message lists for roleplay and helper
turns. They pass the engine a `TurnRequest` (key, standing system prompt, saved history, guidance)
and relay its tokens. The engine is the only user of the pool. Providers only implement
`SessionCapableProvider.open_session()`.

This keeps FR-004 and FR-S13 intact: routers know about conversations, not providers. It also
removes three near-identical `list(llm.chat_stream(messages))` blocks from `chat.py`, which is the
three-repetitions rule from CLAUDE.md.

---

## Probe script

The measurements above came from a throwaway script in the session scratchpad. It ran `claude -p`
with the R-2 environment scrub, the R-3 flags, and each R-4 output format, and timed the first
`text_delta` and the process exit. Six model calls in total, all on Haiku or Sonnet with prompts
under 500 tokens. The session round (R-13–R-14) added two Ollama probe scripts (no plan usage) and
three Claude session runs (six Sonnet replies). The script is not committed. The opt-in live test in
[quickstart.md](quickstart.md) § 5 replaces it.
