# Research: Configurable Podcast Shows

**Feature**: `011-configurable-podcast-shows` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

Each decision gives the choice, why it was made, and what else was considered. References to
existing code use the state of `011-configurable-podcast-shows` @ `bad97c7`.

---

## R1. Where "how hosts talk" lives: a `HostTalk` strategy, chosen once per episode

**Decision**: Add `app/podcasts/services/host_talk.py` with a small `HostTalk` ABC and two
implementations:

- `LegacyTalk`: today's behaviour, byte for byte. It covers the reply cap, invitations on every One
  host line, Panel's hazards, `discuss` lines, and the "Keep each line to a few sentences" rule.
- `ConfiguredTalk(settings)`: this feature's behaviour, driven by the episode's stored settings.

`host_talk_for(settings: EpisodeSettings | None)` is the only place a settings record becomes
behaviour. An episode with no settings row gets `LegacyTalk`. That row is `podcast_episode_settings`
(data-model §2.1), and every episode started before this feature lacks one. `TurnPolicy`, the
standing prompt and `render_cue` all ask the episode's `HostTalk` for the following:

| Method | Answers |
|---|---|
| `invites(run, rng)` | Whether the host line at position `run` since the learner spoke invites them |
| `discussion_intent(state, rng)` | Which kind a discussion line is (R4) |
| `line_rules(label, languages)` | The standing prompt's line rules |
| `speech_rules(prompt, level)` | The level block (R2) |
| `instruction(cue, cast, label)` | A cue's instruction for the line kinds it knows |
| `closing(cue, label)` | The cue's last sentence: invite, or do not ask (R5) |

**Rationale**:
- FR-025 requires that an unfinished pre-feature episode resume exactly as it started. The engine
  fingerprints the standing prompt and re-renders every cue from stored facts (007 R3), so "as it
  started" means byte-identical text. Keeping the old behaviour as one whole object keeps the 007
  one-off golden test and 010's series prompt tests valid unchanged.
- The presence of a row is data, as 010's link row is (constitution V, no flags). One factory
  function maps it to a strategy (OCP).

**Alternatives considered**:
- *Backfilling old episodes with settings that mean "today"*: rejected. Conversation · Short · Often
  is close to today's behaviour, but its prompt text differs (R5), so a resumed episode's session
  would rebuild with new rules mid-episode.
- *`if settings is None` checks inside `prompts.py` and `turn_policy.py`*: rejected. That scatters
  the same branch across a dozen functions.

---

## R2. Line length versus level: a third level renderer without the reply cap

**Decision**: `app/conversation_levels/` gains a third pure renderer,
`with_sentence_rules(prompt, level)`. It produces the partner block from `rules.py` without the
`Say at most N sentences per reply.` line. It keeps the per-sentence word limit, joining, tenses,
vocabulary, idioms, the "Questions to the learner" line and the four behaviour lines. At Natural it
returns the prompt unchanged, like the other two renderers.

`ConfiguredTalk.speech_rules` uses it. `LegacyTalk` keeps `with_partner_speech_rules`. The sentence
count comes from a new catalogue in `app/podcasts/catalog.py`:

| `HostLineLength` | Sentences | Phrase in the cue |
|---|---|---|
| `short` | 1–2 | "in one or two sentences" |
| `medium` (default) | 3–5 | "in three to five sentences" |
| `long` | 5–8 | "in five to eight sentences" |

The count is stated twice:
- once in the standing prompt's line rules ("Each host line has three to five sentences unless the
  producer note says otherwise; every sentence follows the rules at the end");
- once in every cue, because a per-line instruction holds better on `llama3.1:8b` than a standing
  rule, as 005 found for levels.

**Rationale**:
- FR-001 requires a split: the level owns each sentence, Host lines owns the count.
- Removing the cap through a new function leaves the roleplay partner's block byte-identical, which
  005's tests pin. The level module stays the only place level limits are turned into text, and
  podcasts import only its root.

**Alternatives considered**:
- *A `max_sentences` override parameter on `with_partner_speech_rules`*: rejected. It changes a
  shared signature for one caller, and a flag-like argument breaks the clean-code rules.
- *A podcast-only copy of the level lines*: rejected. It duplicates `_shared_lines` and drifts the
  moment a limit changes.

---

## R3. How often the learner is asked: per-setting hazards, deadline 4 everywhere

