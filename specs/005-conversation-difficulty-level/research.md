# Research: Conversation Difficulty Level

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-09-26

Each entry records a decision, why it was made, and what else was considered. The Technical Context
in the plan had no open NEEDS CLARIFICATION items after the spec's clarification session. These
entries resolve the design questions that came up while reading the code.

---

## R1. The level scheme

**Decision**: Four levels, anchored to the CEFR (Common European Framework of Reference for
Languages): Beginner ≈ A1, Elementary ≈ A2, Intermediate ≈ B1, and Natural (no limits, covering B2
and above). Each level below Natural carries the seven limits in spec FR-003. Every number and phrase
is a named constant in one catalogue (`conversation_levels/catalog.py`), not scattered through prompt
strings.

**Rationale**:
- CEFR is language-neutral and is the scale most courses and apps use, so a learner coming from
  another app recognises "A2". Target language is a setting in this app, so a Spanish-only scale
  (such as DELE) would not fit.
- A B2 learner can generally follow unscripted native speech on familiar topics, which is exactly
  the "regular, unbounded, day-to-day speech" the user described as the top option. Separate B2, C1
  and C2 levels would add three choices that differ very little in a roleplay.
- The limits in FR-003 follow graded-reader practice and CEFR "can-do" descriptors. A1 learners
  handle short simple sentences in the present with a few hundred high-frequency words. A2 adds
  simple connectors and the common past and near-future forms, with about 1,000–1,500 words. B1
  adds connected discourse and the full common tense range, with about 2,500–3,000 words. The
  numbers are working targets; the evaluation (R9) may tune them without changing the level order.

**Alternatives considered**:
- *Six CEFR levels*: rejected. Too many choices for a one-control setting (Constitution IV), and the
  upper levels are indistinguishable in a short roleplay.
- *A free slider (1–10)*: rejected. It is not testable (what does "6" promise?) and learners cannot
  map it to anything they know.
- *Automatic adaptation to the learner*: out of scope per the spec's Assumptions.

---

## R2. Where the level enters the model's instructions

**Decision**: The level's rules are appended to the **standing prompt** (the system prompt that holds
for the whole conversation), after the scenario and character text. They are not sent as per-turn
`guidance`.

**Rationale**:
- **FR-008 comes for free.** A session's `SessionFingerprint` already includes
  `standing_prompt_digest`, and `plan_session_use` rebuilds any session whose fingerprint differs
  ([sync.py](../../backend/app/services/conversation/sync.py)). Changing the level changes the
  standing prompt, so the next turn rebuilds the session from saved history with the new rules. This
  works for a live Ollama session and a live Claude process alike, with **no change** to the
  engine, pool, or either provider.
- **Per-turn guidance would gain nothing on Ollama.** `OllamaSession._generate` sends
  `standing_prompt + guidance` as a single system message
  ([ollama_session.py:108](../../backend/app/services/llm/ollama_session.py)), so a per-turn
  reminder sits in the same place as the standing prompt and brings no recency benefit.
- **The guidance channel belongs to corrections.** Gentle mode sends its recast instruction there
  (`TurnPlan.reply_prompt_suffix`). Sharing the channel would mean composing two features'
  instructions in the chat router, which couples them.

**Alternatives considered**:
- *Per-turn guidance*: rejected for the reasons above. It also would not trigger a rebuild, which is
  harmless but means a Claude session built at one level keeps that level in its opening context
  while being told otherwise each turn.
- *Appending a reminder to the learner's last message*: rejected. It changes how both providers
  render turns (Principle VI: feature code must not reach into providers) and puts app text in the
  saved-history boundary.
- *Storing the level on each conversation*: rejected by the spec (one learner-wide setting).

**Consequence (recorded against SC-008)**: the first turn after a level change pays for a session
rebuild. On Ollama that is only a re-prefill of the history. On Claude it is a new process that
replays the transcript, a few seconds — the same cost 004 already accepts when the learner changes
model or effort. SC-008 is a steady-state criterion ("under the same conditions") and holds from the
second turn onward. The quickstart measures both.

---

## R3. Natural is byte-identical to today

**Decision**: At Natural, both public functions, `with_partner_speech_rules` and
`with_learner_text_rules`, return the prompt unchanged, byte for byte. Natural's descriptor has
`limits=None`, so no rules block is rendered and nothing is appended (data-model §4).

