# Research: Podcast Mode

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-09-28

Each entry records a decision, why it was made, and what else was considered. The spec has no
NEEDS CLARIFICATION markers; its five clarifications are already folded in. These entries settle
the design questions raised by reading the code on `007-podcast-mode` @ `5897b32`.

Four findings shape the whole design:

1. **Almost everything a podcast needs already exists for a conversation.** Learning tools, saved
   words, corrections, transcription and speech are all keyed by `message_id` or
   `conversation_id`, and every one of them takes its language from the conversation (006, R9).
   An episode that *is* a conversation inherits all of FR-027–FR-029 for free (R1).
2. **The conversation engine assumes one partner who replies to the learner.** `TurnRequest` must
   end with a learner turn, and a turn produces one reply. A podcast needs host lines with no
   learner turn in between, several speakers, and no reply at all at the learner's turn (R3).
3. **A small local model cannot be trusted with the turn-taking rules.** FR-014, FR-015, FR-018
   and FR-019 are hard numeric limits. The code enforces them. The model only writes the words of
   the one host the code has chosen (R2).
4. **Two voices per language are already installed** (006), so FR-030 needs no new downloads (R7).

---

## R1. An episode is a conversation with a podcast extension

**Decision**: Starting an episode creates an ordinary `conversations` row, with
`scenario_id = "podcast"` and `scenario_title` = the show's title, stamped with the practice
language like any conversation. Every line is an ordinary `messages` row: host lines are
`assistant`, learner lines are `user`. The podcast-only facts live in three new tables owned by a
new `app/podcasts/` module: the episode (format, length, show), its hosts, and one row per host
line (who spoke it and why). See [data-model.md](data-model.md) §2.

**Rationale**:
- `/api/learning/*` resolves languages from `message_id → conversation`, `/api/vocabulary` saves
  words with `source_conversation_id`, `/api/audio/tts/{message_id}` caches by message, the
  corrections tables key on `message_id` and `conversation_id`, and `/api/chat/helper` takes a
  `conversation_id`. All of them work on an episode unchanged (FR-027, FR-028, FR-029).
- Past Chats lists conversations, so episodes appear in it by construction (FR-032). The podcast
  label is added from the podcast module's own list (R17).
- FR-025 ("keeps its language for its whole life") and the "practice language changed
  mid-episode" edge case are already how conversations behave.
- The core `conversations` and `messages` tables gain **no columns**. FR-034 and SC-011 are
  easier to keep when nothing existing changes shape.

**Alternatives considered**:
- *A separate `episodes` + `episode_lines` table pair*: rejected. Every learning tool, the TTS
  cache, vocabulary and corrections would need a second code path or a polymorphic key.
- *A `speaker` column on `messages`*: rejected. It would put a podcast concept in the core table
  that every roleplay row carries as `NULL`, and make `messages` depend on a feature table.

---

## R2. Turn-taking: the code chooses the speaker, the model writes the line

**Decision**: A pure `TurnPolicy` in `app/podcasts/services/turn_policy.py` decides, from the
stored lines alone:
- whose turn it is (the learner's, the hosts', or finished);
- for the next host line, a `LineCue`: which host speaks, the line's purpose (`intent`: open,
  greet, discuss, wrap up, sign off), and whether the line must end by inviting the learner.

The language model is then asked to write **only that host's line**. The rules below are
enforced by the policy, not requested from the model:

| Rule | How the policy enforces it |
|---|---|
| FR-012 one host per line | One cue names one host; the sanitiser removes anything else (R4) |
| FR-013 flow, not rotation | After a host line, the other host answers with probability 0.7 and the same host continues with 0.3. A host line that names the other host hands over to them |
| FR-014 learner invited by the 4th host line | Panel: each host line since the learner last spoke or passed invites with a rising probability (0.25, 0.45, 0.6, then 1.0 on the 4th). One host: every host line invites (spec interpretation 1) |
| FR-015 run ≤ 3; share ≥ 25% | A host with three lines in a row cannot be chosen. When the two hosts' line counts differ by 2, the host with fewer lines speaks next |
| FR-018 addressed host first | A learner line that names one host (accent- and case-insensitive, whole word) makes that host speak next. If both are named, the first named speaks |
| FR-019 length | When the host-line count reaches the chosen length and no wrap-up has been given, the next host line is the wrap-up. In Listen, the line after it is the sign-off, which ends the episode. End episode always gets a sign-off |

