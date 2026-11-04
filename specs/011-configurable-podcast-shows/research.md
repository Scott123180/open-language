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
| `ask(run, format, rng)` | The `Ask` level of the host line at position `run` since the learner spoke: `required`, `allowed` or `none` (R3, R19) |
| `invitation(ask, addressee)` | Whether the written line invites the learner (R19) |
| `discussion_intent(state, rng)` | Which kind a discussion line is (R4, R21) |
| `line_rules(label, languages)` | The standing prompt's line rules |
| `speech_rules(prompt, level)` | The level block (R2) |
| `speaking_style(personality)` | The personality's speaking style in the hosts section (R22) |
| `instruction(cue, cast, label)` | A cue's instruction for the line kinds it knows |
| `closing(cue, label)` | The cue's last sentence, from its `Ask` (R5) |
| `replayed_line(text, addressee, cast, label)` | A stored host line as the history replays it (R19) |

*Amended 2026-11-03*: `invites` became `ask` plus `invitation`, and `speaking_style` and
`replayed_line` were added. `LegacyTalk` returns `required` or `none` from today's rules, makes
`invitation` true exactly for `required`, keeps every speaking style, and replays text unchanged, so
legacy prompts, cues and histories stay byte for byte.

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

*Amended 2026-11-03*: the cue phrase now depends on the line's kind; R22 replaces this column with a
brief and a full phrase inside the same range.

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
the chance that the 1st, 2nd and 3rd host line since the learner last spoke or passed is *allowed*
to invite them. The 4th line is *required* to (FR-003, 007 FR-014).

*Amended 2026-11-03 (R19)*: the draw now gives each cue an `Ask` level (`required`, `allowed` or
`none`) instead of a yes/no. Whether the stored line invites is decided after it is written, from who
it is for. The hazards below give the share of `allowed`-or-`required` cues; the measured invitation
share is checked by SC-001 in the benchmark, not by the property test.