**Rationale**:
- FR-004 requires Natural replies to be equivalent to today's behaviour. An identical prompt makes
  that provable with a unit test (`prompt at Natural == prompt before this feature`) rather than by
  judging model output.
- Upgrading doesn't disturb anything: an existing learner defaults to Natural (FR-009), their
  standing prompts are unchanged, fingerprints match, and no live session is rebuilt.
- The phrasing cache (R7) keeps its existing keys at Natural, so cached results stay valid.

**Alternatives considered**: an explicit "speak naturally" instruction at Natural. Rejected, because
it changes today's output for every learner who never touches the setting.

---

## R4. How the rules are worded for a small local model

**Decision**: The rules block is short, numeric, and imperative. It opens with a precedence line
("These rules about how you speak override anything above"), then states:
- the limits as counts (at most N sentences, at most M words per sentence);
- the allowed tenses in generic grammatical terms ("present tense only", "the simple past");
- vocabulary as an approximate frequency band;
- the ceiling rule (FR-005);
- the two exceptions (words essential to the scenario, and words the learner just used; FR-012);
- the instruction to answer the learner's actual question at the level (FR-013);
- the instruction to simplify further when asked (FR-014).

It includes **no example sentences** in the target language.

**Rationale**:
- `llama3.1:8b` follows explicit counts much better than qualitative words like "simple". 003
  found the same thing with restraint: concrete negative rules outperformed judgement words.
- Small models tend to copy example sentences verbatim into their replies. Examples would also have
  to be written per target language, which would break language-neutrality (spec edge case).
- The precedence line and its placement last are what make "the level wins" over a custom
  character prompt (spec edge case: custom scenario asks for complex speech). The existing
  CRITICAL LANGUAGE RULE stays first and untouched (FR-015). The level block only restricts how the
  partner speaks within the target language.

**Alternatives considered**:
- *Few-shot examples*: rejected (copying, and per-language maintenance).
- *A hard token cap on generation (`num_predict`)*: rejected. It truncates mid-sentence rather than
  producing shorter sentences, and it is provider-specific.
- *Post-generation simplification (a second model call to rewrite the reply)*: rejected. It doubles
  latency (fails SC-008), and the rewrite has the same adherence problem one step later.

---

## R5. Two renderings: partner speech and learner-facing text

**Decision**: The catalogue renders each level two ways:
- **Partner speech rules**, for the roleplay standing prompt: all seven FR-003 limits.
- **Learner text rules**, for reply suggestions, alternative phrasings, and the expression helper's
  phrase: sentence length, tenses, vocabulary, and idioms only. Reply length and "ask the learner a
  question" do not apply to text the learner will say.

**Rationale**: FR-017 requires the aids to "follow the level", but a suggested reply that must ask a
question, or a phrasing limited to two sentences, would be wrong. The difference between the two
renderings is data in the catalogue, not branching in callers.

**Alternatives considered**: a single rendering with the partner-only lines phrased conditionally.
Rejected, because the model then has to decide which rules apply, which is exactly the judgement
small models do badly.

---

## R6. The expression helper: only the phrase follows the level

**Decision**: The helper's standing prompt gets the same learner-text rules as the other aids. They
are worded to limit "the target-language words the learner will say or read" and to state that
explanations in any other language are not limited (data-model §4). So the helper's phrase follows
the level, and its native-language explanation does not, with no helper-specific rendering.

**Rationale**: FR-017 names "the expression helper's suggested phrase", and FR-018 excludes
native-language output. The helper has its own `SessionKey`, so its fingerprint also changes with the
level and the helper session is rebuilt on the next question (R2 applies unchanged).

---

## R7. Alternative phrasings are cached, so the cache key must include the level

**Decision**: The `input_selection` cache key for `alternative_phrasing` becomes level-qualified,
built by one named helper. At Natural the key stays the bare message content (R3), so existing cached
rows are still hits. At any other level, a level marker is prefixed to the content.

**Rationale**: `get_or_create_learning_result` looks up
`(message_id, tool_type, input_selection)`. Without the level in the key, a phrasing produced at
Natural would be served after the learner moved to Beginner, which breaks FR-017. `tool_type` is a
database enum (`ToolType`) and the table has a unique constraint. Adding a column to the constraint
would need a table rebuild, and this project has no migration framework (additive columns only).
`input_selection` already means "the input that produced this result", and the level is part of
that input.