Probabilities come from an injected `random.Random`, so tests are deterministic. Priority when
rules collide: run cap > addressed host > balance > hand-over > random. The addressed-host rule
cannot break the run cap, because a learner line resets every run.

**Rationale**:
- SC-002 asks for 100% compliance over 100 learner turns. A probabilistic model cannot promise
  that; a pure function can, and property tests over thousands of simulated episodes prove it
  before any model is involved.
- The model's job becomes the one it is good at: writing a short in-character line. A model
  asked to write "Lucía's next line" will not also write Marco's nearly as often as a model asked
  to "continue the podcast" (SC-003).
- The invitation is a stored flag, so "the screen shows it is the learner's turn" (US3-3) never
  depends on parsing the model's text for a question mark.

**Alternatives considered**:
- *The model picks the speaker in a JSON reply* (`{"speaker": …, "line": …}`): rejected. Nothing
  enforces the run and invitation limits, and constrained JSON on every line adds latency and
  rules out the session (R3).
- *Generate a whole segment (several lines) per call*: rejected. It invites cross-speaker text
  (SC-003), and a Jump in would discard the unplayed lines.
- *Strict alternation*: rejected by FR-013.

---

## R3. Host lines go through the existing conversation engine

**Decision**: Episodes use `ConversationEngine` with a new `SessionKind.PODCAST`, so an episode
keeps Ollama loaded and a Claude process alive between lines, exactly as a roleplay does (004).
The session's saved history is built from the stored lines plus **producer cues**:
- each host line is an `assistant` turn with id `p{message_id}` and its stored (sanitised) text;
- each learner line is a `user` turn with id `p{message_id}`, rendered as
  `"{learner label}: {text}"`;
- before every host line there is a `user` turn, the cue, with id `c{position}`. `position` is the
  number of lines before it. Its text is rendered from the host line's stored `host`, `intent`,
  `invites_learner` and the preceding line's `is_passed` flag, by the same pure `render_cue()` that
  wrote it.

The next line's request ends with a fresh cue at position `len(lines)`. That satisfies
`TurnRequest`'s invariant (the history ends with a user turn), and on a rebuild every earlier cue
is re-rendered byte-for-byte from stored facts. **No cue is stored as text**, and the engine, pool,
sync and both provider sessions are **unchanged** apart from the new enum member.

When the sanitiser removed text from a line (R4), the router calls `engine.end(key)` after
storing the line. The provider's context would otherwise hold the discarded words, and the saved
history is the source of truth (004, R-15).

A level change alters the standing prompt, so the existing fingerprint check rebuilds the session
and the next line follows the new level (FR-026, "level changed mid-episode").

**Rationale**:
- SC-009 (next line within 5 s after Continue) and the Claude experience both benefit from a warm
  session far more in a podcast than in a roleplay, because a Listen episode generates on every
  press.
- The engine's rule is that routers never build message lists or touch provider sessions. Cues as
  user turns keep that rule. The alternative of a stateless `llm.chat` per line would bypass it.

**Alternatives considered**:
- *Stateless `LLMProvider.chat` with the whole transcript per line*: rejected. On Claude every
  Continue would spawn a fresh `claude -p` process (the cost 004 built sessions to avoid), and it
  would be a second way of talking to providers.
- *Store cue text in a table*: rejected. Deriving cues from facts that are stored anyway keeps one
  source of truth, and a cue's wording can improve without migrating old rows.
