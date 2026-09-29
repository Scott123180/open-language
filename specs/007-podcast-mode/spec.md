# Feature Specification: Podcast Mode

**Feature Branch**: `007-podcast-mode`
**Created**: 2026-09-28
**Status**: Draft
**Input**: User description: "I want a feature for a podcast. A podcast is very similar to the original premise of roleplaying, especially if you're just with someone else. One case is the base where it's you and someone else. Another case is you're not actually talking and you're just listening and maybe clicking advance to continue the podcast. And then you might be in a podcast with multiple people. So there should be some configurability to this. Each person gets a persona when the podcast is picked. The learner can select from a few scenarios that you create, but we should also have a generator, and a random suggestion for a podcast. And a mix of personalities as well, because this is meant to be engaging, and topics relevant to whoever is using the program will be engaging. It should still adhere to the configured speech levels. The podcast is turn-based, because it's a conversation but not totally a conversation: it should get back to the learner's turn and the learner shouldn't be neglected, but it might not be exactly round-robin. With the speakers we'd want different voices, which might involve downloading more voices, and making names for people. We'll start with up to three people: two other speakers and the learner. In the future we might add more, but to keep things simple."

## Clarifications

### Session 2026-09-28

- Q: Where do the learner's interests, used to personalise suggestions and generated shows, come
  from? → A: The learner types a few interests on the Podcasts screen and the app remembers them.
  They are not inferred from conversations or saved words (FR-023, Key Entities updated).
- Q: The learner also asked for "a current conversation summary for the learner, based on the
  conversation, a simple summary toggleable to the conversation language or the learner's language
  (English)". Does it belong to this feature, and where does it apply? → A: In this feature,
  for both podcast episodes and roleplay conversations (User Story 6, FR-035–FR-042, SC-012–SC-014;
  FR-034 amended).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner joins a podcast as a guest of one host (Priority: P1)

The learner opens **Podcasts** from the home screen and sees a short list of ready-made shows, for
example *Weekend Food Talk* or *Tech for Normal People*. Each show card gives the topic, the host's
name and personality in one line, and the learner's role (guest, co-host or caller). They pick
*Weekend Food Talk*. The host, **Lucía**, an upbeat food lover, introduces the episode and the
learner in the practice language, then asks the learner a first question. The learner answers by
speaking or typing, and Lucía reacts, adds her own story and asks a follow-up. It feels like being on
a show rather than completing a transaction: the host drives the topic, has opinions, and keeps the
episode moving. The host's lines are read aloud in the host's own voice, and every learning tool the
learner already knows (translation, word lookup, saving words, suggestions, corrections) works on the
episode as it does in a roleplay conversation.

**Why this priority**: This is the base case the learner described, and the smallest slice that
delivers the podcast experience: a ready-made show, a host with a persona, a topic-led conversation
and a spoken host. Every other story adds speakers, sources of shows, or a listening mode on top of
it.

**Independent Test**: Pick any ready-made show in the one-host format, exchange five turns (typed and
spoken), and use each learning tool once. The host stays in persona, keeps the episode on the show's
topic, speaks in the practice language at the learner's level, and every line is played in the
host's voice.

**Acceptance Scenarios**:

1. **Given** the Podcasts screen, **When** the learner opens it, **Then** it lists at least six
   ready-made shows, each with a title, a one-line topic, its host(s) and the learner's role.
2. **Given** the learner starts a one-host show, **When** the episode opens, **Then** the host
   introduces the show, themselves and the learner, and ends the opening with a question to the
   learner, all in the practice language.
3. **Given** an episode in progress, **When** the learner replies, **Then** the host's next line
   responds to what the learner said, stays in the host's persona and keeps to the show's topic.
4. **Given** a conversation level below Natural, **When** the host speaks, **Then** the host's lines
   follow that level's limits, as the roleplay partner's replies do.
