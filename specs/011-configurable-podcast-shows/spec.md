# Feature Specification: Configurable Podcast Shows

**Feature Branch**: `011-configurable-podcast-shows`
**Created**: 2026-10-18
**Status**: Draft
**Input**: User description: "make the recommended changes. also make the podcast more configurable.
and if I want to change the series of podcasts, then I could change the settings for the series. for
example, if I wanted to later on change big little questions so that there is an expert, I could do it
for an episode or more."

## Overview

The learner played Big Little Questions in One host at the Beginner level and found it "too
conversational": the host never said more than a few sentences, and every line ended with a yes/no
question. Episode 44 shows why: the learner asked "why does toast land butter-side down?" and the host
kept asking questions back instead of answering ("¿Qué dices? No me respondes."). Three rules, each
reasonable alone, add up to an interview rather than a podcast:

1. **The level caps a host line like a chat reply.** Beginner allows two sentences per reply and one
   easy question; a podcast host is held to the same cap (007 FR-026).
2. **One host invites the learner on every line.** Every line ends "ask our guest a question", so the
   host never talks for long.
3. **Hosts only react.** Each line is asked to "react to the last line"; nothing asks a host to explain
   or tell a story, and in One host the show's second role (Big Little Questions' expert) is dropped,
   so nobody answers the show's questions.

This feature fixes those three things (the recommended changes), adds a small set of **episode
settings** so the learner can shape how a podcast sounds, and lets the learner **change a series'
settings for just the next episode or from now on**: for example, bringing an expert into Big Little
Questions for one episode, or for every episode after it.

Episode 45, the series' second episode in Panel with Claude as the conversation partner, showed four
more problems. A strong model did not prevent them, so the cause is the design, not the model:

4. **Questions to the learner were left behind Continue.** The app decides whether a line invites the
   learner before the line is written, and never checks what was written. Six of thirteen
   non-inviting lines asked the learner something anyway ("Y el pan, ¿lo comes con otra cosa?"); when
   the learner pressed Continue, the next line ignored the question. A host's question to the other
   host was answered only when the name happened to appear.
5. **No subject was ever chosen.** The opening welcomed the learner back but named no subject;
   coffee became the topic by accident, and the show's hook, one everyday curiosity, came up once.
6. **The wrap-up did not wrap up.** The wrap-up line was asked both to wrap up and to ask a question,
   and kept only the question. Nothing told the learner the end was near, and a Short episode ran
   22 host lines until the learner pressed End.
7. **The expert was not much of an expert.** Asked why coffee takes a while to wake you up, Julia
   gave two short sentences. The level's two-sentence cap, the expert's "one fact at a time" style and
   the required closing question each shortened the answer; the level should limit how hard each
   sentence is, not how much the expert can explain.

The recommended changes therefore also include: the app knows who each host line is for and acts on
it, every episode is about one subject that the opening names, the wrap-up says the show is ending
and the hosts then sign off, and explaining lines are longer than reacting ones.

## Clarifications

### Session 2026-10-18

- Q: When several settings of one series episode are changed, is the scope (Just this episode / This and later episodes) chosen once for all changes or per change? → A: Per change: each changed setting gets its own scope, asked when that setting is first changed, and the setup marks each one "this episode" or "from now on".
- Q: In a One host series switched to Panel for Just this episode, is the show's expert who joins a one-episode guest or a standing second host? → A: A one-episode guest, cast fresh each time, introduced as joining today, never part of the series' cast; only a This-and-later-episodes switch to Panel casts a regular second host.
- Q: Does 007 SC-009's target (next host line starts playing within 5 s of Continue, 90% of cases) still hold for Medium and Long lines? → A: Yes, the same 5 s target for every length, measured to the line's first sentence starting to play; later sentences may arrive while it speaks.
- Q: Outside a series, does Your role start on the show's own role or on the role used last? → A: Always on the show's own role; Style, Host lines and How often you're asked carry over from last time.
- Q: After a guest episode, how does the regular host who was away treat what the series remembers from it? → A: That episode's remembered points are marked as from an episode the host missed; the host may mention them as heard secondhand, never as having been there.

### Session 2026-11-03

From the review of episode 45 (Big Little Questions, Panel, Short, Beginner, Claude).

