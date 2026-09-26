# Feature Specification: LLM Provider Selection and Conversation Sessions

**Feature Branch**: `004-llm-provider-selection`
**Created**: 2026-09-25
**Status**: Draft
**Input**: User description: "Make the language-model backend swappable and add Claude as a second
provider next to Ollama, using the learner's own Claude Code installation (`claude -p`) so requests
draw on their Claude plan instead of a metered API key. The learner picks the provider and model on
the Settings screen and can switch without a restart. Everything that works today keeps working
with Ollama as the default. Reposition the docs from 'local-only, no cloud' to 'provider-agnostic,
local by default, cloud opt-in'. Make the configured Ollama host actually take effect."
Revised 2026-09-25 after planning. The learner asked whether picking Claude would let them "choose
model and level of effort", and then asked for sessions: "Both could benefit from sessions and I
think we should have an interface that supports that. this might end up being a large refactor, but
the product is much stronger."

## Context

Every language-model feature in the app — the roleplay partner, the per-message learning tools,
flashcard word explanations, conversation titles, and corrective feedback — already talks to the
model through one shared contract. But there is no way to choose what sits behind that contract:
the app always uses the local Ollama model. This feature makes the choice real and adds Claude as
the first alternative.

The Claude provider goes through the learner's **Claude Code installation** rather than a direct
API key. The learner already has Claude Code installed and signed in to a Claude plan. Running
requests through its non-interactive mode puts them on that plan's usage allowance instead of a
separately billed API account, and the app never touches a credential. Claude Code is a coding
agent, though, with file access, shell access, and project-specific configuration. The provider
must strip all of that away so Claude acts only as a conversation partner.

This feature also changes how the project describes itself. Until now the docs presented
"everything runs on your machine" as the decision everything else followed from. The actual design
principle is narrower and more durable: **every AI capability sits behind a swappable provider
interface**. The fully local stack stays the default because of the privacy reasoning behind it;
cloud providers are something the learner opts into.

The provider contract also gains **conversation sessions**. Today every turn is a cold, stateless
request: the app rebuilds the whole conversation from storage and sends all of it. That is correct,
but it wastes the thing that makes speaking practice feel fluid, which is a partner who is already
"in" the conversation. Measured during planning:
- The local model is unloaded after five idle minutes. The next reply then waits for it to reload,
  which takes about 4 seconds, and up to about 50 seconds when it has to be read back from disk.
- Each stateless Claude request starts a new process and re-reads the whole history. A live Claude
  conversation answers later turns in under a second.

A session keeps the provider warm and in context for the life of a conversation. Saved history
remains the single source of truth: a session only speeds things up, and it is rebuilt from storage
whenever it could be out of step.

Only the language model gains a second provider here. Speech recognition and speech synthesis are
unchanged. Claude offers neither, and both already sit behind their own provider interfaces.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Everything keeps working through the provider layer (Priority: P1)

A learner who upgrades does nothing new. The app starts, their existing settings load, and every
feature that uses the language model behaves exactly as before, still on the local Ollama model
they had selected. Behind the scenes the model is now chosen through a provider-selection step
instead of being hard-wired, and the Ollama host set in configuration is the one actually used.

**Why this priority**: The layer is only worth adding if it breaks nothing. It is also the
foundation the Claude provider plugs into. On its own it delivers a working, extensible seam and
fixes the ignored host setting.

**Independent Test**: With no new configuration, run every existing automated test and exercise
each language-model feature (roleplay chat, open chat, grammar/translation/alternatives/word
lookup, expression helper, suggested response, flashcard explanations, conversation titles,
corrective feedback). Outcomes are unchanged. Point the Ollama host setting at a non-default
address and confirm requests go there.

**Acceptance Scenarios**:

1. **Given** an existing database created before this feature, **When** the app starts, **Then**
   the provider is Ollama and the previously selected model is still in use.
2. **Given** a fresh install, **When** the app starts, **Then** the provider is Ollama with the
   default local model.
3. **Given** the Ollama host is configured to an address other than the default, **When** any
   language-model feature runs, **Then** the request goes to the configured address.