**Decision**: Invitations become a catalogue entry per setting, `InviteFrequency`. Each entry holds
the chance that the 1st, 2nd and 3rd host line since the learner last spoke or passed invites them.
The 4th line always does (FR-003, 007 FR-014).

| Setting | Hazards (1st, 2nd, 3rd) | Expected share of host lines that invite |
|---|---|---|
| `often` | 1.0 | 1 in 1 (today's One host) |
| `sometimes` (default) | 0.35, 0.45, 0.55 | about 1 in 2.2 (0.46) |
| `rarely` | 0.0, 0.05, 0.10 | about 1 in 3.8 (0.26) |

The following stay as they are:
- the wrap-up line still invites in a speaking format, so the learner gets the last word on the
  topic;
- the sign-off never invites;
- Panel's balance rule (`_gap_after`) still applies.

**Rationale**:
- SC-001 caps inviting lines at 50% with the defaults. `sometimes` sits at 46% before wrap-up, which
  leaves headroom.
- A hazard per position keeps the deadline exact. Expected rates are checked by a seeded property
  test over 10,000 simulated runs: `sometimes` in [0.40, 0.50], `rarely` in [0.22, 0.30], and never
  five host lines in a row.
- Today's Panel schedule (0.25, 0.45, 0.60) averages about 1 in 2.3, so Sometimes keeps Panel's feel.

**Spec reading**: FR-003 says Often means every host line in both formats, and the plan follows it.
FR-026's "Conversation · Short · Often reproduces today's behaviour" is then exact for One host. In
Panel, today's behaviour is closest to Sometimes (plan, Spec interpretations).

**Alternatives considered**:
- *A fixed every-Nth-line rhythm*: rejected. It is predictable and robotic.
- *Letting the model decide when to ask*: rejected. This is the behaviour the learner complained
  about, and 007 R2 already moved the decision to the policy.

---

## R4. Line kinds: the policy picks react, explain, story, answer or follow-up

**Decision**: In a configured episode, a discussion line's `intent` is one of five new values. All
fit `podcast_host_lines.intent String(10)`, and legacy episodes keep `discuss`.

| Intent | When | Asked for |
|---|---|---|
| `answer` | The learner's last line asks a question (it contains `?`) | Answer it first and clearly, never with only a question; if two were asked, answer one and say the other is coming |
| `follow_up` | The learner's last line had two or more `?`, and the one host line since was `answer` | Answer the other question from before |
| `react` | Drawn by Style weight | React to the last line and add something of your own |
| `explain` | Drawn by Style weight | Explain one thing about the subject simply |
| `story` | Drawn by Style weight | Tell a short story or example from your own life |

The Style weights are a catalogue entry:

| Style | React | Explain | Story |
|---|---|---|---|
| `conversation` | 0.90 | 0.07 | 0.03 |
| `balanced` (default) | 0.55 | 0.30 | 0.15 |
| `presented` | 0.35 | 0.40 | 0.25 |

`answer` and `follow_up` take priority over the Style draw. `open`, `greet`, `wrap_up` and
`sign_off` keep their rules in `_intent`. The draw uses the policy's injected `random.Random`, so
it is seeded in tests.

**Rationale**:
- FR-005 and FR-006 become properties of the policy rather than hopes about the model, as 007 did
  for speakers. The stored intent rebuilds the cue byte for byte (`stored_cue`), so history stays
  stable.
- SC-004 asks for at least 40% explain or story lines in Presented (65% expected) and at most 20% in
  Conversation (10% expected). The margins absorb model drift, which the review sheet measures.

**Detecting a question with `?`**: `?` is language-independent across the practice languages (`¿…?`
in Spanish), and Whisper punctuates spoken questions. A question without `?` is still covered by the
standing rule "When {label} asks a question, answer it first" (R5). No per-language list of question
words is needed (FR-027).

**Alternatives considered**:
- *Asking the model to classify the learner's line*: rejected. It adds an extra call per turn
  against SC-011.
- *Only a standing rule, no answer cue*: rejected. That is how episode 44 happened.

---

## R5. Prompt and cue text for configured episodes

**Decision**: `ConfiguredTalk` renders the standing prompt in this order:

1. The language rule.
2. The show section. The learner's role comes from the episode's Your role. When Today's subject is
   set, the section adds "Today's subject, chosen by {label}: {subject}. Talk about it within the
   show's topic."
3. The hosts section.
4. In One host only, the covered-role sentence (R6).
5. The series section (010; R11 adds guest and away lines).
6. The line rules, with these changes:
   - "Keep each line to a few sentences" becomes the Host lines count;
   - "When {label} asks a question, answer it first; never answer only with a question." is added;
   - "Only ask {label} something when the producer note says so." is added.
7. The level sentence rules (R2), last.

Each cue is: the producer marker, then `Next: {name}.`, then the intent's instruction with the
Host-lines phrase, then the after-pass sentence, then a closing. The closing is one of:
- `End by asking {label} a question.` (or `to settle it`, as today) when the line invites;
- **`Don't ask {label} anything this time.`** when it does not.

**Rationale**:
- The learner's main complaint is that every line ends in a question. The model adds a question by
  habit unless told not to, so a line that does not invite says so explicitly.
- The new rules add at most about 600 characters to the standing prompt. A unit test bounds a
  configured prompt at 900 tokens with a full series section: the 007 budget of 700, plus 010's
  section.

**Alternatives considered**:
- *Putting the sentence count only in the standing prompt*: rejected. Per-line instructions win on
  small models (005 R4).

---

## R6. One host covers the absent second host's role (FR-007)

**Decision**: At Start, a One host episode records the personality of the host who is not taking
part:
- the draft's second host for a one-off;
- the series' second host for a series episode.

It is stored as `podcast_episode_settings.covered_personality`. The standing prompt then adds:

> "This show usually has a second host, the {Expert}: {description}. Today you play that part too:
> {speaking_style}"

**Rationale**: The show keeps its purpose; Big Little Questions' interviewer also gives the expert's
answers. The value is stored rather than looked up, so a later recast or a reset series cannot change
a resumed episode's prompt (FR-012).

**Alternatives considered**:
- *Using the show template's second personality*: rejected. A learner-made show, or a series whose
  second host was recast, has its own second host.

---

## R7. Episode settings are a frozen row beside the episode

**Decision**: A new table, `podcast_episode_settings`, keyed by `conversation_id` and cascading from
the episode. It holds:
- `style`;
- `line_length`;
- `invite_frequency`;
- `today_subject`;
- `covered_personality`.

It is written in `create_episode`'s transaction, and nothing updates it afterwards (FR-012).

**Your role** needs no new column: `podcast_episodes.learner_role` already stores the role an
episode was started with. This feature fills it from the episode settings instead of copying the
show's role.

In Listen, `invite_frequency` is stored as the default and ignored, because a listening format never
invites. Today's subject is stored, so a resumed episode keeps it.

**Alternatives considered**:
- *Additive columns on `podcast_episodes`*: rejected. Every existing row would get default values,
  which would make it look configured and break R1's "no row means legacy" rule.

---

## R8. Last-used settings outside a series (FR-013)

**Decision**: `podcast_preferences` gains three additive columns through `_ADDITIVE_COLUMNS` in
[database.py](../../backend/app/database.py), each with the new default:
- `last_style`;
- `last_line_length`;
- `last_invite_frequency`.

A **one-off** start writes them in `_remember_start`; a series start does not. `last_format` and
`learner_name` stay as they are.

Your role and Today's subject are never remembered. The setup starts Your role on the show's own
role.

**Rationale**: These are preferences of the same kind as `last_format`, already stored in that
table. Additive columns are the project's only schema-change mechanism. This is the one exception
to 010's "database.py untouched".

---

## R9. Series settings and scopes (FR-014 to FR-019)

**Decision**:
- **Storage**: a new table, `podcast_series_settings`, keyed by `series_id` and cascading from the
  series. It holds:
  - `format`;
  - `length`;
  - `style`;
  - `line_length`;
  - `invite_frequency`;
  - `learner_role`.

  A series with no row (every pre-feature series, and every series after a reset) has the **show's
  standard settings**:
  - One host;
  - Medium length;
  - Balanced, Medium lines, Sometimes;
  - the show's own role.

  This is FR-019's target and FR-025's starting point. `SeriesSettings.standard(show)` is the one
  place it is built.
- **Episode 1** of a series writes the row from its own choices (FR-014). No scope is asked, because
  the series has no usual settings yet.
- **Later episodes**: the request carries the effective settings for this episode, plus
  `from_now_on`, the names of the settings whose new value becomes the series' usual value.
  `SeriesService` checks the following, then writes the new series values in the same transaction as
  the episode, so a failed start changes nothing (FR-017):
  - each name is one of the six setting names;
  - each named value is the value this episode uses.

  Settings not named apply to this episode only. Hosts are not a request setting: a guest is
  one-episode by nature (R10), and Recast keeps 010's immediate, confirmed action (FR-023).
- **Reset** (FR-019): `DELETE /series/{id}/settings` removes the row after the client confirms. Past
  episodes, the count, the hosts and the memory are untouched.
- **The setup** reads the series' usual settings from `GET /series/{id}` (`usual_settings`) and
  keeps per-setting scope locally until Start (FR-016). Leaving the screen discards it.

**Rationale**:
- The server never has to diff "what changed": the client sends exactly what this episode uses, plus
  the explicit list of from-now-on changes. The episode's own settings row is always complete, so
  FR-012 holds for series episodes too.
- A scope can only be chosen for a setting that differs from the usual value. The server does not
  need to enforce that, because naming an unchanged setting is a no-op.

**Alternatives considered**:
- *A per-episode override table holding only the differences*: rejected. The episode settings row
  already records everything an episode used. An override is just "episode value ≠ series value",
  which the setup computes.
- *Writing series settings from a separate endpoint as soon as the learner picks "from now on"*:
  rejected. FR-017 requires that leaving without starting discard the change.

---

## R10. Guests: cast on request, checked at Start, never stored on the series

**Decision**:
- **Casting**: `POST /api/podcasts/series/{id}/guest` returns a host draft for one slot.
  `HostCaster.cast_guest(slot, personality_id, present, avoid_names, language)` draws the name and
  voice by the 007 rules (FR-020):
  - the name is not any series host's (the away host's included) nor the learner's;
  - the voice differs from the other present host's when two or more are installed;
  - the personality is the one chosen, or, for the automatic expert of a Panel-this-episode switch
    (FR-024a), the show's second personality (`KeptShow.personalities[1]`). It must differ from the
    other present host's personality.

  The setup calls the endpoint in two cases:
  - when the learner invites a guest;
  - when a One host series switches to Panel for this episode. The draft is shown on the guest's
    card, and "Another guest" casts a new one.