| Setting | Hazards (1st, 2nd, 3rd) | Expected share of host lines that invite |
|---|---|---|
| `often` | 1.0 | 1 in 1 (today's One host) |
| `sometimes` (default) | 0.35, 0.45, 0.55 | about 1 in 2.2 (0.46) |
| `rarely` | 0.0, 0.05, 0.10 | about 1 in 3.8 (0.26) |

The following stay as they are:
- the wrap-up line is `required` in a speaking format, so the learner gets the last word on the
  topic (R21 changes what it asks);
- the sign-off is `none`;
- Panel's balance rule (`_gap_after`) still applies.

**Rationale**:
- SC-001 caps inviting lines at 50% with the defaults. `sometimes` sits at 46% before wrap-up, which
  leaves headroom.
- A hazard per position keeps the deadline exact. Expected rates are checked by a seeded property
  test over 10,000 simulated runs: `sometimes` in [0.40, 0.50], `rarely` in [0.22, 0.30], and never
  five host lines in a row.
- Today's Panel schedule (0.25, 0.45, 0.60) averages about 1 in 2.3, so Sometimes keeps Panel's feel.

**Spec reading**: FR-003 says Often means every host line in both formats, and the plan follows it.
FR-026's "Conversation · Short · Often reproduces today's quick back-and-forth" is then exact for One host's line length and invitations. In
Panel, today's behaviour is closest to Sometimes (plan, Spec interpretations).

**Alternatives considered**:
- *A fixed every-Nth-line rhythm*: rejected. It is predictable and robotic.
- *Letting the model decide when to ask*: rejected. This is the behaviour the learner complained
  about, and 007 R2 already moved the decision to the policy. R19 keeps the policy's allowance and
  deadline, and only lets the model decide *whether it fits* on an `allowed` line.

---

## R4. Line kinds: the policy picks react, explain, story, answer or follow-up

**Decision**: In a configured episode, a discussion line's `intent` is one of five new values. All
fit `podcast_host_lines.intent String(10)`, and legacy episodes keep `discuss`.

| Intent | When | Asked for |
|---|---|---|
| `answer` | The learner's last line asks a question (it contains `?`), **or** the last host line is a question for the other host (its addressee is that host, R19) | Answer {asker}'s question first and clearly, step by step, never with only a question; if two were asked, answer one and say the other is coming. In Panel, after a learner question that names neither host or both: "If it is for both of you, answer for yourself, then ask {other} for theirs." |
| `follow_up` | The learner's last line had two or more `?`, and the one host line since was `answer` | Answer the other question from before |
| `react` | Drawn by Style weight | React to the last line and add something of your own |
| `explain` | Drawn by Style weight | Explain one thing about the subject step by step: what it is, how it works, and an everyday example |
| `story` | Drawn by Style weight | Tell a short story or example from your own life |

*Amended 2026-11-03*: `answer` also follows a host's question to the other host, and `explain` and
`answer` ask for a step-by-step explanation (FR-005, FR-006a). The line's length comes from its kind
(R22). After a wrap-up, R21's rules take over from the Style draw.

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
   - "Only ask {label} something when the producer note says so." is added;
   - "A closing question to {label} comes after the line's sentences and is not one of them." is
     added (FR-002);
   - "Never ask {label} something they have already answered in this episode." is added (FR-003a);
   - "Every episode is about one subject, named in the opening. Stay on it until the wrap-up." is
     added (FR-007a, R20);
   - the addressing rule of R19 is added, last.
7. The level sentence rules (R2), last.

Each cue is: the producer marker, then `Next: {name}.`, then the intent's instruction with the
Host-lines phrase (R22), then the after-pass sentence, then a closing from the cue's `Ask` (R19):
- `required`: `Then end by asking {label} one question.` (or `to settle it`, as today; the wrap-up
  has its own, R21);
- `allowed`: `If it fits, then end by asking {label} one question; if not, ask {label} nothing.`;
- `none`: **`Don't ask {label} anything this time.`**

*Amended 2026-11-03*: three closings instead of two, and the new line rules above.

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

`{speaking_style}` is the configured style of R22, so a One host interviewer covering the expert
explains step by step too.

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

## R19. Who a line is for: a hidden address tag, read after the line is written

*Added 2026-11-03, from episode 45 (spec Overview, item 4).*

**Problem**: 007 R2 decides whether a line invites the learner before it is written, and stores
that decision as the line's `invites_learner`. Its rationale said the screen should never depend on
"parsing the model's text for a question mark". Episode 45 shows the cost: Claude Sonnet asked the
learner something on 6 of 13 non-inviting lines (messages 384, 395, 399, 402, 407, 409), the screen
offered Continue, and three of those questions were never answered. A host's question to the other
host was routed only when the name happened to appear (`_handed_over_host`). This decision reverses
that part of 007 R2 for configured episodes; legacy episodes keep it (FR-025).

**Decision**: code sets the limits, the content picks within them, and chance breaks ties.

1. **The cue carries an `Ask` level, not a yes/no** (R3, R5). `required` on the deadline line, the
   wrap-up and every line under Often; `allowed` when the hazard draw hits; `none` otherwise. The
   sign-off and every Listen line are `none`. The `Ask` is stored with the line (`podcast_host_lines.ask`),
   so the cue is rebuilt byte for byte (007 R3).
2. **Every configured host line ends with an address tag.** The standing prompt's last line rule:
   "End every line with who it is for, in square brackets: [@{learner}], [@{other host}], or [@all]
   when it is for no one in particular. The brackets are never read aloud." In One host the choices
   are the learner or all. `{learner}` is the learner label, so an unnamed learner is "[@our
   guest]".