5. **Given** an episode in progress, **When** the learner uses translation, word lookup, save word,
   suggestions or the expression helper, **Then** each works as it does in a roleplay conversation,
   and corrections follow the learner's correction mode.
6. **Given** an episode the learner left part-way, **When** they open it from Past Chats, **Then** it
   is labelled as a podcast with its show title and hosts, and they can continue it where they left
   off with the same hosts and voices.
7. **Given** an episode in progress, **When** the learner chooses **End episode**, **Then** the host
   gives a short sign-off in character and the episode is marked finished.

---

### User Story 2 - Learner listens to two hosts and advances at their own pace (Priority: P1)

Some days the learner does not want to speak; they want comprehensible listening. They choose a show
and the **Listen** format. Two hosts, **Lucía** and **Marco**, talk to each other about the topic,
each with a different personality and a clearly different voice. After each line the episode pauses,
and the learner presses **Continue** when they are ready for the next one. They can replay a line,
translate it, look up or save a word, and then continue. The episode runs through an introduction, a
discussion with a few turns of back-and-forth, and a sign-off.

**Why this priority**: Listen-only episodes are the other half of what the learner described, and the
first place two speakers, two personas and two voices appear. It needs no speech from the learner, so
it serves a different kind of practice than Story 1. It is independent of Story 1 apart from the
shared show list.

**Independent Test**: Start any ready-made show in the Listen format and press Continue until the
sign-off. The two hosts alternate in a natural, not strictly alternating, way; each line is played in
its speaker's voice; the two voices are different; and the episode never waits for input from the
learner other than Continue.

**Acceptance Scenarios**:

1. **Given** a Listen episode, **When** a host line is shown, **Then** it is labelled with the
   speaker's name, played in that speaker's voice, and the next line does not begin until the learner
   presses Continue.
2. **Given** a Listen episode, **When** the learner presses Continue, **Then** the next line is spoken
   by whichever host would naturally speak next. A host may speak twice in a row, but neither host
   speaks more than three lines in a row.
3. **Given** a Listen episode, **When** the hosts talk, **Then** they respond to each other (agree,
   disagree, ask, joke) in line with their personalities, rather than taking turns delivering
   unconnected statements.
4. **Given** a Listen episode, **When** the learner selects a host line, **Then** they can replay it,
   translate it, look up and save its words, just as with a partner message in a roleplay.
5. **Given** a Listen episode, **When** the episode reaches its planned length, **Then** the hosts
   wrap up with a sign-off and the episode is marked finished. The learner can also end it at any
   time.

---

### User Story 3 - Learner joins a panel with two hosts (Priority: P2)

The learner picks a show in the **Panel** format: two hosts plus the learner, three people in all.
The hosts sometimes talk to each other for a line or two, sometimes one asks the learner directly,
and sometimes the learner is invited to settle a disagreement between them. The learner is never
left out for long: within a few host lines, someone always brings the conversation back to them with
a question or an invitation. When the learner addresses a host by name, that host answers.

**Why this priority**: The three-person format is the richest version of the feature and the one the
learner said to build up to, but it depends on the turn-taking of Story 1 and the two-speaker
handling of Story 2.

**Independent Test**: Run a Panel episode for ten learner turns. After each learner turn, count host
lines until the learner is invited to speak again. The learner is always invited within four host
lines, both hosts take part, and a learner message addressed to one host by name is answered by that
host.

**Acceptance Scenarios**:

1. **Given** a Panel episode, **When** it is not the learner's turn, **Then** the next host line is
   played, and the learner presses Continue to hear the one after it, as in Listen.
2. **Given** a Panel episode, **When** the hosts have spoken four lines in a row since the learner
   last spoke, **Then** the fourth line at the latest ends by inviting the learner to speak.
3. **Given** a Panel episode, **When** the learner is invited to speak, **Then** the invitation is
   clearly addressed to the learner, and the screen shows it is the learner's turn.
4. **Given** it is not the learner's turn, **When** the learner chooses **Jump in**, **Then** they
   can speak straight away, and the hosts respond to what they said.