- Q: How does the app know who a host line is for: the learner, the other host or no one in particular? → A: The host says so in a short hidden note at the end of the line, which is never shown or spoken. When the note is missing, the app falls back to the names and the question mark in the line. No extra model call is made.
- Q: When does the learner get the turn? → A: Whenever a host line asks them something, whatever How often you're asked drew. The setting decides how often a host is told it may ask; a line that may not ask is told not to.
- Q: After the wrap-up, do the hosts sign off on their own? → A: Yes. The wrap-up says the show is nearly over and asks for one last thought. After the learner's reply, or a pass, the next host line signs off. A question in the reply is answered first. This replaces 007's "the episode ends when the learner chooses End" for new episodes.
- Q: Who picks the subject when Today's subject is empty? → A: The opening host names one concrete subject within the show's topic (in a series, one not yet covered). The learner can also press Suggest subjects for a few generated subjects not yet covered, and pick one.
- Q: How long may an expert's explanation be? → A: Lines that explain, answer or tell use the upper part of the Host lines range, and reacting lines the lower part. A closing question to the learner is not counted. The level still decides how simple each sentence is.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hosts talk like podcast hosts, at the learner's level (Priority: P1)

The learner, at Beginner, starts Big Little Questions in One host. Hugo opens the show with a proper
introduction, several short, simple sentences long. When the learner asks why toast lands butter-side
down, Hugo answers it: a few simple sentences explaining the table's height and the half turn, then a
small story about his own breakfast. Every sentence is still short, in the present tense and in
everyday words, but a line can now be long enough to say something. Hugo does not end every line with
a question; for a line or two he just talks, and the learner presses Continue or jumps in.

**Why this priority**: This is the learner's complaint. Without it the other stories only add settings
to a show that still feels like an interview.

**Independent Test**: At Beginner, play a Medium One host episode of Big Little Questions with the
default settings. Verify that host lines are several sentences long while each sentence stays within
the Beginner limits, that not every host line asks the learner something, that a question the learner
asks is answered in the next host line, and that some host lines explain or tell rather than react.
Then play a Short Panel episode: verify that every host question to the learner gives them the turn,
that a host's question to the other host is answered by that host, that the opening names a subject,
and that the hosts sign off after the learner's last thought.

**Acceptance Scenarios**:

1. **Given** the Beginner level and default episode settings, **When** a host speaks, **Then** the line
   may hold several sentences, and each sentence follows the level's limits on sentence length, tenses,
   vocabulary and idioms.
2. **Given** a One host episode with default settings, **When** the host speaks, **Then** not every
   line invites the learner; the learner is still invited at the latest by the fourth host line in a
   row.
3. **Given** the host has the floor in a One host episode, **When** the learner wants to speak, **Then**
   they can jump in, as in Panel.
4. **Given** the learner asks the host a question, **When** the next host line is spoken, **Then** it
   answers the question before moving on, and does not answer it with another question.