**Alternatives considered**:
- *A `level` column in the unique constraint*: rejected (needs a table rebuild in SQLite).
- *New `ToolType` values per level*: rejected (mixes two concepts into one enum).
- *Skipping the cache when level ≠ Natural*: rejected (a repeat click would cost a model call).

Grammar, translation and word lookup are native-language output (FR-018), so their keys stay as
they are.

---

## R8. Where the level is read, and when

**Decision**: The level is read from `app_settings` on every request that builds a prompt — roleplay
open, message, session warm-up, suggestions, phrasing, helper — through the existing
`get_app_settings` dependency. It is never copied onto the conversation.

**Rationale**:
- The spec requires one learner-wide setting, with a reopened conversation using the *current* level
  (US2 AS3).
- A reply already being generated was built from the request that started it, so a mid-reply change
  applies from the next reply, as the spec's edge case requires, with no extra code.
- **`warm_session` must use the same level.** If it built the standing prompt without the level, it
  would warm a session whose fingerprint never matches and the first real turn would rebuild. It
  builds the prompt through the same function as the turn endpoints.

**Verified**: a level-only `PUT /api/settings` does not trigger a Claude availability check.
`resolve_llm_selection` returns before checking when the resolved selection equals the stored one
([selection.py](../../backend/app/services/llm/selection.py)). A level change from the chat screen
is therefore one cheap write, even while Claude is selected but signed out.

---

## R9. Measuring whether the model honours the level (SC-001 – SC-003)

**Decision**: A hand-run benchmark under the existing `benchmark` pytest marker (deselected by
default, as with 003's detection benchmark). It plays a fixed evaluation set (4 built-in scenarios ×
5 scripted learner turns = 20 turns) at each of the four levels against the default local model,
through the real conversation engine.
- **Automated, asserted**: replies per level meeting the reply-length and words-per-sentence limits,
  and the no-native-language check (SC-004), using a deterministic, language-neutral sentence and
  word splitter.
- **Automated, printed and asserted**: average sentence length and the share of words outside the
  1,500 most frequent, per level (SC-003), using `wordfreq`'s `top_n_list`. Both must rise strictly
  from level to level.
- **Order**: every figure is printed and the review sheet is written *before* any assertion runs,
  and all failures are reported together. A missed threshold, the case that decides whether the
  feature ships experimental, still leaves the complete evidence behind.