- *Extend `TurnRequest` with a "no learner turn" mode*: rejected. It would change the engine, the
  pool and both provider sessions for something a user-role cue already expresses.

---

## R4. Keeping each line to one speaker

**Decision**: `LineSanitiser` (pure) post-processes every host line before it is stored or shown:
1. strip a leading label for the speaking host (`Lucía:`, `**Lucía:**`, `[Lucía]`);
2. cut the text at the first line or sentence that starts with **another participant's label**:
   the other host's name, the learner's name, or a guest label from the catalogue of role words
   (`Guest`, `Learner`, `User`, `You`, and the practice language's own words for guest, which live
   in the language catalogue as `guest_labels`);
3. drop bracketed stage directions (`(laughs)`, `*risas*`).

If nothing is left, the line is regenerated once. If it is still empty, the request fails with a
plain message and a retry (the edge case "the model writes another speaker's lines"). Each stored
host line records `was_trimmed`, so SC-003 can be audited from the database.

**Rationale**: the standing prompt already forbids other speakers' words (R5), but a small model
will sometimes script the whole exchange. Cutting at a label is conservative: it never invents
text, and it removes exactly the failure SC-003 counts.

**Alternatives considered**: *reject and regenerate every trimmed line*: rejected. It doubles
latency on the most common failure, when the host's own words before the label are usually fine.

---

## R5. Prompts: one standing prompt per episode, one short cue per line

**Decision**: A new `app/podcasts/prompts.py`. `prompts/templates.py` is not edited, so the
roleplay prompts stay byte-identical (FR-034).
- **Standing prompt**: the practice-language rule (the same wording as the roleplay's
  CRITICAL LANGUAGE RULE, with language names from `ConversationLanguages`), the show (title,
  premise, the learner's role), each host (name, personality description, speaking style, show
  role, and the angle for generated shows), and the line rules:
  - write only the words of the host named in the producer note;
  - no name label and no stage directions;
  - never speak for the other host or the learner;
  - address the learner by the label given;
  - producer notes are never read aloud or mentioned.

  The level's rules are appended last with the existing `with_partner_speech_rules()`, so a line
  is held to the same limits as a roleplay reply (FR-026, SC-006).
- **Cue**, which stays under ~40 tokens, for example:
  `[Producer note, not part of the show] Next: Marco. React to Lucía, in character. End by asking
  our guest a question.` An invitation after two lines from different hosts asks the learner to
  settle it, which gives US3's "settle a disagreement".
- **Learner label**: the learner's name if given, else "our guest" (FR-011). A learner who writes
  in English is handled by the language rule, as in roleplay.

**Rationale**: reusing the level renderer means 005's measured behaviour carries over, and
SC-006 compares like with like. English instructions around target-language output are what every
existing prompt does.

---

## R6. Hosts: names, personalities and voices are cast by code

**Decision**: A `HostCaster` in `app/podcasts/services/casting.py` builds every host, for ready-made,
generated and Surprise me shows alike:
- **Voice**: the installed voices for the episode's language (`voices_for()` filtered by
  `VoiceInstallation`). The lead host takes the first, the second host takes a different one.
  With fewer than two installed, both share one voice and the setup screen says so (edge case,
  FR-007).
- **Name**: drawn from the language's name bank for the voice's gender (a female voice gets a
  female name), excluding the other host's name and the learner's name (FR-008, edge case).
  Ready-made shows get a stable default by hashing `show_id + slot`, so *Weekend Food Talk* in
  Spanish always opens with the same host.
- **Personality**: from the catalogue of ten (R8); the two hosts always differ (FR-007).

Name banks, guest labels and the voice-sample sentence are **language data**. They go into
`PracticeLanguage` in `practice_languages/catalog.py` as three new fields, because that module is
the only place a language code may appear (006, and `test_no_language_literals.py`). A third
language adds its names in its one catalogue entry.

Shuffle (FR-010) calls `HostCaster.recast(slot, other_host, learner_name)`: a new name and
personality, keeping the voice when there is no third voice to move to. The voice sample speaks
`sample_line.format(name=…)` in the host's voice.