4. **Given** Ollama is the provider, **When** a learner uses any language-model feature, **Then**
   it behaves as it did before this feature, including how replies are delivered to the chat
   screen and corrective feedback.

---

### User Story 2 - Learner switches the conversation partner to Claude (Priority: P2)

A learner who has Claude Code installed and signed in opens Settings, chooses Claude as the
language-model provider, picks a Claude model and an effort level, and saves. Their next message,
whether a roleplay reply, a learning-tool request, a flashcard explanation, or a correction, is
answered by Claude on their Claude plan. Switching back to Ollama works the same way. No restart is needed in either
direction.

**Why this priority**: This is the capability the learner asked for. It depends on Story 1's seam.

**Independent Test**: With Claude Code signed in, switch to Claude in Settings, then use roleplay
chat, a learning tool, a flashcard explanation, and Gentle correction mode. Each one produces a
response from Claude. Switch back to Ollama and confirm the next request goes to the local model.

**Acceptance Scenarios**:

1. **Given** Claude Code is installed and signed in and Ollama is selected, **When** the learner
   selects Claude and a Claude model and saves, **Then** the next language-model request is served
   by that Claude model without restarting the app.
2. **Given** Claude is selected, **When** the learner sends a roleplay message, **Then** the reply
   is delivered to the chat screen the same way an Ollama reply is.
3. **Given** Claude is selected and correction mode is Gentle or Strict, **When** the learner sends
   a message with a grammar error, **Then** the correction is produced by Claude in the same
   structured form the correction feature already expects.
4. **Given** Claude is selected, **When** the learner switches back to Ollama and saves, **Then**
   the next request is served by the local model.
5. **Given** the learner changes the provider on the Settings screen, **When** the model field
   updates, **Then** it shows the new provider's default model. It never offers a model that
   belongs to the other provider.
6. **Given** Claude is selected, **When** the learner opens Settings, **Then** they can choose an
   effort level (Low, Medium, or High, with Low the default), described in terms of speed against
   depth, and the next conversation reply uses it.
7. **Given** Ollama is selected, **When** the learner opens Settings, **Then** no effort control is
   shown.

---

### User Story 3 - Claude acts only as a conversation partner (Priority: P2)

Whatever the learner types, and whatever a roleplay drifts into, Claude answers with text and
nothing else. It cannot read, create, or change files, run commands, or reach other tools. It does
not pick up instructions from the learner's own Claude Code setup (personal or project
instruction files, hooks, plugins, connected tool servers). The app's requests also never appear
in the learner's own list of saved Claude Code conversations (the ones `claude --resume` offers).

**Why this priority**: Claude Code is a coding agent with real access to the machine. Without this
isolation, a conversation-practice message could lead to file or shell actions, and the learner's
personal coding instructions would bleed into the roleplay. It ships together with Story 2.

**Independent Test**: With Claude selected, send messages that ask Claude to list files, read a
file, or run a command. It replies in conversation and performs no action. Add a distinctive
instruction to the learner's personal Claude Code instruction file and confirm replies do not
follow it. After a stretch of practice, confirm no new entries appear in the learner's saved
Claude Code conversations.

**Acceptance Scenarios**:

1. **Given** Claude is selected, **When** a learner message asks Claude to read, write, or list
   files or run a command, **Then** no such action happens and Claude replies with text only.
2. **Given** the learner's personal or project Claude Code configuration contains instructions,
   hooks, plugins, or tool servers, **When** the app sends a request, **Then** none of them is
   loaded or triggered.
3. **Given** Claude is selected, **When** the learner has practised for a while, **Then** the
   learner's saved Claude Code conversations contain no entries created by the app.

---

### User Story 4 - Learner can see whether Claude is usable and what it means for privacy (Priority: P3)

On the Settings screen the learner can tell at a glance whether Claude can be selected. If Claude
Code is not installed or not signed in, the Claude option is visibly unavailable and a short note
says which step is missing. When Claude is selected, a plain-language notice says that the text of
their conversations will be sent to Anthropic under their Claude account and will count toward
their plan's usage, and that their voice recordings stay on their machine. If a Claude request
later fails — the plan's usage limit is reached, the sign-in expired, or the network is down — the
learner gets a message telling them what went wrong and what to do.