- **Start**: the request carries `guest: {slot, name, personality_id, voice_key, show_role}`.
  `SeriesService` checks it as it checks any host. It also checks that:
  - the episode has **at most one guest**, and at least one regular host takes part;
  - the guest's slot is one the format uses.

  It then builds the episode's hosts as the series hosts, with the guest in its slot, and sets the
  snapshot's `guest_slot` and, when a regular host is replaced, `away_host_name`.
- **Episode prompt** (series section and cues):
  - the guest is introduced as joining for this episode, and does not know earlier episodes;
  - the away host is "away today", never gone (FR-021);
  - the `open` cue names both;
  - the `greet` cue makes a second-slot guest introduce themself as today's guest;
  - a guest in the lead slot (a One host series) opens as standing in for the away host.
- **After the episode**: nothing about the guest is written to the series. The next episode's draft
  has the regular hosts again (FR-022).

**Rationale**:
- Checked, not trusted: 010 R2's principle applies to guests too.
- Casting before Start lets the learner see and hear the guest (acceptance US4-2).
- Allowing only one guest keeps a regular host in every series episode, so the series' memory always
  has someone who remembers. The spec allows a guest "in place of either host" and does not ask for
  two at once.

**Alternatives considered**:
- *Casting the guest inside `POST /episodes`*: rejected. The learner would meet the guest only once
  the episode had started.