**Rationale**:
- Names chosen by code are guaranteed distinct, language-appropriate and never the learner's name.
  SC-007's "distinct, language-appropriate host names" becomes a unit test.
- Matching name to voice gender avoids a jarring mismatch the spec does not mention but a
  listener would notice.

**Alternatives considered**: *let the generator model invent names*: rejected. The model cannot
see which voices are installed, and would repeat names across hosts.

---

## R7. Voices: none to download; per-host speech; never a silent substitute

**Decision**:
- **No new voice downloads.** Each language already has two installed voices of different genders
  (`es_ES-davefx-medium` and `es_AR-daniela-high`; `de_DE-thorsten-medium` and
  `de_DE-kerstin-low`), which meets FR-030. Adding a voice later is one `VoiceInfo` entry and one
  `run.sh` key, which the existing invariant test checks.
- **Speaking as a host**: `SpeechForLanguage` gains `provider_for_voice(language, voice_key)`. It
  raises `VoiceUnavailable` when the voice is not installed **or does not speak that language**,
  with a host-specific message ("Marco's voice isn't installed …"). It never picks another voice
  (FR-031, Principle VI).
- **The audio endpoint** needs to know that a message belongs to a host. A one-method consumer
  interface, `MessageVoiceLookup.voice_for_message(message_id) -> str | None`, is declared in
  `services/tts/base.py`. The podcast module implements it, and `services/factory.py` wires it in.
  `None` means the conversation's voice, as today. The audio router never imports the podcast
  module.
- **Listen with a missing voice**: that host's lines are shown in full even with Show text off,
  because a hidden, silent line would be empty (spec interpretation 5).

**Alternatives considered**:
- *Download a third voice per language for variety*: deferred. It adds 60–120 MB per voice to setup
  and isn't needed by any requirement. The catalogue makes it a data change.
- *A `voice_key` column on `messages`*: rejected (R1).

---

## R8. Catalogues: formats, lengths, personalities and ready-made shows

**Decision**: `app/podcasts/catalog.py` holds four immutable catalogues. It is the one place each
is defined (FR-004):
- **Formats**: `one_host` (1 host, learner speaks), `panel` (2 hosts, learner speaks, Jump in and
  Pass), `listen` (2 hosts, learner listens). Each `PodcastFormat` descriptor carries `host_count`,
  `is_learner_speaking`, `has_jump_in`, `max_host_run`, and `invite_deadline` (1 or 4). A
  four-person panel would be a new descriptor plus a third host slot, with no policy change,
  because the policy reads these fields.
- **Lengths**: `short` 10, `medium` 20 (the default), `long` 40 host lines (FR-019).
- **Personalities** (ten, FR-006): enthusiast, dry sceptic, storyteller, curious interviewer,
  expert, joker, warm mentor, contrarian, dreamer, pragmatist. Each has a learner-facing label and
  description, and a prompt-facing speaking style.
- **Ready-made shows** (eight, FR-002): Weekend Food Talk (food), Tech for Normal People
  (technology), Game Day (sport), On the Road (travel), Screen & Sound (film and music), Nine to Five
  (work life), Home Sweet Home (housing and family), Big Little Questions (everyday curiosities).
  Each has an English title and premise, a topic, the learner's role, and default personalities for
  the lead and second host. Titles are English interface text, like scenario titles (006
  interpretation 3).

Catalogue invariants (data-model §1) are unit-tested: unique ids, at least eight personalities and
six shows, and two different default personalities per show.

---

## R9. The generator and Surprise me

**Decision**:
- **Generate** (`POST /api/podcasts/shows/generate`) sends the idea, and the learner's interests if
  any, to `StructuredLLMProvider.chat_json` with a JSON schema. The schema asks for `is_suitable`,
  `decline_reason`, `title`, `premise`, `topic`, `learner_role` (enum), and for each host a
  `personality` (catalogue enum) and a one-line `angle`. Code then casts names and voices (R6). A
  duplicate personality is replaced by the catalogue's next one rather than rejected.