3. **`LineAddress`** (`app/podcasts/services/line_address.py`, pure) reads the tag. It takes the cast
   and the learner label and returns an `Addressee`: `learner`, `lead`, `second`, or `None` (no one
   in particular).
   - The tag is `\[@\s*([^\]\n]{1,60})\]`. The last tag in the text wins, names are folded
     (case and accents, as `_fold`). `[@all]` is valid and gives `None`. A tag naming no
     participant, or the speaker themselves, is not valid, so the fallback decides. In Listen,
     anything for the learner gives `None`, because listeners never speak.
   - **Fallback when there is no valid tag**, in order:
     - the text ends with `?` (ignoring closing quotes and spaces) and names a participant → the
       *last* participant named. The learner counts as named by their name or by one of the existing
       `guest_labels_for(language)` labels, so no new per-language data is needed;
     - the text names the other host anywhere → that host (today's hand-over, first named);
     - otherwise `None`.
   - Every tag is removed from the text. The stage-direction rule already strips `[...]`, but the tag
     must be read before that strip runs.
   - The result records whether the tag or the fallback decided, for the benchmark (SC-012).
4. **Invitation from the written line.** `talk.invitation(ask, addressee)`: `ConfiguredTalk` gives
   `ask == required or addressee == learner`; `LegacyTalk` gives `ask == required`. That value is
   stored as `invites_learner`, so `TurnPolicy.turn`, the frontend and the stored facts stay as they
   are. A question to the learner on a `none` line still hands them the turn (FR-003a). A `required`
   line hands it to them even if the model forgot to ask (SC-005 stays exact).
   - Exceptions: in a two-host format, the `open` and `greet` lines never invite. The second host's
     greeting must come next, and the open and greet cues say "Don't ask".
5. **Next speaker from the addressee.** In configured episodes a new speaker rule sits above balance:
   run cap > addressed host (learner line names a host, 007 FR-018) > **addressee of the last host
   line** > balance > hand-over > preferred slot > random. The addressee is always the other host
   (a host does not address itself), so the run cap cannot conflict. Legacy lines have no addressee,
   so the rule never fires for them and legacy speaker choice is unchanged.
6. **`answer` after a host's question** (R4): when the last line is a host line whose addressee is
   the other host and whose text ends with `?`, the next discussion intent is `answer`. The addressed
   host speaks it by rule 5.
7. **Streaming** (R13): `SentenceSplitter` keeps the tag with the last sentence, because `[` is not a
   sentence start. `StreamingSanitiser` extracts the tag through `LineAddress` before stripping stage
   directions. A sentence that is only a tag, which happens after a newline, gives no part. The tag
   never reaches a `line_part`, the stored content, speech, the summary or the series memory.
8. **History replay**: `talk.replayed_line(text, addressee, cast, label)` re-appends the canonical tag
   (`[@Name]` or `[@all]`) to each configured assistant turn, so a rebuilt session keeps seeing the
   pattern it must follow. It is derived from stored facts, so it is byte-stable. A live session keeps
   the model's raw output. The two differ only when the model wrote the tag in another spelling or
   left it out. The meaning is the same, so stripping a tag is **not** a trim (`was_trimmed` stays
   false) and does not end the session.

**Rationale**:
- The decision comes from content wherever content gives a signal, with no extra model call (SC-011)
  and no change to the streaming path's latency: the tag arrives with the last sentence, which is
  already held until flush.
- Every guarantee stays in code: the deadline, the run cap, balance, the sign-off, and Listen never
  inviting. Property tests can still prove them by feeding chosen addressees.
- On episode 45's 22 host lines, the fallback alone gives the right addressee for every line that
  asks someone something:
  - the six stranded questions, the five invitations and the opening question go to the learner;
  - 387, 392 and 403 go to Julia;
  - the rhetorical 386 goes to no one.

  Statements go to the other host only when they name them (382, 404), as today's hand-over does.
  `test_line_address.py` pins all 22 lines as a table.

**Alternatives considered**:
- *An LLM "director" call per turn*: rejected. A full round trip before every line breaks SC-011,
  especially through `claude -p`, and `llama3.1:8b` cannot be trusted with the turn limits anyway.
- *A JSON reply `{line, addressee}`*: rejected. It rules out sentence streaming (R13) and the
  session (007 R3).
- *Only the fallback*: rejected. It misses questions that don't end the line or name nobody ("¿Y tú?"
  after naming someone in an earlier sentence works, "¿Qué opinas?" alone does not).