5. **Given** a One host episode of a show whose second host has a role (Big Little Questions' expert),
   **When** the host speaks, **Then** the host also covers that role, so the show's questions get
   answered.
6. **Given** any episode, **When** the discussion runs, **Then** some host lines explain something or
   tell a short story, not only react to the last line.
7. **Given** a host line asks the learner something, **When** the line ends, **Then** it is the
   learner's turn, whatever How often you're asked drew; a question to the learner is never followed
   by only Continue.
8. **Given** a host line that may not invite the learner, **When** it is spoken, **Then** it asks the
   learner nothing.
9. **Given** in Panel one host asks the other a question, **When** the next host line is spoken,
   **Then** the asked host speaks it and answers the question.
10. **Given** in Panel the learner asks both hosts something ("what do you two like?"), **When** the
    hosts reply, **Then** each host answers for themselves.
11. **Given** a host explains or answers, **When** the line is spoken, **Then** it is longer than a
    reacting line and explains how or why step by step, while every sentence keeps the level's limits.
    An expert host explains, not only states one fact.
12. **Given** Today's subject is empty, **When** the episode opens, **Then** the opening names one
    concrete subject within the show's topic, and the discussion stays on it until the wrap-up.
13. **Given** the episode reaches its length, **When** the wrap-up line is spoken, **Then** it says the
    show is nearly over and asks the learner for one last thought; after the learner's reply or a pass,
    the next host line signs off, answering first if the reply asked something.

In Panel, the same fixes read like this: Hugo asks Julia why coffee takes a while to wake you up, and
Julia answers in four or five simple sentences, step by step. When Hugo then asks the learner how
they take their coffee, it is the learner's turn, not Continue.

---

### User Story 2 - Learner shapes an episode with a few settings (Priority: P1)

On the setup screen, besides the format, length and hosts that exist today, the learner sees **Episode
settings**, closed by default and showing a one-line summary ("Balanced · Medium lines · Asked
sometimes"). Opening it offers:

- **Style**: *Conversation* (lots of back-and-forth), *Balanced* (the default) or *Presented* (the
  hosts mostly explain and tell stories, as on a radio show).
- **Host lines**: *Short*, *Medium* (the default) or *Long*.
- **How often you're asked**: *Often* (every host line, as One host is today), *Sometimes* (the
  default) or *Rarely*.
- **Your role**: guest, co-host or caller, starting on the show's own role.
- **Today's subject** (optional): a short free-text subject for this episode, such as "why do we yawn",
  kept within the show's topic. **Suggest subjects** offers three subjects within the show's topic
  (in a series, ones not yet covered); choosing one fills the field, which stays editable.

The learner can start without touching any of it. The Style, Host lines and How often you're asked
they used last are offered next time, as the format is today; Your role always starts on the show's
own role.

**Why this priority**: "Make the podcast more configurable" is the second part of the request, and the
fix in Story 1 needs somewhere to live: a learner who liked the old quick back-and-forth can choose
Conversation and Often to get it back.

**Independent Test**: Start two episodes of the same show, one with Presented · Long · Rarely and one
with Conversation · Short · Often. Verify the first has longer lines, more explaining and fewer
invitations than the second, that each episode keeps its settings when resumed, and that the next
setup offers the last Style, Host lines and How often you're asked used, with Your role on the show's
own role.

**Acceptance Scenarios**:

1. **Given** the setup screen, **When** it opens, **Then** Episode settings is closed, shows a summary
   of the current choices, and Start remains the single primary action.
2. **Given** the learner chooses Presented, **When** the episode runs, **Then** more host lines explain
   or tell stories than with Conversation, and fewer lines invite the learner.
3. **Given** the learner chooses Short host lines, **When** a host speaks, **Then** the line is at most
   two sentences, as today; Long lines are noticeably longer than Medium ones.
4. **Given** the learner chooses Rarely, **When** the hosts have the floor, **Then** they still invite
   the learner at the latest by the fourth host line in a row.
5. **Given** the learner types today's subject, **When** the episode opens, **Then** the hosts take it
   as the episode's subject; an unsuitable subject is declined with a plain message, as with the
   show generator, and the episode does not start until it is changed or cleared.
6. **Given** the Listen format, **When** the setup screen shows Episode settings, **Then** How often
   you're asked and Your role are not offered, because the learner does not speak.
7. **Given** an episode was started with some settings, **When** it is resumed later, **Then** it keeps
   those settings, even if the learner has since chosen others for new episodes.
8. **Given** the setup screen, **When** the learner presses Suggest subjects, **Then** up to three
   subjects within the show's topic appear (in a series, none already covered); choosing one fills
   Today's subject, and pressing again offers different ones.

---

### User Story 3 - Learner changes a series' settings for one episode or from now on (Priority: P1)

The learner has a Big Little Questions series in One host with Hugo. On the setup screen for Episode 4
they open Episode settings and switch the format to Panel, so the show's expert joins as the second
host. Because this is a series, changing a setting asks one question: **Just this episode** or **This
and later episodes**. They choose Just this episode, and the format is marked "this episode". Episode 4
runs with Hugo and the expert, who joins as a guest for today; Episode 5 opens in One host again with
the series' usual settings. Later they make Presented their series' default by choosing This and later
episodes; on the same setup they can still switch the format for just that episode, because each
changed setting has its own scope.

**Why this priority**: This is the third part of the request, and its example ("change Big Little
Questions so that there is an expert, for an episode or more"). It builds on the settings of Story 2,
which a series must remember.

**Independent Test**: In a series, change the format and the style for Just this episode and play the
episode; verify the next episode's setup shows the series' previous settings. Then change the style
for This and later episodes; verify the next two episodes use it. Check that the episode count and the
hosts' memory are unaffected by either change.

**Acceptance Scenarios**:

1. **Given** a series, **When** the learner opens its next episode's setup, **Then** every setting
   (format, length, the Episode settings and the hosts) starts on the series' own settings, not on the
   last settings used elsewhere.
2. **Given** the learner changes a series setting, **When** they start the episode, **Then** they have
   chosen, for each changed setting, Just this episode or This and later episodes, and the setup
   screen marks each changed setting "this episode" or "from now on".
3. **Given** a change made for Just this episode, **When** the next episode's setup opens, **Then** it
   shows the series' usual settings again.
4. **Given** a change made for This and later episodes, **When** the next episodes' setups open,
   **Then** they start on the changed settings until the learner changes them again.
5. **Given** either kind of change, **When** the episode is played, **Then** it counts as the series'
   next episode, and the hosts' memory is read and updated as for any series episode.
6. **Given** the learner has changed series settings, **When** they choose to go back to the show's
   standard settings, **Then** the series' usual settings return to the show's defaults after a
   confirmation; past episodes are unchanged.

---

### User Story 4 - A guest host joins a series for one episode (Priority: P2)

The learner's Big Little Questions series has two regular hosts, Hugo and Clara. For Episode 6 they
want a different expert's view, so they choose **Invite a guest for this episode** on one host's chair
and pick a personality (Expert). The guest gets a name and a voice like any host. In the episode, Hugo
introduces the guest as joining for today, and Clara is said to be away. In Episode 7, Clara is back;
she may say she heard what Episode 6 was about ("Hugo told me you talked about yawning") but never that
she was there, while Hugo remembers it as any episode. Recasting a host for good
works as today: it applies to this and later episodes.

**Why this priority**: It completes "for an episode or more" for hosts, the most personal setting of a
series, so a one-time change never replaces a regular host. Story 3 already covers adding the show's
expert by changing the format for one episode, and that expert is a guest under the same rules; this
story adds a guest in a regular host's place.

**Independent Test**: In a two-host series, invite a guest in place of the second host for one
episode. Verify the guest is introduced as a guest, the regular host is said to be away, and the next
episode returns to the regular host, who never claims to have been in the guest episode (mentioning it
as heard secondhand is fine), while the series' count and the other host's memory include it.

**Acceptance Scenarios**:

1. **Given** a series episode's setup, **When** the learner looks at a host, **Then** they can invite a
   guest for this episode in that host's place, or recast the host from now on (010 FR-009).
2. **Given** a guest for this episode, **When** the learner chooses its personality, **Then** the guest
   is cast with a name and a voice that differ from the other host's, as for any host.
3. **Given** a guest episode, **When** it opens, **Then** the guest is introduced as joining for this
   episode, and the absent regular host is mentioned as away.
4. **Given** a guest episode has been played, **When** the next episode opens, **Then** the regular
   host is back with the same name, personality and voice, and the guest does not reappear unless
   invited again.
5. **Given** the returning host mentions the guest episode, **When** they speak of it, **Then** they
   speak of it as something they heard about, never as something they were there for.
6. **Given** a guest episode in a One host series, **When** the learner invites the guest, **Then** the
   guest takes the one host's place for that episode, or, if the learner switches to Panel for that
   episode, joins as the second host beside the regular host.

---

### Edge Cases

- **Settings and level together**: the level always decides how simple each sentence is; the Host lines
  setting decides how many sentences a line may hold. At Natural, Short still means at most two
  sentences.
- **The learner changes the level during an episode**: as today, it applies from the next host line;
  the episode settings do not change.
- **Conversation · Often**: gives today's quick back-and-forth, a question on every host line, so the learner can
  keep the quick back-and-forth if they prefer it.
- **A long line in Listen with Show text off**: the words stay hidden until tapped, whatever the length.
- **Replay and Slower on a long line**: replay the whole line, as today.
- **A long line still arriving**: its first sentence starts playing before the rest has arrived, and the
  remaining sentences follow without a gap the learner must wait through; Replay and Slower are offered
  once the whole line has arrived.
- **The learner asks two questions at once**: the next host line answers at least one and says the
  other will come; the other is answered within the next two host lines.
- **The learner answers instead of asking**: the host reacts and carries on in the episode's style.
- **Just this episode, then the episode is abandoned**: the change still applied only to that episode;
  the next setup shows the series' usual settings.
- **A Just-this-episode change, then the learner resumes that episode later**: it resumes with the
  settings it started with.
- **A guest's name matches the learner's name or a regular host's**: a different name is cast, as for
  any host.
- **A guest whose voice is missing**: handled as for any host (007 FR-031): the learner is told plainly,
  and the guest's lines can be read as text.
- **One host series and a guest**: the regular host is away for that episode; the series' memory still
  records the topic and what the learner said, marked as missed by that host (FR-022).
- **A host misses two guest episodes in a row**: every point from both is marked as missed by them.
- **Series settings in another language**: each language's series has its own settings, as its hosts
  and memory are per language (010).
- **Episodes and series that existed before this feature**: they keep working; series start on the
  show's standard settings with the new defaults, and an unfinished episode resumes as it was.
- **Today's subject already covered in the series**: the hosts take it anyway, because the learner
  asked for it, and may say they have touched on it before.
- **A provider that cannot keep long lines simple** (the default local model may drift at Beginner):
  the level's limits still apply; SC-002 measures this and may lead to an experimental label, as with
  earlier features.
- **The hidden note is missing or names someone who isn't there**: the line names someone and ends
  with a question → it is for the last person it names; otherwise a line naming the other host hands
  over to them, as today; otherwise it is for no one in particular. The note is never shown or spoken
  either way.
- **A host asks both the learner and the other host in one line**: the hidden note decides; without
  it, the last person named before the closing question does.
- **The learner's question names one host**: that host answers, as today (007 FR-018), even if the
  other host just spoke.
- **The learner asks something after the wrap-up**: the next host line answers it, and the hosts sign
  off at the following Continue. The learner can keep asking with Jump in; each question is answered
  before the sign-off.
- **The learner passes on the wrap-up**: the next host line signs off.
- **End episode before the wrap-up**: a sign-off at once, as today.
- **Suggest subjects with the conversation partner unavailable**: a plain message says what to do;
  typing a subject and starting with an empty one both still work.
- **A suggested subject, then edited**: checked like any typed subject at Start (FR-010).
- **Suggest subjects pressed again**: the subjects already shown are not offered again; when nothing
  new comes back, the learner is told so and the shown subjects stay.
- **Listen**: the opening names the subject and the wrap-up says the show is nearly over, but nobody
  is asked a last thought; the sign-off follows the wrap-up, as today.

## Requirements *(mandatory)*

### Functional Requirements

**How hosts talk (the recommended changes)**

- **FR-001**: The number of sentences a host line may hold MUST be set by the Host lines setting, not by
  the conversation level's reply cap. The level MUST still govern each sentence's length, tenses,
  vocabulary and idioms, and a level change MUST still apply from the next host line. This replaces
  007 FR-026's reply cap for podcast host lines only; the roleplay partner is unchanged.
- **FR-002**: Host lines MUST be: Short, at most 2 sentences; Medium, 3 to 5 sentences; Long, 5 to 8
  sentences, not counting a closing question to the learner (FR-003). Medium MUST be the default.
- **FR-002b**: Within the Host lines range, lines that open, explain, answer or tell MUST use the upper
  part and lines that greet, react, wrap up or sign off the lower part.
- **FR-002a**: A host line of any length MUST start playing as quickly as a Short line does today
  (007 SC-009): playback MUST NOT wait for the whole line when its first sentence is ready.
- **FR-003**: In One host as in Panel, a host MUST be allowed to invite the learner only as often as
  the How often you're asked setting allows: Often, every host line; Sometimes (the default), one host
  line in two on average; Rarely, one in four on average. A line that is allowed to invite asks only
  when it fits the conversation. In every case the learner MUST be invited at the latest by the fourth
  host line in a row (007 FR-014). Invitations MUST be one question, clearly addressed to the
  learner, added after the line's sentences, and MUST NOT always be yes/no questions above the
  Beginner level.
- **FR-003a**: A host line that is not allowed to invite MUST NOT ask the learner anything. Whenever a
  host line asks the learner something anyway, it MUST be the learner's turn: a question to the
  learner is never followed by only Continue. Hosts MUST NOT ask the learner something the learner
  has already answered in this episode.
- **FR-003b**: The app MUST know who each host line is for (the learner, the other host, or no one in
  particular) without showing or speaking anything extra and without an extra model call. In Panel,
  the next host line MUST come from the host the last line was for, within the run limit (007
  FR-015); a line for no one in particular leaves the choice to the flow rules (007 FR-013).
- **FR-004**: The learner MUST be able to jump in whenever the hosts have the floor in One host as in
  Panel (extending 007 FR-017).
- **FR-005**: When the learner's last line asks a question, the next host line MUST answer it before
  anything else and MUST NOT reply to it only with a question. The same holds when a host asks the
  other host a question: the asked host's next line answers it. When the learner's question is for
  both hosts, each host MUST answer it for themselves.
- **FR-006**: Besides reacting, hosts MUST be able to speak lines that explain something or tell a short
  story or example. The share of such lines MUST follow the Style setting: fewest with Conversation,
  most with Presented.
- **FR-006a**: Lines that explain or answer MUST explain step by step (what it is, how or why it
  works, an everyday example), using the length FR-002b gives them. An expert host MUST explain how
  and why, not only state one fact; an interviewing host MUST also say what they think, not only ask.
- **FR-007**: In One host, the host MUST also cover the absent second host's role in the show (for
  example, an interviewer who also gives the expert's answers), so the show keeps its purpose.
- **FR-007a**: Every episode MUST be about one subject. The opening line MUST name it: Today's subject
  when given, otherwise one concrete subject the host chooses within the show's topic (in a series,
  one not in the covered list). The hosts MUST stay on it until the wrap-up.
- **FR-007b**: The wrap-up line MUST say the show is nearly over and, in a speaking format, ask the
  learner for one last thought rather than a new question. After the learner's reply, or a pass, the
  next host line MUST sign off; if the reply asks a question, that line answers it and the sign-off
  comes at the next Continue. In Listen, the sign-off follows the wrap-up, as today. End episode
  stays available at any time. For new episodes this replaces 007's edge case "the episode ends when
  the learner chooses End".

**Episode settings**

- **FR-008**: The setup screen MUST offer Episode settings: Style, Host lines, How often you're asked,
  Your role, and an optional Today's subject. It MUST be closed by default, show a one-line summary of
  the current choices, and MUST NOT add a second primary action.
- **FR-009**: Style MUST offer Conversation, Balanced (the default) and Presented. Your role MUST offer
  guest, co-host and caller, starting on the show's own role.
- **FR-010**: Today's subject MUST be optional, short (at most 120 characters), and checked by the same
  suitability rules as the show generator (007 FR-024); an unsuitable subject MUST be declined with a
  plain message saying what to change.
- **FR-010a**: Beside Today's subject, the setup MUST offer Suggest subjects, a secondary action. It
  gives up to three suitable subjects within the show's topic, from the selected conversation
  partner, drawing on the learner's interests where they fit. In a series, none of them may be a
  subject the series has already covered. Pressing it again MUST NOT repeat a subject already shown.
  Choosing a subject fills Today's subject, which stays editable and is checked at Start like any
  typed subject. A provider failure MUST be shown as a plain message, and starting MUST still work.
- **FR-011**: In the Listen format, How often you're asked and Your role MUST NOT be offered.
- **FR-012**: An episode MUST keep the settings it started with for its whole life, including when
  resumed.
- **FR-013**: Outside a series, the setup screen MUST start Style, Host lines and How often you're
  asked on the values the learner used last, or on the defaults the first time. Your role MUST start on
  the show's own role, and Today's subject MUST NOT be carried over.

**Series settings**

- **FR-014**: Every series MUST have its own usual settings: format, length, the Episode settings
  (except Today's subject) and its hosts. A series' first episode MUST set them from that episode's
  choices.
- **FR-015**: A series episode's setup MUST start on the series' usual settings.
- **FR-016**: When the learner changes a setting of a series episode, they MUST choose Just this
  episode or This and later episodes for that setting, asked when it is first changed on this setup;
  changing it again keeps its scope. Each changed setting has its own scope, so one setup can mix
  both. The setup screen MUST mark each changed setting "this episode" or "from now on".
- **FR-017**: A Just-this-episode change MUST apply to that episode only; that setting's series value
  MUST be unchanged. A This-and-later-episodes change MUST become that setting's series value. Both
  take effect when the episode starts; leaving the setup without starting discards them.
- **FR-018**: A series episode with changed settings MUST count as the series' next episode and MUST
  read and update the series' memory as any series episode does (010 FR-004, FR-005).
- **FR-019**: Learners MUST be able to return a series' usual settings to the show's standard settings
  after a confirmation, without changing past episodes, the episode count, the hosts or the memory.

**Guest hosts**

- **FR-020**: In a series episode, learners MUST be able to invite a guest for this episode in place of
  either host, choosing the guest's personality; the guest MUST be cast with a name and voice under the
  same rules as any host (007 FR-006 to FR-008).
- **FR-021**: A guest MUST be introduced as joining for this episode, and the regular host they replace
  MUST be referred to as away, never as having left the show.
- **FR-022**: A guest MUST NOT become a series host: the next episode MUST return to the regular hosts.
  The series' memory MUST still record the guest episode's topic and what the learner said, and each
  point from it MUST be marked as from an episode the away host missed. That host MAY mention such a
  point as heard secondhand, and MUST NOT claim to have been in that episode or to have heard the
  learner say it.
- **FR-023**: Recasting a host for good MUST work as in 010 FR-009, offered beside the guest option, so
  the learner chooses between this episode and from now on.
- **FR-024**: The number of people in an episode MUST still not exceed three, the learner included
  (007 FR-004). A guest takes a host's place or Panel's empty second chair; it never adds a fourth
  person.
- **FR-024a**: When a One host series switches to Panel for Just this episode, the second host MUST be
  a guest under FR-020 to FR-022, cast for the show's second role (for Big Little Questions, the
  expert) and cast afresh each time; no regular host is away. When the switch to Panel is This and
  later episodes, the second host MUST be cast as a regular series host (010 FR-009).

**Compatibility**

- **FR-025**: Episodes started before this feature MUST resume with the behaviour they started with.
  Existing series MUST keep their hosts, episode count and memory, and MUST start on the show's standard
  settings with the new defaults.
- **FR-026**: The new defaults (Balanced, Medium, Sometimes) MUST apply to new one-off and series
  episodes alike. Conversation, Short and Often together MUST reproduce today's quick back-and-forth
  (short lines and a question on every host line) for learners who prefer it. The fixes of FR-003a,
  FR-003b, FR-007a and FR-007b apply under every setting.
- **FR-027**: Episode settings, series settings and guests MUST work with every conversation-partner
  provider the learner can select and with every practice language, without per-language changes
  beyond the existing language data.

### Key Entities *(include if feature involves data)*

- **Episode settings**: how an episode sounds: Style, Host lines, How often you're asked, Your role and
  an optional Today's subject. Fixed for an episode once it starts.
- **Series settings**: a series' usual format, length, Episode settings (without Today's subject) and
  hosts. Set by the first episode, changed by a This-and-later-episodes change, reset on request.