5. **Given** it is the learner's turn, **When** the learner chooses **Pass**, **Then** the hosts
   carry on without them and invite them again later.
6. **Given** the learner addresses one host by name, **When** the hosts respond, **Then** that host
   speaks first.
7. **Given** a ten-turn Panel episode, **When** it is reviewed, **Then** each host has spoken at least
   a quarter of the host lines.

---

### User Story 4 - Learner creates a podcast from an idea or asks for a surprise (Priority: P2)

None of the ready-made shows appeals today. The learner types an idea, such as *"football
tactics"* or *"living abroad as a nurse"*, into the podcast generator and picks a format. The app
creates a show: a title, a one-line premise, the learner's role, and hosts with names, personalities
and voices. The learner can start it, or ask for another version. On another day the learner presses
**Surprise me** and gets a random show suggestion they would not have thought of, leaning towards
topics they care about. Either way they see the show before it starts.

**Why this priority**: The ready-made shows make the feature usable on day one; generation and random
suggestions are what keep it engaging over weeks. They depend on the show and host concepts that
Stories 1–3 establish.

**Independent Test**: Enter ten different ideas and press Surprise me ten times. Each produces a
complete, playable show that matches the idea (or, for Surprise me, varies between presses), with
distinct hosts whose names suit the practice language.

**Acceptance Scenarios**:

1. **Given** the learner enters an idea and a format, **When** they generate, **Then** they get a
   show with a title, a one-line premise, the learner's role, and the right number of hosts for the
   format, each with a name, a personality and a voice.
2. **Given** a generated show, **When** the learner asks for another version, **Then** a new show on
   the same idea is produced, and the previous one is discarded unless they started it.
3. **Given** the learner presses Surprise me, **When** the suggestion appears, **Then** it is a
   complete show they can start or reject, and repeated presses give varied topics.
4. **Given** the learner has told the app their interests, **When** they press Surprise me, **Then**
   suggestions draw on those interests more often than not.
5. **Given** the learner enters an empty idea, or one that cannot become a show, **When** they
   generate, **Then** they are told in plain language what to change, and offered Surprise me.

---

### User Story 5 - Learner shapes the hosts before starting (Priority: P3)

Before an episode starts, the setup shows the hosts. The learner can shuffle for a new host, change a
host's personality from a list (for example *enthusiast*, *dry sceptic*, *storyteller*, *curious
interviewer*, *expert*, *joker*), or hear a sample line in the host's voice. The app keeps the mix
varied: two hosts on the same show never share a name, a voice or a personality.

**Why this priority**: The generated and ready-made personas are enough for Stories 1–4. Letting the
learner tune the mix is a refinement that makes favourite combinations possible.

**Independent Test**: On the setup of a two-host show, shuffle each host three times and change one
host's personality. The two hosts always differ in name, voice and personality, and the episode uses
the final choices.

**Acceptance Scenarios**:

1. **Given** the setup of any show, **When** the learner views the hosts, **Then** each host shows a
   name, a personality and a voice sample.
2. **Given** a two-host show, **When** the learner shuffles or changes a host, **Then** the two hosts
   still have different names, voices and personalities.
3. **Given** the learner changes a host's personality, **When** the episode runs, **Then** that host
   speaks in line with the new personality.

---

### User Story 6 - Learner catches up with a summary of the conversation so far (Priority: P2)

Ten minutes into a Panel episode, the learner has lost the thread: the hosts have moved from
Barcelona's markets to a disagreement about tapas prices, and the learner isn't sure what they
missed. They open **Summary** and read a few short lines: what the conversation has covered, what
each speaker thinks, and where it stands now. The summary is in German, the episode's language, in
simple sentences they can follow. One line still puzzles them, so they switch the summary to
**English**, check it, and switch back. They close the summary and carry on. The same Summary is
available in an ordinary roleplay conversation, for example to recall what was ordered so far in
*Order at a Restaurant*.