- *An arrow or "to:" tag*: rejected. "to:" is English inside a target-language line, and `@` is a
  convention every model knows.
- *Per-language plural words ("ustedes", "ihr") for a question to both hosts*: rejected. It would need
  a new language-kit `Requirement` (FR-027). The `answer` cue asks the first host to pass the question
  on instead (R4), and the tag routes it.

---

## R20. One subject per episode: named in the opening, with suggested subjects

*Added 2026-11-03, from episode 45 (spec Overview, item 5).*

**Decision**:
1. **Opening** (`ConfiguredTalk.instruction` for `open`; FR-007a):
   - with Today's subject: "…introduce the show and yourself, and introduce today's subject.";
   - without: "…introduce the show and yourself, and name today's one subject: one concrete question
     or thing within the show's topic.";
   - in a series episode after the first, without a subject, the opening also says "not in the covered
     list". The series section's rule (010) already says so; the cue repeats it because per-line
     instructions hold better (005 R4).

   The subject is not stored separately. The opening line carries it in the history, and the series
   keeper records it as the episode's topic (010 R6).
2. **Suggest subjects** (FR-010a): `POST /api/podcasts/subject-suggestions` (contracts §8a), one
   structured call through `SubjectSuggester` (`services/subject_suggestions.py`), which takes a
   `StructuredLLMProvider`.
   - The prompt uses the creator intro of 007's generator (subjects in the learner's own language,
     like titles and premises). It gives the show's title, premise and topic, the learner's interests,
     the series' covered topics, the subjects already shown (`avoid`, at most `SUBJECT_AVOID_MAX`),
     007's suitability rule worded for subjects, and "at most 120 characters each".
   - The schema is `{subjects: string[1..3]}`.
   - The server trims each subject, drops any longer than 120 characters, and drops any whose folded
     text equals a covered topic, an avoided subject or an earlier subject in the same reply. It
     returns up to `SUBJECT_SUGGESTIONS` (3).
   - It returns 200 with the list. An empty list means nothing new came back, and the UI says so. A
     provider failure is a 503 with the provider's message (Principle VI).
   - Covered topics are read with `SeriesStorage.remembered(series_id)`, topic points only. There is
     no new storage method.
3. **No shortcut at Start**: a chosen suggestion is checked by `SubjectCheck` (R14) like a typed one,
   because the client can edit it and the server keeps no record of what it suggested.

**Rationale**:
- The opening rule fixes every episode for free. Suggestions are on demand, so the default Start
  still calls no model (010 R6).
- The covered-topic filter only catches exact repeats. Near-duplicates are left to the prompt and
  reviewed (SC-016).

**Alternatives considered**:
- *Code picks from a hand-written sub-subject list per show*: rejected. It does not work for generated
  or suggested shows, and the lists would need writing and translating.
- *Suggest on setup open*: rejected. It would add a model call to every setup.
- *Skipping `SubjectCheck` for an unedited suggestion*: rejected. The server would have to trust the
  client or keep state.

---

## R21. Wrap-up and sign-off: the hosts end the episode

*Added 2026-11-03, from episode 45 (spec Overview, item 6).*