- **Manual**: tense compliance (SC-001/SC-002's tense clause). The benchmark writes a review sheet
  (one reply per row, with its level's allowed tenses), and the learner marks it. Turns written to
  probe FR-012, FR-013 and FR-014 carry an extra yes/no question on the sheet, so those behaviours
  are reviewed rather than only prompted for.

**Rationale**:
- Length is objectively countable. Tense detection in Spanish needs a morphological analyser, and
  spaCy with a Spanish model is a heavy dependency for one hand-run check. A 20-reply sheet per level
  takes minutes to review. An LLM judge using the same 8B model would be marking its own homework.
- `wordfreq` 3.1.1 (verified current on PyPI) supports 40+ languages, which keeps SC-003
  language-neutral. It is a **dev-only** dependency: the app never imports it. Word-form frequency
  (not lemma frequency) is fine here because SC-003 compares levels against each other rather than
  against an absolute bar.

**Alternatives considered**: spaCy + `es_core_news_sm` for automatic tense tagging (rejected: heavy,
Spanish-only); an LLM-as-judge (rejected, as above); no benchmark (rejected: after 003, the project
cannot ship an adherence claim about the 8B model without measuring it).

**If the thresholds are missed**: per the spec's Assumptions, the feature ships marked experimental
on the Settings screen, as 003 did, and the thresholds are not lowered.

---

## R10. Module placement

**Decision**: A new domain module `backend/app/conversation_levels/`, with no tables and no router,
following `services/llm/catalog.py` for "ids listed once" and `corrections/` for "a domain module
with a public `__init__`". Its public interface:
- `ConversationLevel` (a `StrEnum`)
- `DEFAULT_CONVERSATION_LEVEL`
- `LEVEL_CATALOG`
- `with_partner_speech_rules(prompt, level)`
- `with_learner_text_rules(prompt, level)`

The existing prompt builders in `prompts/templates.py` are **not modified**. Call sites compose them:
`with_partner_speech_rules(build_roleplay_system_prompt(...), level)`.

**Rationale**:
- Open/Closed: every existing builder, and every test pinned to its output, stays as it is.
  Composition also guarantees R3, because an empty rules string means the untouched prompt.
- The level ids are listed once. The settings API's validation pattern and the level list the
  frontend receives are both derived from `LEVEL_CATALOG`, the same way `LLM_PROVIDER_PATTERN` is
  derived from `PROVIDER_CATALOG`.

**Alternatives considered**: a `level_rules` parameter on each builder (rejected: it edits four
stable functions for no gain), or putting the definitions in `prompts/templates.py` (rejected: the
catalogue is also served to the UI, and it is domain data, not a prompt).

---

## R11. Frontend: two controls, one setting

**Decision**:
- **Level list**: a new `GET /api/settings/conversation-levels` endpoint serves the catalogue
  (id, label, CEFR label, description), so the frontend hardcodes none of it. A
  `useConversationLevels` hook in the shared `frontend/src/hooks/` folder loads it for both
  controls, so the chat and settings component folders never import from each other.
- **Settings screen**: a `ConversationLevelFieldset` radio group, in the same pattern as the
  correction-mode group. It takes part in the page's existing Save action, which stays the screen's
  single primary action.
- **Conversation screen**: a self-contained `ConversationLevelControl` in the header: a native
  `<select>` labelled "Level". It saves on change (a level-only `PUT`), keeps the new value, and
  announces "Level set to Elementary. It applies from the next reply." through a polite live
  region. If the save fails, it reverts and shows the error with `role="alert"`. `Chat` gains only
  the element that renders it.

**Rationale**:
- A native `<select>` is two interactions (open, choose), which meets SC-006. It is keyboard- and
  screen-reader-accessible without custom ARIA, and it is compact enough for the 52 px header at
  phone width.
- Saving immediately is what FR-010 asks for ("MUST NOT open another screen or interrupt"). The
  Settings screen keeps its Save model. These are different controls on different screens, so
  Principle IV's consistency rule ("the same control produces the same result") holds.
- Both controls read the persisted setting on mount, so a change in one shows in the other on the
  next visit (US2 AS4) with no shared client store.

**Alternatives considered**:
- *A segmented button group in the header*: rejected. Four buttons do not fit the header on a phone.
- *A popover menu*: rejected. It needs custom focus management for no gain over `<select>`.
- *Hardcoding the level list in TypeScript* (as correction modes are): rejected. It would duplicate
  the catalogue, and the descriptions would drift.

---

## R12. The 004 follow-up on `Settings.tsx`

**Decision**: This feature carries out the Settings split that 004 deferred. 004's Complexity
Tracking made "split `Settings` into per-section components the next time a non-LLM setting is
added" a recorded follow-up, and the conversation level is that setting. The split moves the form's
state, load and save into a `useSettingsForm` hook and each section into its own component. It is a
behaviour-preserving refactor, done **before** the level section is added and guarded by the
existing `Settings.test.tsx` and `settings.spec.ts`.

**Rationale**: the constitution's Boy Scout clause ("existing long functions are brought under the
limit when next touched") and 004's explicit trigger both apply. Deferring it a second time would
need a stronger reason than 004 gave, and there isn't one.

**Scope note**: this is the one part of the plan that is not required by the spec. It sits in its
own phase so it can be dropped at `/speckit-tasks` time if the learner prefers. Doing so needs a new
Complexity Tracking justification.

---

## Summary of named constants

| Constant | Value | Source |
|---|---|---|
| `ConversationLevel` values | `beginner`, `elementary`, `intermediate`, `natural` | FR-001 |
| `DEFAULT_CONVERSATION_LEVEL` | `natural` | FR-009, R3 |
| Beginner limits | ≤ 2 sentences/reply, ≤ 8 words/sentence, present only, ~top 500 words, no idioms, 1 easy question | FR-003 |
| Elementary limits | ≤ 3 sentences/reply, ≤ 12 words/sentence, present + simple past + near future, ~top 1,500, no idioms, 1 open question | FR-003 |
| Intermediate limits | ≤ 4 sentences/reply, ≤ 20 words/sentence, common indicative tenses + fixed-phrase subjunctive, ~top 3,000, common idioms | FR-003 |
| Benchmark set | 4 scenarios × 5 learner turns | SC-001 – SC-003 |
| `SC_BEGINNER_MIN_COMPLIANCE` | 0.90 | SC-001 |
| `SC_OTHER_MIN_COMPLIANCE` | 0.85 | SC-002 |
| `VOCABULARY_BAND_FOR_SC_003` | 1,500 | SC-003 |