- **Episode override**: the settings of one series episode that differ from the series' usual ones,
  each with its own scope (this episode, or from now on).
- **Guest host**: a host who appears in one series episode, either in place of a regular host or as the
  second host of a one-episode switch to Panel: personality, name, voice, and the host they replace (if
  any). Cast afresh for each episode; never part of the series' cast.
- **Line kind**: what a host line does: react, explain, tell a story or example, invite the learner,
  answer the learner's or the other host's question, open (naming the episode's subject), wrap up or
  sign off.
- **Who a line is for**: stored with each host line: the learner, the other host, or no one in
  particular. It decides whose turn comes next and is never shown or spoken.
- **Subject suggestion**: a subject offered by Suggest subjects for one setup; not stored unless the
  learner starts with it as Today's subject.
- **Last-used settings**: the Style, Host lines and How often you're asked the learner used last
  outside a series, offered on the next setup (not Your role or Today's subject).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a review of at least 20 Medium One host episodes at Beginner with default settings, the
  median host discussion line has at least 3 sentences, and no more than 50% of host lines invite the
  learner.
- **SC-002**: In the same review, at least 90% of host-line sentences stay within the Beginner sentence
  length, and at least 90% use only present-tense verbs.
- **SC-003**: In a review of at least 20 learner questions asked during episodes, at least 90% are
  answered in the very next host line.
- **SC-004**: Across reviewed Presented episodes, at least 40% of discussion lines explain or tell a
  story; across Conversation episodes, at most 20% do.
- **SC-005**: The learner is never left more than four host lines in a row without an invitation, in
  any speaking format and setting (checked over every reviewed episode).
- **SC-006**: In 100% of checked cases, a Just-this-episode change leaves the next episode's setup on
  the series' usual settings, and a This-and-later-episodes change appears on the next two episodes'
  setups.
- **SC-007**: From a One host series' next-episode setup, the learner can bring in an expert for one
  episode in at most three choices before Start.
- **SC-008**: A learner can start an episode with the defaults in the same number of choices as today
  (Episode settings never has to be opened).
- **SC-009**: In a review of at least 10 guest episodes, 100% introduce the guest as a guest, and in the
  following episodes 0 lines from the returning host claim to have been in the guest episode or to have
  heard the learner say something from it (mentions as heard secondhand are allowed).
- **SC-010**: All episodes, series, memories, conversations, vocabulary and settings that existed before
  the change are still present and usable afterwards.
- **SC-011**: After Continue, the next host line's first sentence starts playing within 5 seconds in 90%
  of cases with the default local setup, for Short, Medium and Long lines alike (007 SC-009 kept).
- **SC-012**: In a review of at least 20 Panel and 20 One host episodes with default settings, at least
  95% of host lines that ask the learner something give the learner the turn, and at least 90% of a
  host's questions to the other host are answered by that host in the very next line.
- **SC-013**: In the SC-001 review, the median line that explains or answers has at least 4
  sentences, while SC-002's sentence limits still hold.
- **SC-014**: In the reviewed episodes, at least 90% of openings name one concrete subject, and at
  least 90% of wrap-up lines say the show is nearly over.
- **SC-015**: In 100% of speaking episodes that reach the wrap-up, the hosts sign off at the first host
  line after the learner's last thought that does not answer a question (checked automatically).
- **SC-016**: Over 10 presses of Suggest subjects in a series with covered subjects, every press shows
  at least one subject, and no suggestion repeats a covered subject or one already shown (reviewed).

## Assumptions

- **"The recommended changes" are the three from the earlier diagnosis**: longer lines at the same
  level, fewer questions in One host, and lines that explain or tell, plus the four from episode 45
  (Overview, items 4–7). They become the defaults for every new episode, so the learner's complaint is
  fixed without opening any settings.
- **Hosts say who a line is for.** The model adds a short note at the end of each line saying who it
  is for; the app removes it before the line is shown, spoken, summarised or remembered. When a model
  leaves it out, the names and question marks in the line decide, so smaller models still work, only
  less precisely. SC-012 measures how often each approach is needed.
- **Ending on its own changes 007 for new episodes only.** Episodes started before this feature keep
  running until End (FR-025).
- **"More configurable" means the five Episode settings above**, chosen because each maps to something
  the learner noticed (line length, questions, style) or to something a series wants to vary (role,
  today's subject). Voice speed, the number of hosts beyond two, and changing settings mid-episode are
  out of scope.
- **"Add an expert" is a format or host change, not a fourth person.** Big Little Questions already
  has an expert as its second host, who appears in Panel and Listen; One host dropped them. Switching
  the series to Panel brings the expert in; a guest (Story 4) brings in a different person for one
  episode. The three-person cap (007 FR-004) stays.
- **"For an episode or more" means two scopes**: this episode only, or this and later episodes until
  changed again. A count of episodes ("the next three") is not offered.
- **The level still protects the learner.** A Beginner line can be longer but never harder: each
  sentence keeps the Beginner limits, and the learning tools (translate, replay slower, word lookup)
  work on long lines as on short ones.
- **The one-off prompt changes on purpose.** 010 pinned one-off episodes to 007's behaviour; this
  feature changes how every new host line is asked for, one-offs included. Episodes already started
  keep their old behaviour (FR-025).
- **Line-level behaviour is model-dependent.** As with levels, corrections and series, the default local
  model may keep long Beginner lines simple less reliably than a larger one; SC-001 to SC-004 and
  SC-012 to SC-014 measure this and may lead to an experimental label.
- **Settings stay on the learner's machine** like the rest of their data; today's subject goes to the
  conversation partner as part of the episode context, under the existing provider notice. Suggest
  subjects sends the show, the series' covered subjects and the learner's interests to the selected
  conversation partner, under the same notice.