**Why this priority**: Long episodes, and above all Listen and Panel episodes with two fast hosts, are
where learners lose the thread. A summary lets them recover without leaving the practice language
for long. It is useful in roleplay too, and it relies on nothing but the conversation's own lines,
so it can be built alongside Story 1.

**Independent Test**: In a roleplay conversation and in a Panel episode, each with at least eight
lines, open Summary. It covers the main points of the lines so far and nothing that was not said. It
is short and simple in the conversation's language, and switching to English shows the same points
in English. Add two more lines and open Summary again: it now includes them.

**Acceptance Scenarios**:

1. **Given** a roleplay conversation or a podcast episode with at least one learner or host reply
   after the opening, **When** the learner opens Summary, **Then** they see a short summary of the
   conversation so far, based only on what was said in it.
2. **Given** the summary is shown, **When** the learner looks at it, **Then** it is in the
   conversation's language by default, in short, simple sentences that follow the learner's
   conversation level.
3. **Given** the summary is shown, **When** the learner switches it to English, **Then** the same
   points appear in English, and switching back shows the conversation-language version again.
4. **Given** the learner switched the summary to English, **When** they next open Summary in any
   conversation, **Then** it opens in English until they switch it back.
5. **Given** a podcast episode with two hosts, **When** the learner reads the summary, **Then** it
   says which host holds which view or told which story, by name.
6. **Given** the learner opened Summary earlier, **When** new lines have been added since and they
   open it again, **Then** the summary covers the new lines as well.
7. **Given** the summary is open, **When** the learner closes it, **Then** the conversation is exactly
   where they left it: no line was added, skipped or advanced, and it is still the same speaker's
   turn.

---

### Edge Cases

- **Fewer than two voices for the practice language**: one-host shows work normally. For two-host
  shows the learner is told, before starting, that both hosts will share one voice and how to add
  another; the episode can still run, with every line labelled by speaker. The app never uses a voice
  for another language.
- **A host's voice is missing when an episode is resumed**: the episode continues as text, with a
  plain message saying that voice is unavailable and what to do. It does not switch that host to a
  different voice silently.
- **The model writes another speaker's lines**: a host line must contain only that host's speech. It
  must not include the other host's reply or put words in the learner's mouth; if it does, the extra
  speech is not shown or played as that host's line.
- **Learner writes in English**: the host who replies answers in the practice language and invites
  the learner, in character, to use it.
- **Level changed mid-episode**: the next host line follows the new level; the episode, its hosts and
  history are unchanged.
- **Practice language changed mid-episode**: the episode keeps its own language, hosts and voices, as
  conversations do.
- **Provider fails mid-episode**: the learner sees a plain message with what to do and can retry the
  same line. The episode history is kept, and the app does not switch provider.
- **Learner stays silent at their turn in One-host or Panel**: nothing happens until they reply, Pass
  (Panel) or end the episode. The hosts never talk over a pending learner turn.
- **Learner jumps in during the Listen format**: Listen has no Jump in. The learner can end the
  episode and start the same show in a speaking format.
- **Very long episode**: after the planned length the hosts wrap up. In speaking formats the learner
  can keep talking after the wrap-up has been offered, and the episode ends when they choose End
  episode.
- **Generator idea is unsuitable**: an idea that asks for hateful, sexual or dangerous content is
  declined with a plain message and the offer of Surprise me.
- **Summary too early**: before anyone has replied to the opening line, Summary says in plain
  language that there is nothing to summarise yet.
- **Summary of a very long conversation**: the summary stays short. It gives the main points and where
  the conversation stands now, not a line-by-line account.
- **Summary while a line is being produced**: the summary covers the lines finished so far. Opening it
  does not interrupt or cancel the line in progress.
- **Summary and the practice language setting**: the summary uses the conversation's own language, not
  the practice language currently selected in Settings.
- **Summary in a finished or resumed conversation**: Summary works on conversations opened from Past
  Chats, finished or not, the same way.