**Why this priority**: Stories 1–3 deliver the capability safely. This story makes it
understandable. It matters, but a learner who set up Claude Code could get by without it at
first.

**Independent Test**: Run with Claude Code absent, then present but signed out, and confirm the
Claude option is disabled with the matching guidance each time. Run signed in and confirm the
option is enabled and the notice appears when it is selected. Simulate a usage-limit response and
a network failure and confirm each produces an actionable message.

**Acceptance Scenarios**:

1. **Given** Claude Code is not installed, **When** the learner opens Settings, **Then** the Claude
   option is disabled and a note says Claude Code must be installed.
2. **Given** Claude Code is installed but not signed in, **When** the learner opens Settings,
   **Then** the Claude option is disabled and a note says to sign in to Claude Code.
3. **Given** Claude Code is signed in with an API key rather than a Claude plan, **When** the
   learner opens Settings, **Then** the Claude option is disabled and a note says to sign in with
   their Claude plan, because an API key would bill a separate account.
4. **Given** Claude Code is installed and signed in, **When** the learner selects Claude, **Then**
   a notice states that conversation text is sent to Anthropic, counts toward their Claude plan's
   usage, and that audio stays local.
5. **Given** Claude is selected and the plan's usage limit has been reached, **When** any
   language-model feature runs, **Then** the learner sees a message saying the Claude usage limit
   was reached and suggesting switching to the local model until it resets.
6. **Given** Claude is selected and Anthropic is unreachable, **When** any language-model feature
   runs, **Then** the learner sees a message saying Claude could not be reached, which suggests
   retrying or switching to the local model.

---

### User Story 5 - The conversation partner stays warm and in context (Priority: P2)

A learner practising a roleplay gets quick replies from the second turn onward, whichever provider
they use. When they return to a conversation, including after pausing for a while, restarting the
app, or reopening it from History, the partner still knows everything said so far. The first reply
is not held up by the model loading, because the app got it ready while the learner was reading.
The same holds for the expression helper's side thread.

**Why this priority**: This story makes both providers feel like a partner who is already in the
conversation rather than one starting cold every turn, which is what speaking fluidity depends on.
It builds only on Story 1, and it is independently valuable for Ollama learners with no Claude at
all. The plan builds it before the Claude provider on purpose: the conversation path is restructured
while there is only one provider, so every existing test guards the refactor.

**Independent Test**: For each provider, hold a ten-turn roleplay and time the replies. Tell the
partner your name in turn 1 and ask for it in turn 10. Pause for ten minutes and send another turn.
Restart the backend and continue the same conversation. Switch provider mid-conversation and
continue. The partner stays consistent throughout, and later replies meet the timing targets.

**Acceptance Scenarios**:

1. **Given** a roleplay conversation in progress, **When** the learner sends a second or later
   turn, **Then** the reply draws on the live session rather than starting the provider cold.
2. **Given** the learner opens an existing conversation, **When** the chat screen appears, **Then**
   the provider is warmed up in the background before the learner sends anything.
3. **Given** a conversation whose session was lost (app restart, idle expiry, eviction, or a
   provider, model, or effort change), **When** the learner sends a turn, **Then** the reply is
   based on the full saved history, exactly as if the session had never been lost.
4. **Given** Strict mode paused the conversation for a retry, **When** the learner sends the
   corrected message, **Then** the partner's reply accounts for both the paused message and the
   retry, as it does today.
5. **Given** Gentle mode adds a recast hint for one turn, **When** the partner replies, **Then** the
   hint shapes that reply only and does not become a standing instruction for later turns.
6. **Given** the learner leaves a conversation idle past the session idle limit, or opens more
   conversations than the live-session limit, **When** a session is closed, **Then** its resources
   are released, and the conversation still resumes correctly later (scenario 3).

---

### User Story 6 - Project docs describe a provider-agnostic app (Priority: P4)

Someone reading the README, the architecture document, or the agent guidance learns that the app
is built around swappable provider interfaces for every AI capability. The local stack is the
default, and cloud providers such as Claude are opt-in. The privacy reasoning is kept as the reason
for that default. How to enable Claude is documented alongside the existing setup steps.

**Why this priority**: Accurate docs matter for contributors and agents, but they change nothing
at runtime.