- *Storing guests in a series table*: rejected. Nothing needs them after the episode. Its
  `podcast_hosts` row and the snapshot are the record.

---

## R11. "Missed by" marks: derived from who was in each episode

**Decision**: A remembered point is marked as missed by every regular host who did not take part in
the episode it came from. The point stays the same; only how it is rendered changes.

- **Storage**: `SeriesStorage` gains one method, `hosts_present(series_id)`. It returns a mapping
  from conversation id to the names in that episode's `podcast_hosts`, guests included. This is a
  single query.
- **Snapshot**: `SeriesService._snapshot` compares each point's episode with the regular hosts who
  take part now. A point carries `missed_by: tuple[slot]`. In JSON, a marked point is an object,
  `{"text": …, "missed_by": ["second"]}`; an unmarked one stays a plain string. `from_json` reads
  both, so 010 snapshots load unchanged. The snapshot also gains `guest_slot` and `away_host_name`,
  absent in older snapshots.
- **Prompt**:
  - a marked point is rendered `- {text} [{Clara} was away for this]`;
  - one rule is added when any mark is present: "{Clara} only heard about points marked [{Clara} was
    away]: {Clara} may mention them as something heard from the other host, never as having been there or having
    heard {label} say it.";
  - with no marks, the series section is byte-identical to 010's.