**Decision** (configured episodes; legacy keeps 007's rules):
- **Wrap-up cue**: "Start wrapping up: tell {label} the show is nearly over, and sum up today's
  subject in one sentence." The closing is wrap-up specific: "Then ask {label} for one last thought
  on it." In Listen it is "…tell {label} the show is nearly over…" with the `none` closing.
- **After the wrap-up**, `ConfiguredTalk.discussion_intent` decides before the Style draw:

  | Last line | Next intent |
  |---|---|
  | The learner's, with `?` | `answer`, then `sign_off` at the next Continue |
  | The learner's, without `?` | `sign_off` |
  | The wrap-up, passed | `sign_off` |
  | A host line after the wrap-up (an answer) | `sign_off` |

  Listen keeps 007's rule: the sign-off follows the wrap-up.
- **Sign-off cue**: "React briefly to the last line, then close the show: thank {label} and say
  goodbye." The speaker comes from the existing rules, preferred slot lead, after the addressed-host
  rule.
- **Invitations after the wrap-up**: an `answer` line after the wrap-up is `none`, so a stranded
  question cannot start a new round. R19 rule 4 still gives the learner the turn if the host asks
  anyway. Jump in stays available, and each question gets an `answer` line.
- The sign-off completes the conversation and tells `EpisodeEndings`, as End does (010 R6).

**Rationale**: FR-007b. Nothing waits for an End the learner may not know to press. The learner keeps
control: a question always gets its answer before the goodbye.

**Alternatives considered**:
- *Sign off a fixed number of lines after the wrap-up*: rejected. It ignores what the learner said.
- *Keep 007 and highlight End*: rejected. The learner chose for the hosts to sign off.

---

## R22. Length by line kind, and personalities that explain

*Added 2026-11-03, from episode 45 (spec Overview, item 7).*

**Decision**:
1. **Two cue phrases per Host lines value** (FR-002b), both inside the FR-002 range:

   | `HostLineLength` | `brief_phrase`: greet, react, wrap up, sign off | `full_phrase`: open, explain, story, answer, follow-up |
   |---|---|---|
   | `short` | "in one or two sentences" | "in two sentences" |
   | `medium` | "in three sentences" | "in four or five sentences" |
   | `long` | "in five or six sentences" | "in six to eight sentences" |

   The standing rule keeps the whole range ("Each host line has three to five sentences unless the
   producer note says otherwise"). A closing question is outside the count (R5 line rule).
2. **Configured speaking styles**: `Personality` gains `configured_speaking_style: str | None`, and
   `ConfiguredTalk.speaking_style` uses it when set. `LegacyTalk` keeps `speaking_style`, so the legacy
   goldens hold.

   | Personality | Configured speaking style |
   |---|---|
   | `expert` | "Explains how and why step by step, with simple facts and an everyday example, and stays precise." |
   | `curious_interviewer` | "Asks how and why, picks up details others said, and says what they think too." |

   The other personalities keep their style. A later change is a catalogue edit.
3. **Step-by-step instructions** for `explain` and `answer` (R4 table).

**Rationale**: in episode 45, four rules shortened Julia's answer: the level's two-sentence cap (R2
removes it), "one clear fact or tip at a time", "End by asking Scott a question" on the same line, and
a reacting length for every line. The level still owns each sentence. The example below is five
Beginner sentences of at most eight words in the present tense, and it explains why it takes a while:

> La cafeína es una sustancia del café. Primero, va del estómago a la sangre. Eso tarda unos veinte
> minutos. Después, la sangre la lleva al cerebro. Allí, la cafeína para la señal del sueño.

SC-001's median of at least 3 sentences still holds under Balanced: react lines are 3 at Medium, and
the rest are 4–5. SC-013 adds the median of at least 4 for explaining and answering lines.

**Alternatives considered**:
- *One phrase for every kind*: rejected. Reactions as long as explanations sound padded.
- *Changing `speaking_style` itself*: rejected. It breaks the 007 one-off golden (FR-025).

---

## Per-language data

No new per-language value (FR-027):
- sentence splitting, question detection, address tags (R19: names, `?` and the existing
  `guest_labels_for`) and casting use only the existing data;
- guest names come from the existing name banks;
- no `Requirement` is added in `backend/language_kit/registry.py`, and no `kit.sh backfill` is run.