**Independent Test**: Read the README, CLAUDE.md, and the architecture document. None of them still
claims the app has no cloud option. Each describes the provider-interface principle and the local
default. The README explains how to enable Claude.

**Acceptance Scenarios**:

1. **Given** the updated docs, **When** a reader looks for the governing design principle, **Then**
   they find "every AI capability sits behind a swappable provider interface, local by default".
2. **Given** the updated README, **When** a reader wants to use Claude, **Then** they find that
   Claude Code must be installed and signed in, and where to select Claude in Settings.
3. **Given** the updated docs, **When** searched for claims such as "no cloud" or "no external
   services", **Then** none remain as unqualified statements about the app.

---

### Edge Cases

- **Sign-in lost after Claude was selected.** The saved provider stays Claude, but Settings shows it
  as unavailable. Language-model features fail with the "sign in to Claude Code" message instead
  of silently switching to the local model. A silent switch would change behaviour without the
  learner knowing.
- **Saving Claude while it is unavailable.** The save is rejected with a message saying which setup
  step is missing. The previous settings are kept.
- **Model name from the other provider.** Saving a provider together with a model that belongs to
  the other provider (for example Claude with an Ollama model name) is rejected rather than
  producing a confusing runtime failure.
- **Switching provider mid-conversation.** The conversation continues with the new provider from
  the next message onward. Earlier messages are sent to the new provider as context unchanged.
- **Cached learning-tool and flashcard content.** Explanations generated by one provider stay valid
  and are reused after switching. The cache is not cleared or keyed by provider.
- **Slower one-shot responses.** One-shot Claude requests (learning tools, flashcards, suggestions,
  titles, corrections) each start a fresh Claude Code process, which adds start-up time on top of
  the model's own response time. Measured during planning, a structured correction takes about
  1.7 s, well inside the existing 8 s correction budget. Corrective feedback keeps its existing rule
  that a slow correction never blocks or fails the reply. Conversation turns avoid this cost through
  sessions (Story 5).
- **Several requests at once.** Opening a conversation can trigger a reply and a title together, and
  learning tools can be opened while a reply is being generated. Requests for different purposes
  each run independently, and none waits on or corrupts another. Only turns within the same
  conversation are serialised (see below).
- **Claude Code updates.** Claude Code updates itself. The provider depends only on documented
  non-interactive behaviour, and if its output changes shape the learner gets a clear "unexpected
  response from Claude" error rather than garbled text.
- **Conversation history that starts with the assistant.** Roleplay conversations open with the AI
  partner's line. The provider must carry that history faithfully even though it opens with the
  assistant.
- **Session out of step with saved history.** A session may have missed messages, for example the
  learner's message that Strict mode paused, or turns sent from a second browser tab. The session is
  brought up to date from storage, or rebuilt if its history no longer matches. It is never answered
  from a history that differs from what is saved.
- **Two turns for the same conversation at once**, for example from two tabs. Turns within one
  conversation are handled one at a time, in arrival order.
- **Session dies mid-conversation.** A provider process exits unexpectedly, or a live session stops
  responding. The turn is retried once on a freshly rebuilt session. Only then does the learner see
  an error. Failures that a retry cannot fix (usage limit, not signed in) are reported immediately,
  without spending a retry.
- **Rebuilding a long conversation.** Reconstructing a live Claude session must not generate one
  throwaway reply per earlier turn. The whole saved history is carried into the first rebuilt turn
  at once.
- **Conversation ended.** When a conversation is ended, its session is closed straight away.
- **A Claude request hangs.** A request that has not finished within a fixed maximum duration is
  stopped and reported as a failure, so a stuck process never runs indefinitely. Stopping a
  request early when the learner navigates away is not possible yet. Today the app collects every
  reply in full before sending it, for Ollama and Claude alike (the batched-delivery trade-off in
  the architecture document), so a departing learner does not interrupt generation for either
  provider.

## Requirements *(mandatory)*

### Functional Requirements

**Provider layer**

- **FR-001**: System MUST route every language-model request through a single provider-selection
  step that decides, per request, which provider serves it from the currently saved settings.