- **Declines** (FR-024): an empty idea or one over 200 characters is rejected locally with a 422
  before any model call. The model judges suitability through `is_suitable`, and an unsuitable
  idea gets a fixed plain message and `can_surprise: true`. The model's own `decline_reason` is
  logged, never shown.
- **Another version** (FR-021) repeats the call with the previous title in `avoid_titles`.
  Generated shows are returned to the client as a **draft** and never stored. Only starting an
  episode persists a show (spec Key Entities).
- **Surprise me** (FR-022, FR-023) builds an idea in code, then calls the generator:
  - the seed topic is one of the learner's interests with probability 2/3 when the list is not
    empty, otherwise one of 40 built-in topics;
  - an angle is added from 12 built-in angles ("a beginner's guide to", "a friendly debate
    about", …);
  - a process-wide `RecentSurprises` remembers the last 10 (topic, angle) pairs and never repeats
    one.

  SC-008 (15 distinct in 20) therefore holds by construction for topic × angle, and the benchmark
  checks that the generated titles differ too.

**Rationale**: structured output is already proven for corrections (003) on both providers. Keeping
names and voices out of the model's hands is what makes SC-007 testable. Randomness in code makes
FR-023's "more often than not" a deterministic test over seeded draws.

**Alternatives considered**: *a local keyword blocklist for FR-024*: rejected as the primary check.
It is easy to evade and blocks innocent ideas ("dangerous sports"). The model's judgement,
reviewed in the SC-007 benchmark, is the check.

---

## R10. Where the new learner preferences live

**Decision**:
- **Podcast preferences**: last format, Show text, interests, and the name the hosts use. They go
  in a podcast-owned single-row table, `podcast_preferences`, read and written through
  `/api/podcasts/preferences`. The last format is written when an episode starts (FR-005).
- **Summary language** (FR-040) is used by roleplay and podcasts alike, so it is a column on
  `app_settings` (`summary_language`, `'conversation'` or `'native'`), written through the existing
  `PUT /api/settings`, as `conversation_level` was in 005.

**Rationale**: "saved with the learner's settings" in the spec is about persistence, not a table.
Podcast-only preferences in a podcast table keep the settings router and `AppSettingsRecord` free
of a feature they do not serve (Principle V). The summary language is cross-feature, and the
settings record is where cross-feature choices already live.

---

## R11. Sharing the turn mechanics that chat.py keeps private

**Decision**: Move the pieces of `routers/chat.py` that a podcast turn also needs into a new
`app/conversation_turns/` package, with an unchanged public shape:
- the SSE frame helper;
- `_EngineTurn`, `_SavedReply` and `_relay_engine_reply`;
- `ChatMessageRequest`, `_save_learner_message` and `_is_low_confidence`;
- `_Corrections`, `_plan_turn_failing_open` and `_turn_context`;
- `_schedule_tts`.

`chat.py` imports them from there, and the podcast router does the same. This is a move, not a
rewrite, and the existing chat tests are the safety net: they must pass untouched.

**Rationale**: the podcast learner turn is identical to the roleplay learner turn up to "produce the
reply": save the message, plan corrections, emit feedback, and honour a Strict pause. Importing
another router's private functions is not allowed (Principle V), and copying them would be a second
copy of the correction flow.

---

## R12. HTTP shape: SSE for anything that produces a line; one line at a time

**Decision**:
- `POST /api/podcasts/episodes/{id}/next` (Continue, the opening, and retry), `/message` (the
  learner speaks, or jumps in), `/pass` and `/end` all return an SSE stream. It uses the chat
  frames `user_message_saved`, `feedback` and `error`, and adds a `line` frame with the whole
  sanitised line and the new turn state. There are no token frames, because a line must be
  sanitised before it can be shown (delivery was already batched in 004).
- Which line to produce next is derived from the stored lines, not from the endpoint. `/next`
  after a failed reply therefore retries that reply, which is the "retry the same line" edge case.
- **One line at a time per episode**: a per-episode, non-blocking in-process lock. A second request
  while a line is being produced gets `409` ("A line is already on its way."). This prevents a
  double-pressed Continue from producing two lines from one stale state.
- Summary, preferences, the catalogue, shuffle and generation are plain JSON.

**Alternatives considered**: *plain JSON for `/next`*: rejected. It would give the podcast page two
client paths for the same errors and feedback that `/message` must stream anyway.

---

## R13. Conversation summary

**Decision**: a new `app/conversation_summary/` module, used by roleplay and podcasts alike, served
at `GET /api/conversations/{id}/summary`.
- **Both languages in one call**: `chat_json` returns up to five points, each a pair
  `{conversation_language, english}`. The two versions describe the same points **by construction**
  (FR-038, SC-013), and switching language is instant, with no second request (SC-014).
- **Grounding** (FR-036, SC-012): the prompt holds only the transcript, with each line labelled by
  speaker. It says to use only what was said, name the host behind each point in a podcast
  (FR-037), end with where the conversation stands, and use no more than five points. The
  conversation-language text gets `with_learner_text_rules()` at the learner's level, plus a
  "short, simple sentences" rule that also applies at Natural (FR-039).
- **Speaker labels** come through a consumer interface, `SpeakerNames.names_for(conversation_id)
  -> Mapping[int, str] | None`. The podcast module supplies host names, and `None` (a roleplay)
  means "Learner" and "Partner".
- **Caching**: the latest summary per conversation is stored with the last message id and level it
  covers. Opening Summary again with no new lines and the same level returns it at once. Any new
  line misses the cache (FR-042).
- **Long transcripts**: the transcript is folded in chunks of about 6,000 characters. Each step
  gets the previous step's English points plus the next chunk. With a cached summary, only the
  lines after it are folded in. Every model call stays inside a small context (R14), and the
  "summary stays short" edge case holds.
- **Too early**: fewer than two lines means `status: "too_early"` with a plain message, and no
  model call.
- **Isolation** (FR-041): the summary uses the stateless `StructuredLLMProvider`, never the
  conversation's session. It reads saved lines only, so a line being produced is neither
  interrupted nor included.

**Alternatives considered**:
- *Two calls, one per language*: rejected. The versions could disagree (SC-013), and switching
  would cost a second wait.
- *Summarise inside the conversation's session*: rejected. It would add turns to the session's
  context and break FR-041's "no line was added".

---

## R14. Context budget on the default local model

**Decision**: no provider configuration changes. The podcast keeps its per-line overhead small:
- the standing prompt stays under ~700 tokens, measured by a unit test that uses a 4
  characters-per-token bound;
- each cue stays under ~40 tokens.

A Long episode on `llama3.1:8b` can still outgrow Ollama's default context window. When it does,
Ollama keeps the system prompt and drops the oldest turns, so the hosts forget the start of the
episode rather than failing. The benchmark (R16) records `prompt_eval_count` on Long episodes. If
the drift is noticeable, `docs/architecture.md` § "Open items" records it along with the option of
a configurable `num_ctx`.

**Rationale**: raising `num_ctx` for every Ollama call would change roleplay memory use and
latency, which FR-034 forbids without a measured reason. The summary never depends on the context
window, because it folds (R13).

---

## R15. Frontend structure

**Decision**:
- **Routes**:
  - `/podcasts`: the Podcasts screen, with show cards, the generator, Surprise me and interests;
  - `/podcasts/setup`: format, length, hosts, your name, and Start;
  - `/podcasts/episodes/:conversationId`: the episode.
- **The episode page stays thin.** Its state machine lives in `usePodcastEpisode`, which loads the
  episode, runs the SSE actions and holds the turn state. Presentation is split into small
  components:
  - `HostLine`, which wraps the existing `MessageBubble` with the speaker's name and the Listen
    hidden or revealed state, so `MessageBubble` is not modified;
  - `EpisodeControls`, with Continue as the primary action at the hosts' turn and Jump in, Pass and
    End episode as secondary actions;
  - `ShowTextSwitch` and `TurnBanner`.

  The input bar reuses `RecordButton`, `SuggestedResponsePanel`, `ExpressionHelperPanel` and
  `FeedbackNote` as they are.
- **Summary** is a shared `SummaryButton` and `SummaryPanel` in `components/chat/`, driven by
  `useConversationSummary` (TanStack Query, keyed by conversation and last message id). It is added
  to the Chat header and to the episode header. The panel is a non-modal disclosure, so closing it
  changes nothing (FR-041).
- **Drafts**: a generated or Surprise me show travels to the setup screen in router state. A
  ready-made show is addressed as `/podcasts/setup?show={id}`. Reloading the setup screen with a
  lost draft returns to `/podcasts` with a plain message.
- **API**: a new `services/podcastsApi.ts`, as `flashcardsApi.ts` did. The summary call and the
  `summary_language` setting go in `api.ts`.
- **Home** gains a "Podcasts" nav pill (FR-001) next to Past Chats; the primary action stays
  starting a scenario.

**Alternatives considered**: *extending `Chat.tsx` with a podcast mode*: rejected. `Chat` is already
about 520 lines (004 and 005 recorded splitting it as a follow-up), and the podcast turn model
(Continue, Jump in, Pass, hidden text) differs from it at every step.

---

## R16. Measuring the model-dependent criteria

**Decision**: follow the hand-run benchmark pattern of 003, 005 and 006 (`@pytest.mark.benchmark`,
deselected by default), plus review sheets for the criteria that need a human.

| Criterion | How |
|---|---|
| SC-002 turn-taking | **Automated, deterministic**: property tests over 1,000 simulated Panel episodes with a scripted writer. **Benchmark**: 10 real Panel episodes × 10 learner turns, checking that each invitation line actually addresses the learner |
| SC-003 one speaker per line | Benchmark over 10 Listen and 10 Panel episodes: `was_trimmed` count, plus a check of the stored text for any participant label |
| SC-004 speaker identifiable | Review sheet: 10 episodes, with the label stripped |
| SC-005 language | Reuse 006's `wordfreq` foreign-word check on every host line, in both languages |
| SC-006 level | Reuse 005's level measurement on host lines vs roleplay replies, same model |
| SC-007, SC-008 generator | Benchmark: 20 ideas, and 20 Surprise me presses |
| SC-009, SC-014 latency | Benchmark timings at p90 on the default local setup |
| SC-010 offline | Manual quickstart step with the network disabled |
| SC-011 upgrade | Automated: a frozen `schema_006.sql` fixture, `init_db()` run twice, every row unchanged |
| SC-012, SC-013 summary | Review sheet: 20 summaries |

---

## R17. Past Chats

**Decision**: `GET /api/podcasts/episodes` returns a summary of each episode keyed by
`conversation_id`: show title, format label, host names, language name and status. The History page
fetches it alongside `/api/conversations`. Rows that are episodes get a "Podcast · Panel · Lucía &
Marco" label and link to the episode screen instead of `/chat/:id` (FR-032, US1-6). The
conversations router is unchanged.

**Alternatives considered**: *a `kind` field on `ConversationResponse`*: rejected. The conversations
router would have to know about podcasts, which reverses the dependency.

---

## R18. Schema changes are additive

**Decision**:
- **New tables** via `create_all()`: `podcast_episodes`, `podcast_hosts`, `podcast_host_lines`,
  `podcast_preferences` and `conversation_summaries`.
- **One `_ADDITIVE_COLUMNS` entry**: `app_settings.summary_language VARCHAR(12) NOT NULL DEFAULT
  'conversation'`.

No existing row is updated. SC-011 is proven against a frozen pre-007 schema fixture, as 006 did
with `schema_005.sql`.