- **Summary fails**: the learner sees a plain message with what to do and can try again. The
  conversation itself is unaffected, and the app does not switch provider.
- **Host names**: names suit the episode's language (Spanish names for a Spanish episode, German names
  for a German one) and never match the learner's own name.

## Requirements *(mandatory)*

### Functional Requirements

**Shows and formats**

- **FR-001**: The system MUST provide a Podcasts area, reachable from the home screen, as a new
  practice activity next to roleplay conversations.
- **FR-002**: The system MUST include at least six ready-made shows covering varied everyday topics
  (for example food, travel, sport, technology, film and music, work life). Each show has a title, a
  one-line premise, the learner's role and default hosts.
- **FR-003**: The system MUST offer three formats: **One host** (the learner and one host), **Panel**
  (the learner and two hosts) and **Listen** (two hosts; the learner only listens). Every show MUST be
  playable in every format.
- **FR-004**: The number of people in an episode MUST NOT exceed three, the learner included. The set
  of formats MUST be defined in one place, so a larger panel can be added later without changing the
  features that use it.
- **FR-005**: The learner MUST see the show, the format, the hosts and their own role before an
  episode starts, and start it with a single primary action.

**Hosts and personas**

- **FR-006**: Every host MUST have a name, a personality drawn from a catalogue of at least eight
  personalities, a speaking style consistent with that personality, and a voice.
- **FR-007**: Two hosts in one episode MUST have different names, different personalities and, when
  the practice language has at least two voices, different voices.
- **FR-008**: Host names MUST suit the episode's language.
- **FR-009**: A host MUST keep the same name, personality and voice for the whole episode, including
  after the episode is resumed.
- **FR-010**: Learners MUST be able to shuffle a host, change a host's personality, and hear a
  sample of a host's voice before starting (Story 5).
- **FR-011**: The learner MAY give the name the hosts should call them. If they give none, the hosts
  address them without a name (for example as "our guest").

**Turn-taking**

- **FR-012**: Each host line MUST contain the speech of exactly one host.
- **FR-013**: The next speaker MUST be chosen by the flow of the conversation, not strict rotation.
  A host MAY speak twice in a row, and MAY respond to the other host rather than to the learner.
- **FR-014**: In the One-host and Panel formats, the learner MUST be invited to speak at the latest
  by the fourth consecutive host line, and every invitation MUST be clearly addressed to the learner.
- **FR-015**: In the Panel and Listen formats, a host MUST NOT speak more than three lines in a row,
  and over an episode each host MUST speak at least a quarter of the host lines.
- **FR-016**: Host lines MUST NOT advance on their own: after each host line, the next one begins only
  when the learner presses Continue, and at the learner's turn nothing advances until they reply,
  pass or end.
- **FR-017**: In the Panel format, the learner MUST be able to Jump in when it is not their turn and
  to Pass when it is.
- **FR-018**: When the learner addresses a host by name, that host MUST speak next.
- **FR-019**: Every episode MUST have an introduction, a discussion and a sign-off. The hosts MUST
  offer to wrap up after a planned length, and MUST give a sign-off whenever the learner chooses End
  episode.

**Topics, generation and suggestions**