- **FR-002**: System MUST support two language-model providers: Ollama (local) and Claude (through
  the learner's Claude Code installation).
- **FR-003**: Each provider MUST support the three capabilities the app already uses: streamed
  replies, complete (non-streamed) replies, and replies constrained to a given structured format.
- **FR-004**: Features that use the language model MUST NOT know which provider is serving them.
  Adding a further provider MUST NOT require changes to those features.
- **FR-005**: A provider failure of any kind MUST reach features as the same failure type they
  already handle today, so existing error handling keeps working unchanged.

**Defaults and compatibility**

- **FR-006**: Ollama MUST be the default provider for fresh installs and for databases created
  before this feature.
- **FR-007**: Upgrading MUST preserve the learner's previously selected Ollama model.
- **FR-008**: The Ollama provider MUST send its requests to the Ollama host set in configuration.
- **FR-009**: With Ollama selected, every existing language-model feature MUST behave as it did
  before this feature.

**Claude provider**

- **FR-010**: The Claude provider MUST authenticate only through the learner's existing Claude Code
  sign-in, so that usage draws on their Claude plan. It MUST NOT use any mode of Claude Code that
  switches authentication to a separately billed API key.
- **FR-011**: The app MUST NOT read, store, log, or transmit the learner's Claude credentials.
- **FR-012**: Every Claude invocation, one-shot or session, MUST run with no tools available: no file
  access, no command execution, no web access, no tool servers.
- **FR-013**: Every Claude invocation MUST ignore the learner's personal and project Claude Code
  customisation (instruction files, hooks, plugins, skills, tool servers). Only the app's own
  instructions shape the reply.
- **FR-014**: Every Claude invocation MUST replace Claude Code's default coding-assistant
  instructions with the app's own instruction text.
- **FR-015**: Claude requests MUST NOT be saved to the learner's list of saved Claude Code
  conversations. The app's conversation sessions (FR-S01 onward) live only in the running app.
- **FR-016**: The Claude provider MUST accept the conversation shape the app already produces,
  including instruction (system) messages in the message list and histories that open with an
  assistant turn.
- **FR-017**: Structured replies from the Claude provider MUST conform to the same format the
  corrective-feedback feature already requests.
- **FR-018**: The Claude provider MUST offer a fixed list of supported Claude models, one of them
  the default.
- **FR-019**: A Claude request that exceeds a fixed maximum duration MUST be stopped and reported
  as a failure. A request whose reply is discarded before it finishes MUST also be stopped.
- **FR-019a**: Learners MUST be able to choose a Claude effort level of Low, Medium, or High, with Low
  as the default. The chosen level MUST apply to conversation replies (roleplay and expression
  helper). One-shot features (learning tools, flashcards, suggestions, titles) and correction
  evaluation MUST use fixed levels suited to them, so that a slow effort choice never pushes
  corrections past their time budget.

**Conversation sessions**

- **FR-S01**: The provider contract MUST offer conversation sessions alongside today's one-shot
  requests. Every provider MUST implement both.
- **FR-S02**: Roleplay conversations and the expression helper MUST be served through sessions.
  One-shot features (learning tools, flashcards, suggestions, titles, correction evaluation) MUST
  keep using one-shot requests.
- **FR-S03**: The app's own record of a conversation MUST remain the single source of truth: the
  saved messages for a roleplay, or the helper thread's stored turns for the expression helper.
  Every session reply MUST be produced from a context equivalent to that record at that moment. A
  session that cannot be brought into line with it MUST be rebuilt from the record before replying.
- **FR-S04**: A session MUST be rebuilt transparently when it is missing (app restart, idle expiry,
  eviction) or stale (provider, model, effort, scenario, or language changed). The only difference
  the learner may notice is latency.
- **FR-S05**: Rebuilding a session MUST cost at most one model reply: the one the learner is waiting
  for.
- **FR-S06**: The number of live sessions MUST be bounded, and sessions MUST close after an idle
  period. Closing a session MUST release what it holds (for example, a running Claude process).
- **FR-S07**: Opening an existing conversation on the chat screen MUST warm its session in the
  background, so that the first reply is not delayed by the provider starting or the model loading.
- **FR-S08**: While a conversation's session is live, the local model MUST stay loaded rather than
  being released under the local server's default five-minute idle policy.
- **FR-S09**: Per-turn guidance (such as Gentle mode's recast hint) MUST shape that turn's reply
  only. It MUST NOT change the session's standing instructions for later turns.
- **FR-S10**: Turns within one conversation MUST be processed one at a time. Different
  conversations MUST NOT block each other.
- **FR-S11**: When a live session fails in a way a fresh session could fix, System MUST retry the
  turn once on a rebuilt session before reporting an error. Account-level failures (usage limit, not
  signed in, not installed) MUST NOT be retried.
- **FR-S12**: Ending a conversation MUST close its session.
- **FR-S13**: Features that use sessions MUST NOT know which provider serves them (FR-004 applies).

**Availability**

- **FR-020**: System MUST determine whether Claude is available by checking that Claude Code is
  installed and signed in with a Claude plan (not an API key). It MUST report which condition is
  missing.
- **FR-021**: The availability check MUST NOT consume plan usage.

**Settings**

- **FR-022**: Learners MUST be able to choose the language-model provider and model on the Settings
  screen, and the choice MUST take effect on the next request without a restart.
- **FR-023**: The saved settings MUST persist the selected provider, model, and Claude effort level.
- **FR-024**: Changing the provider on the Settings screen MUST reset the model to that provider's
  default model.
- **FR-025**: The Settings screen MUST show the Claude option as unavailable when it is, with
  guidance naming the missing step: install Claude Code, sign in to it, or sign in with a Claude
  plan instead of an API key.
- **FR-025a**: The Settings screen MUST show the effort control only while Claude is the selected
  provider.
- **FR-026**: When Claude is selected, the Settings screen MUST show a notice stating that
  conversation text is sent to Anthropic, counts toward the learner's Claude plan usage, and that
  audio stays on the learner's machine.
- **FR-027**: System MUST reject a settings save that selects Claude while it is unavailable, or
  that pairs a provider with a model it does not serve, and MUST keep the previous settings.

**Errors**

- **FR-028**: Claude failures — not installed, not signed in, usage limit reached, model not
  available on the plan, unreachable or timed out, and unexpected response — MUST each produce a
  plain-language message that says what happened and what the learner can do next.
- **FR-029**: System MUST NOT silently fall back from Claude to Ollama, or the reverse. The provider
  the learner selected is the one used.

**Documentation**

- **FR-030**: The README, CLAUDE.md, and the architecture document MUST describe the app as
  provider-agnostic, with the local stack as the default and cloud providers as opt-in, and MUST
  keep the privacy rationale as the reason for the local default.
- **FR-031**: The README MUST document how to enable Claude: install Claude Code, sign in, and
  select Claude on the Settings screen.

### Key Entities

- **Language-model provider**: The service that turns a conversation into a reply. It has an
  identifier (Ollama or Claude), a list of models it serves, a default model, the effort levels it
  offers (Claude only), and an availability state (Ollama is always selectable; Claude is selectable
  only when Claude Code is installed and signed in with a Claude plan). Every provider can answer
  one-shot requests and hold conversation sessions.
- **App settings** (existing, extended): The learner's saved preferences. Gains the selected
  language-model provider and the Claude effort level next to the existing selected model.
- **Conversation session** (in memory, never persisted): a provider's live, warmed-up hold on one
  conversation (a roleplay or an expression-helper thread). It knows which saved messages it has
  already taken in, the standing instructions and provider selection it was built for, and when it
  was last used. It can always be discarded and rebuilt from saved history.
- **Provider availability** (read-only view): What the Settings screen needs to render the choice:
  each provider's identifier, display name, models, default model, effort levels, whether it is
  currently available, and, when it is not, the reason. It never includes credentials or account
  details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After upgrading, 100% of existing automated tests pass with no settings change. Every
  language-model feature produces a result on the default provider.
- **SC-002**: A learner can switch between Ollama and Claude on the Settings screen in under
  30 seconds. The next request uses the new provider with zero restarts.
- **SC-003**: Every language-model feature (at least 9 distinct features: roleplay chat, open
  chat, four learning tools, expression helper, suggested response, flashcard explanations,
  conversation titles, and corrective feedback) produces a valid result with Claude selected.
- **SC-004**: With Claude selected at Low effort, the first reply of a newly opened or rebuilt
  conversation appears in full within 5 seconds, and every later reply within 2 seconds.
- **SC-004a**: With Ollama selected on a GPU host, a reply sent after the learner has been idle for
  up to 25 minutes in an open conversation arrives within 3 seconds. Today it can take 4–50 seconds
  once the model has been unloaded.
- **SC-004b**: In a scripted check, run for each provider, where the learner states a fact in turn 1
  and asks for it in turn 10, the partner recalls it 100% of the time, whether the session stayed
  live, was rebuilt after an app restart, or was rebuilt after a provider switch.
- **SC-004c**: Rebuilding a session for a conversation of any length produces exactly one model
  reply.
- **SC-004d**: No more than 3 conversations hold live provider resources at once.
- **SC-005**: Across a scripted set of at least 10 messages that ask Claude to touch files, run
  commands, or follow instructions planted in the learner's Claude Code configuration, 0 result in
  an action or in those instructions being followed.
- **SC-006**: Practice of any length with Claude selected adds 0 entries to the learner's saved
  Claude Code conversations, and no app-initiated request is billed outside the learner's plan.
- **SC-007**: Each of the six Claude failure types (not installed, not signed in, usage limit,
  model not available, unreachable or timed out, unexpected response) shows the learner a message
  naming a next step, with no crash or stuck loading indicator.
- **SC-008**: Adding a third language-model provider requires changes only to the provider layer
  and settings. No feature that uses the language model changes.
- **SC-009**: None of the three governing docs (README, CLAUDE.md, architecture document) contains
  an unqualified "no cloud" or "no external services" claim.

## Assumptions

- **Integration route**: "Claude SDK" here means the learner's installed Claude Code in its
  non-interactive (`claude -p`) mode, signed in to a Claude subscription. It does not mean the
  Anthropic API with an API key. Planning chose to drive Claude Code directly rather than through
  Anthropic's Agent SDK, which wraps the same installation (research R-1).
- **Personal use**: The Claude provider draws on the learner's own subscription on their own
  machine. Anyone else running the app needs their own Claude Code installation and sign-in. The
  app neither bundles nor shares credentials.
- **Model list**: Claude models are offered as a short fixed list of the model tiers Claude Code
  accepts (Sonnet, Haiku, Opus). The default is Sonnet, the mid tier, balancing reply quality and
  correction restraint against latency and plan usage.
- **Ollama model list**: Ollama keeps a short list of known local models. A previously saved Ollama
  model that is not in the list is still shown and kept, since installed local models vary per
  machine.
- **Latency budget**: the SC-004 targets were checked during planning against measured times on
  this machine: 1.5–2.5 s for a stateless Claude reply, 0.7–0.8 s for later turns in a live Claude
  session, and 0.6–1.4 s for a warm local model.
- **Session limits**: at most 3 live sessions, each closed after 30 minutes idle. A live Claude
  session holds a process of about 240 MB, and a single learner rarely has more than one
  conversation open. Both limits are configurable.
- **Batched delivery stays**: replies continue to reach the screen in one piece once complete, as
  they do today. Word-by-word delivery was considered and deliberately left out of this feature.
- **Effort levels**: only Low, Medium, and High are offered. Claude Code's higher levels add
  seconds of thinking per turn, which works against conversational fluency.
- **Claude context note**: Claude Code adds a small block of environment context (account email,
  working directory, date) to every request, which Anthropic already has. The provider runs from an
  empty working directory, so it reveals nothing about the learner's files.
- **Usage visibility**: No in-app usage metering, budgets, or spend caps. The learner monitors plan
  usage through their Claude account, and the app only reports when the limit has been reached.
- **Scope**: Only the language model gains a second provider. Speech recognition and synthesis keep
  their existing local providers and interfaces. Cloud speech providers and a direct Anthropic API
  key provider are out of scope, though the provider layer leaves room for the latter.
- **Corrections warning**: The existing "corrections are experimental" warning stays. Its wording
  is adjusted so it no longer assumes the model is local.
- **Governance**: The constitution does not mention local-only execution, so no constitution
  amendment is needed.