**Rationale**:
- Deriving the marks from presence covers the guest episode of FR-022, two guest episodes in a row,
  and a One host episode the second host was never in. A second host who later joins a One host
  series (R12) then does not claim those episodes either.
- Nothing new is stored per point, and the 010 memory tables and keeper are unchanged.

**Alternatives considered**:
- *A `missed_by_slot` column on `podcast_series_memories`, written by the keeper*: rejected. It only
  covers guests, and it marks a slot, which is wrong after a recast.

---

## R12. A One host series switching to Panel from now on

**Decision**: A series always stores two hosts (010). In a One host series the second has never
spoken. A This-and-later-episodes switch to Panel brings that stored host in as the series' regular
second host (FR-024a, 010 FR-009). There is no new casting, because the learner may have seen the
host on the setup screen. Recast still changes them.

`_snapshot` adds a slot to `new_host_slots` (010's "introduce as new") in two cases:
- its host joined at the current count (010's rule, kept);
- its host has never been present in any series episode (R11's `hosts_present`), from episode 2
  onwards.

R11's marks then tell the host which earlier points were only heard about.

**Alternatives considered**:
- *Re-casting the second host at the switch*: rejected. It throws away a host the learner already
  knows from the setup screen.

---

## R13. Long lines start playing quickly: sentence-streamed host lines (FR-002a, SC-011)

**Problem**: Today a host line is written in full, sanitised and stored, then sent as one `line`
frame. Speech is then synthesised for the whole line (`EngineTurn.collect`; 007 R7). A Long line is
5–8 sentences. On the default setup (`llama3.1:8b`, partly on the CPU), the whole line takes several
times longer than a Short one, before synthesis even starts. 010 measured 2.1–3.1 s to a *short*
first line, so SC-011's 5 s cannot hold for Long lines with batched delivery.

**Decision**: stream podcast host lines sentence by sentence, from the model to the speaker.

1. **Engine**: `ConversationEngine.stream_live(provider, request)` is a new method, implemented by
   `ConversationSessionPool.run_turn_live`. It yields tokens as the session produces them, holding
   the key's lock for the generator's life.
   - A retryable error **before the first token** retries once on a rebuilt session, as
     `_reply_with_one_retry` does today.
   - An error **after** the first token, or an abandoned generator, finishes the turn as incomplete,
     so the session is rebuilt from saved history next time. It is then raised or closed.
   - `stream_turn` and the chat path are unchanged: roleplay delivery stays batched, by the 004
     decision.
2. **Thread bridge**: `app/conversation_turns/streaming.py` adds `iterate_in_thread(make_iterator)`.
   It runs the sync iterator in the default executor and hands items to the async caller through an
   `asyncio.Queue` with `call_soon_threadsafe`. Closing the async iterator closes the sync one in its
   thread. The architecture note named this bridge as the cost of real streaming.
3. **Sentences**: a pure `SentenceSplitter` (`app/podcasts/services/sentences.py`) is fed tokens and
   returns complete sentences. A boundary is one of:
   - `.`, `!`, `?` or `…`, plus any closing quote or bracket, followed by whitespace and then an
     upper-case letter, digit, `¿`, `¡` or opening quote;
   - a newline.

   A sentence shorter than 12 characters is joined to the next, so "Sr." does not split alone.
   `flush()` returns the rest. The rules are language-independent: no abbreviation lists, no
   per-language data (FR-027).
4. **Sanitising per sentence**: `StreamingSanitiser` wraps `LineSanitiser`.
   - The first sentence has its own label stripped.
   - Every sentence has stage directions removed.
   - A sentence that starts with another speaker's label ends the line: the rest is dropped and the
     line is `was_trimmed`, as today.

   A property test checks that, for random token splits, the joined result equals
   `LineSanitiser.clean` on the whole text, ignoring whitespace. A line cut before its first kept
   sentence is retried as today's empty line (`LINE_WRITING_ATTEMPTS`). Nothing was sent yet, so the
   retry is invisible.
5. **Speech per sentence**: `SpokenParts` (`app/podcasts/services/spoken_parts.py`) is process-wide
   and built once in the factory, like `MemoryCatchUps`.
   - It synthesises each kept sentence in the host's voice on a **single worker thread**, so parts
     come out in order, into `tts_cache/parts/{stream_id}-{n}.wav`. It keeps a future per part.
   - `GET /api/podcasts/episodes/{id}/parts/{stream_id}/{n}` waits up to 30 s for that future and
     returns the WAV (404 for an unknown part).
   - Entries expire 10 minutes after their line ends.
   - When the voice is missing (007 FR-031), no parts are synthesised and the line stays text, as
     today.
6. **Whole-line audio**: once the line is stored, its parts' WAVs are joined into
   `tts_cache/{message_id}.wav` with the standard-library `wave` module (one voice, so one format),
   and `set_tts_path` is called. Replay and Slower keep using `GET /api/audio/tts/{message_id}`
   unchanged. `schedule_speech` is no longer called for host lines, so nothing is synthesised twice.
7. **Frames** (contracts §4), added to the existing ones:
   - `line_started {stream_id, host_id}`;
   - one `line_part {stream_id, index, text, audio_url}` per sentence;
   - then today's `line` frame, sent once the line is stored, and `done`.

   An error after parts were sent is `{"error", "stream_id"}`. The line is not stored, the session is
   ended (saved history is the source of truth), and the learner sees "The host lost their words.
   Press Retry." Old clients ignore the new events.
8. **Frontend**:
   - `episodeState` gains an `arriving` line (host, sentences so far);
   - `useEpisodeAudio` gains a part queue that plays each `audio_url` in order as it arrives, and
     does not auto-play the final `line` again;
   - Replay and Slower appear once the `line` frame arrives (spec edge case);
   - in Listen with Show text off, the arriving line is hidden like any line.

**Rationale**:
- The time to first sound becomes time to the first sentence plus one sentence's synthesis, whatever
  the length (SC-011).
- Later sentences arrive while earlier ones play. Piper synthesises much faster than real time, so
  the queue stays ahead of playback.
- Storing only complete lines keeps 007 R3's invariant: history is the source of truth, and a line
  is stored before its `line` frame.

**Alternatives considered**:
- *Batched text with speech split into sentences*: rejected. It saves only the synthesis share. A
  Long line's writing time stays on the critical path.
- *Storing a placeholder message and appending to it*: rejected. A half-written row would be visible
  to history, memory and Past Chats.
- *Base64 audio inside SSE frames*: rejected. It is heavy, cannot be cached, and Replay would still
  need the URL.
- *Streaming roleplay chat too*: out of scope (004 decision, spec).

---

## R14. Today's subject: one suitability call inside Start, only when given

**Decision**: When `settings.today_subject` is set (trimmed, 1–120 characters, newlines folded to
spaces), `POST /episodes` first runs `SubjectCheck`, one structured call:
- the request uses 007's suitability rule, worded for a subject;
- the reply schema is `{is_suitable, decline_reason}`;
- the call goes through `get_structured_llm`, so it uses the selected provider.

The outcomes are:
- unsuitable: 422, "That subject can't be used for an episode. Change it or clear it, then
  start.", and the decline reason is logged, never shown (as 007);
- an `LLMError`: 503 with the provider's message (Principle VI, no fallback);
- with no subject, no call is made, so 010 R6's "Start never calls the model" holds for every
  default start.

**Rationale**: The server enforces FR-010 in one round trip. A separate check endpoint would need the
server to trust that the client called it.

**Alternatives considered**:
- *A check-as-you-type endpoint*: rejected. It adds a model call per edit.
- *Letting the hosts refuse in character*: rejected. FR-010 requires that the episode not start.

---

## R15. Jump in for One host, without Pass

**Decision**: `PodcastFormat` gains `has_pass`, which is Panel only. `has_jump_in` becomes true for
One host as well as Panel.
- `turn_actions` gives `can_pass` from `has_pass`.
- `_check_message` and `_check_pass` read the matching flag.

Listen has neither.

**Rationale**: FR-004 asks for Jump in, not Pass. In a One host episode that is not inviting, the
host carries on anyway, so Pass has nothing to do. Legacy One host episodes invite on every line, so
they never reach the hosts' Continue, and the new flag does not change them.

---

## R16. Setup screen: Episode settings, scope marks, guests (Principle IV)

**Decision**:
- **Episode settings** is a disclosure button (`aria-expanded`, `aria-controls`), closed by default.
  Its label holds the one-line summary, for example "Balanced · Medium lines · Asked sometimes".
  Inside are:
  - radio groups for Style, Host lines, How often you're asked and Your role, built like the existing
    `FormatFieldset`;
  - a text field for Today's subject with a 120-character counter.

  In Listen, How often you're asked and Your role are not rendered (FR-011). Start stays the only
  primary button (FR-008, SC-008).
- **Scope**: in a continuing series, the first change to a setting opens `ScopeDialog`, an
  `alertdialog` built like `ConfirmDialog`. It offers **Just this episode** and **This and later
  episodes**; Escape or Cancel reverts the change.
  - The field's legend then carries a `ScopeMark` reading "this episode" or "from now on" (text, not
    colour alone).
  - Changing the same setting again keeps its scope. Setting it back to the series' usual value
    clears its mark.
  - **Use the show's standard settings** is a secondary text button, shown only when the series'
    usual settings differ from standard. It opens `ConfirmDialog` (FR-019).
- **Guests**: `SeriesHostCard` gains **Invite a guest…** beside **Recast…**. `GuestDialog` asks for a
  personality, then shows the cast guest. The card then shows the guest, with a "Guest · this
  episode" badge, **Another guest** and **Remove guest**. The away host is listed as "Away this
  episode".
- **SC-007** is three choices from a One host series' setup:
  1. choose Panel;
  2. choose Just this episode (the expert guest is cast and shown);
  3. Start.

**Rationale**: This follows the patterns 010 established (`ConfirmDialog`, `ThemedSelect`, radio
fieldsets) and the design system's tokens. There are no native selects.

---

## R17. Measuring the model-dependent criteria

**Decision**: The hand-run pattern of 003, 005, 007 and 010: `benchmark`-marked tests, deselected by
default, plus a review sheet, `talk-review-sheet.md`, filled during validation.

| Criterion | Measured by |
|---|---|
| SC-001, SC-002 | `test_host_talk_benchmark.py`: 20 Medium One host Beginner episodes with defaults. It records sentences per discussion line, invitation share, words per sentence (Beginner ≤ 8) and verb tenses, using the existing level benchmark's tense check |
| SC-003 | Scripted learner questions inside the same run. The next host line is reviewed in the sheet |
| SC-004 | 10 Presented and 10 Conversation episodes; intents are counted from storage and spot-checked in the sheet |
| SC-005 | Checked automatically over every benchmark episode, and by the policy property test |
| SC-009 | `test_guest_episode_benchmark.py`: 10 guest episodes plus their following episodes, reviewed in the sheet |
| SC-011 | `test_podcast_latency_benchmark.py` is extended to measure to the first `line_part` audio for Short, Medium and Long lines (p90 ≤ 5 s each) |

SC-006, SC-007, SC-008 and SC-010 are automated: integration tests, E2E, and a frozen
`schema_010.sql` upgrade test. If SC-001 to SC-004 miss on `llama3.1:8b`, configured talk ships
labelled experimental, as in 005 and 010 (spec Assumptions).

---

## R18. Context size with Long lines in Long episodes

**Finding**: A Long episode (40 host lines) of Long lines (about 110 tokens each), plus cues and the
standing prompt, comes to about 6–7k tokens. Ollama's default context may be smaller, and the app
sets no `num_ctx`. 007 R14 already lists this as an open item for Long episodes.

**Decision**:
- No `num_ctx` change in this feature. The latency benchmark already records `prompt_eval_count`. It
  is extended to record it at the end of a Long · Long-lines episode.
- If the count shows truncation (the count stops growing), the plan's Polish phase records it in
  `docs/architecture.md` § "Open items" with the configurable `num_ctx` option.

**Rationale**: It is a provider-configuration change (004's domain), with memory costs on the
learner's GPU. It should be decided on a measurement, not a guess.

---

## Per-language data

No new per-language value (FR-027):
- sentence splitting, question detection and casting use only the existing data;
- guest names come from the existing name banks;
- no `Requirement` is added in `backend/language_kit/registry.py`, and no `kit.sh backfill` is run.