- **FR-020**: Learners MUST be able to generate a show from a short free-text idea and a chosen
  format. The result MUST be a complete show (title, premise, learner's role, hosts) that the learner
  sees before starting.
- **FR-021**: Learners MUST be able to ask for another version of a generated show.
- **FR-022**: Learners MUST be able to request a random show suggestion (Surprise me). Repeated
  requests MUST give varied topics.
- **FR-023**: Learners MUST be able to enter a short list of interests (for example "football,
  cooking, nursing") on the Podcasts screen, and to edit or clear it at any time. The list MUST be
  saved and kept between sessions. When it is not empty, Surprise me MUST draw on it more often than
  not, and the generator MUST use it to shape the hosts' angle on the learner's idea. Interests are
  never inferred from the learner's conversations or saved words.
- **FR-024**: The generator MUST decline unsuitable ideas (hateful, sexual or dangerous content)
  with a plain message instead of producing a show, and offer Surprise me.

**Language, level and learning tools**

- **FR-025**: An episode MUST use the practice language selected when it starts, and keep it for its
  whole life. Host lines MUST be entirely in that language; explanations stay in English.
- **FR-026**: Host lines MUST follow the learner's conversation level, as the roleplay partner's
  replies do, and a level change MUST apply from the next host line.
- **FR-027**: Every learning tool available on a roleplay conversation MUST be available on an
  episode: translation, alternative phrasing, word lookup, saving words, reply suggestions, the
  expression helper and corrections. Suggestions and the expression helper appear only at the
  learner's turn.
- **FR-028**: Words saved from an episode MUST be saved in the episode's language, as they are from a
  conversation.

**Voices and speech**

- **FR-029**: Each host line MUST be spoken in that host's voice. Learner speech MUST be transcribed
  in the episode's language.
- **FR-030**: At least two distinct voices MUST be available for every practice language, set up
  locally and usable without an internet connection.
- **FR-031**: If a host's voice is not usable, the system MUST tell the learner in plain language and
  MUST NOT use a voice for another language or silently give the host a different voice.

**History and providers**

- **FR-032**: Episodes MUST be saved as they happen and appear in Past Chats, marked as podcasts with
  their show title, format, hosts and language. They MUST be resumable with their hosts and voices
  intact.
- **FR-033**: Episodes MUST work with every language-model provider the learner can select today,
  and MUST follow the existing rules for provider errors: a plain message, a retry, and no silent
  fallback.
- **FR-034**: Adding this feature MUST NOT change existing conversations, vocabulary, decks, settings
  or the roleplay experience, apart from adding Summary to roleplay conversations (FR-035).

**Conversation summary**

- **FR-035**: Learners MUST be able to open a summary of the current conversation from the
  conversation screen, in roleplay conversations and in podcast episodes of every format. Summary
  MUST be a secondary action that does not compete with the screen's primary action.
- **FR-036**: The summary MUST be based only on the conversation's lines up to the moment it is
  opened. It MUST NOT state anything that was not said in the conversation.
- **FR-037**: The summary MUST be short (at most five sentences or bullet points) and cover what has
  been discussed, the speakers' main points, and where the conversation stands now. In a podcast
  episode it MUST name the host behind each point.
- **FR-038**: The summary MUST be available in the conversation's language and in English, with a
  single control to switch between them. Both versions MUST describe the same points.
- **FR-039**: The conversation-language version MUST use short, simple sentences that follow the
  learner's conversation level. At Natural it is still plain and short.
- **FR-040**: The summary MUST open in the conversation's language by default. The learner's last
  choice of summary language MUST be remembered across conversations and sessions.
- **FR-041**: Opening, switching or closing the summary MUST NOT add, skip or advance any line, or
  change whose turn it is.
- **FR-042**: When lines have been added since the summary was last shown, opening it again MUST give
  a summary that includes them.

### Key Entities *(include if feature involves data)*

- **Show**: a podcast concept: title, one-line premise, topic, the learner's role (guest, co-host or
  caller) and default hosts. Either ready-made or generated. Generated shows that are never started
  are not kept.
- **Format**: One host, Panel or Listen. It fixes how many hosts there are and whether the learner
  speaks.
- **Personality**: an entry in a fixed catalogue (for example enthusiast, dry sceptic, storyteller),
  with a short description of how a host with it speaks and reacts.
- **Host**: a persona in one episode: name, personality, voice and the show role it plays (host,
  co-host or guest expert).
- **Episode**: one run of a show in one format. It is a kind of conversation: it has a language, a
  status (in progress or finished), its hosts, and its lines. It appears in Past Chats.
- **Episode line**: one turn, spoken by exactly one participant (a named host or the learner), in
  order.
- **Learner interests**: a short, learner-entered list of topics, saved with the learner's
  settings, that personalises Surprise me and the generator (FR-023).
- **Conversation summary**: a short account of one conversation or episode up to a given line, in
  the conversation's language and in English. It always reflects the lines at the time it is shown.
- **Summary language choice**: the learner's last choice between the conversation's language and
  English, saved with the learner's settings (FR-040).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From the home screen, a learner can start a ready-made show in under 30 seconds, and a
  Surprise me show in under 60 seconds.
- **SC-002**: Across 10 Panel episodes of 10 learner turns each, the learner is invited to speak
  within four host lines 100% of the time, and each host speaks at least 25% of the host lines in
  every episode.
- **SC-003**: Across 10 Listen and 10 Panel episodes, 0 host lines contain another speaker's speech or
  speak for the learner.
- **SC-004**: In a blind review of 10 two-host episodes, a reviewer can tell which host said a given
  line from its content and voice alone (without the name label) for at least 80% of lines.
- **SC-005**: At least 95% of host lines are entirely in the episode's language, across both practice
  languages.
- **SC-006**: At each level below Natural, host lines meet the level's limits at least as often as
  roleplay partner replies do at the same level with the same provider and model.
- **SC-007**: Of 20 generated shows from 20 different ideas, at least 18 are on the given idea and
  playable end to end, with distinct, language-appropriate host names.
- **SC-008**: 20 consecutive Surprise me presses give at least 15 different topics.
- **SC-009**: After pressing Continue, the next host line starts playing within 5 seconds in 90% of
  cases with the default local setup.
- **SC-010**: With the network disconnected and the local defaults selected, a Panel episode with
  spoken input and two spoken hosts completes normally.
- **SC-011**: After updating, 100% of existing conversations, words, decks and settings are present
  and unchanged, and a roleplay conversation behaves as before apart from the new Summary.
- **SC-012**: In a review of 20 summaries (10 roleplay conversations, 10 podcast episodes, both
  practice languages), 0 summaries state something that was not said, and at least 90% cover every
  main point a reviewer lists for the conversation.
- **SC-013**: For the same 20 summaries, the English and conversation-language versions describe the
  same points in 100% of cases, and at levels below Natural the conversation-language version meets
  the level's limits at least as often as roleplay partner replies do.
- **SC-014**: A summary appears within 10 seconds of opening Summary, and switching its language
  takes under 10 seconds, in 90% of cases with the default local setup.

## Assumptions

- **Formats are fixed at the start.** An episode's format cannot change mid-episode; a learner who
  wants to speak in a Listen episode starts the show again in a speaking format.
- **Manual pacing only.** Every host line waits for Continue. Automatic, hands-free playback is out
  of scope for this feature.
- **Host voices are separate from the Settings voice.** The voice chosen in Settings remains the
  roleplay partner's voice. Hosts are given voices from the installed voices for the episode's
  language.
- **Ready-made shows are shared across languages.** Like roleplay scenarios, they are not tied to a
  country; the hosts set them in a context that fits the episode's language, with suitable names.
- **Generated shows are not kept as templates.** A generated show lives on only through the episodes
  started from it. Saving favourite shows for new episodes is out of scope.
- **More voices are a one-time setup step.** The additional voices each language needs are fetched
  during setup, like the existing voices, and used offline afterwards.
- **Quality limits carry over.** Levels and corrections are experimental on the default local model;
  their existing warnings apply to podcasts too. Multi-speaker turn-taking may also be harder for a
  small local model than for a larger one, which SC-002 and SC-003 are meant to measure.
- **Summary is read, not heard.** The summary is shown as text only; reading it aloud, and word
  lookup or saving words from it, are out of scope for this feature.
- **English is the only native language.** "The learner's language" for the summary is English, as
  everywhere else in the app.
- **Larger panels** (more than two hosts) are out of scope, but FR-004 should make them a catalogue
  change.
