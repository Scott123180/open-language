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
  kept within the show's topic.

The learner can start without touching any of it. The settings they used last are offered next time,
as the format is today.

**Why this priority**: "Make the podcast more configurable" is the second part of the request, and the
fix in Story 1 needs somewhere to live: a learner who liked the old quick back-and-forth can choose
Conversation and Often to get it back.

**Independent Test**: Start two episodes of the same show, one with Presented · Long · Rarely and one
with Conversation · Short · Often. Verify the first has longer lines, more explaining and fewer
invitations than the second, that each episode keeps its settings when resumed, and that the next
setup offers the last settings used.

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

---

### User Story 3 - Learner changes a series' settings for one episode or from now on (Priority: P1)

The learner has a Big Little Questions series in One host with Hugo. On the setup screen for Episode 4
they open Episode settings and switch the format to Panel, so the show's expert joins as the second
host. Because this is a series, changing a setting asks one question: **Just this episode** or **This
and later episodes**. They choose Just this episode. Episode 4 runs with Hugo and the expert; Episode 5
opens in One host again with the series' usual settings. Later they make Presented their series'
default by choosing This and later episodes.

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
   chosen, for the change, Just this episode or This and later episodes, and the setup screen shows
   which settings differ from the series' usual ones.
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
introduces the guest as joining for today, and Clara is said to be away. In Episode 7, Clara is back,
and she does not claim to remember what the guest said, while Hugo does. Recasting a host for good
works as today: it applies to this and later episodes.

**Why this priority**: It completes "for an episode or more" for hosts, the most personal setting of a
series, so a one-time change never replaces a regular host. Story 3 already covers adding the show's
expert by changing the format; this adds a different person for one episode.

**Independent Test**: In a two-host series, invite a guest in place of the second host for one
episode. Verify the guest is introduced as a guest, the regular host is said to be away, and the next
episode returns to the regular host, who does not claim to remember the guest episode, while the
series' count and the other host's memory include it.

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
5. **Given** a guest episode in a One host series, **When** the learner invites the guest, **Then** the
   guest takes the one host's place for that episode, or, if the learner switches to Panel for that
   episode, joins as the second host beside the regular host.

---

### Edge Cases

- **Settings and level together**: the level always decides how simple each sentence is; the Host lines
  setting decides how many sentences a line may hold. At Natural, Short still means at most two
  sentences.
- **The learner changes the level during an episode**: as today, it applies from the next host line;
  the episode settings do not change.
- **Conversation · Often**: gives today's behaviour, a question on every host line, so the learner can
  keep the quick back-and-forth if they prefer it.
- **A long line in Listen with Show text off**: the words stay hidden until tapped, whatever the length.
- **Replay and Slower on a long line**: replay the whole line, as today.
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
  records the topic and what the learner said.
- **Series settings in another language**: each language's series has its own settings, as its hosts
  and memory are per language (010).
- **Episodes and series that existed before this feature**: they keep working; series start on the
  show's standard settings with the new defaults, and an unfinished episode resumes as it was.
- **Today's subject already covered in the series**: the hosts take it anyway, because the learner
  asked for it, and may say they have touched on it before.
- **A provider that cannot keep long lines simple** (the default local model may drift at Beginner):
  the level's limits still apply; SC-002 measures this and may lead to an experimental label, as with
  earlier features.

## Requirements *(mandatory)*

### Functional Requirements

**How hosts talk (the recommended changes)**

- **FR-001**: The number of sentences a host line may hold MUST be set by the Host lines setting, not by
  the conversation level's reply cap. The level MUST still govern each sentence's length, tenses,
  vocabulary and idioms, and a level change MUST still apply from the next host line. This replaces
  007 FR-026's reply cap for podcast host lines only; the roleplay partner is unchanged.
- **FR-002**: Host lines MUST be: Short, at most 2 sentences; Medium, 3 to 5 sentences; Long, 5 to 8
  sentences. Medium MUST be the default.
- **FR-003**: In One host as in Panel, a host line MUST invite the learner only as often as the How
  often you're asked setting allows: Often, every host line; Sometimes (the default), one host line in
  two on average; Rarely, one in four on average. In every case the learner MUST be invited at the
  latest by the fourth host line in a row (007 FR-014). Invitations MUST be one question, clearly
  addressed to the learner, and MUST NOT always be yes/no questions above the Beginner level.
- **FR-004**: The learner MUST be able to jump in whenever the hosts have the floor in One host as in
  Panel (extending 007 FR-017).
- **FR-005**: When the learner's last line asks a question, the next host line MUST answer it before
  anything else and MUST NOT reply to it only with a question.
- **FR-006**: Besides reacting, hosts MUST be able to speak lines that explain something or tell a short
  story or example. The share of such lines MUST follow the Style setting: fewest with Conversation,
  most with Presented.
- **FR-007**: In One host, the host MUST also cover the absent second host's role in the show (for
  example, an interviewer who also gives the expert's answers), so the show keeps its purpose.

**Episode settings**

- **FR-008**: The setup screen MUST offer Episode settings: Style, Host lines, How often you're asked,
  Your role, and an optional Today's subject. It MUST be closed by default, show a one-line summary of
  the current choices, and MUST NOT add a second primary action.
- **FR-009**: Style MUST offer Conversation, Balanced (the default) and Presented. Your role MUST offer
  guest, co-host and caller, starting on the show's own role.
- **FR-010**: Today's subject MUST be optional, short (at most 120 characters), and checked by the same
  suitability rules as the show generator (007 FR-024); an unsuitable subject MUST be declined with a
  plain message saying what to change.
- **FR-011**: In the Listen format, How often you're asked and Your role MUST NOT be offered.
- **FR-012**: An episode MUST keep the settings it started with for its whole life, including when
  resumed.
- **FR-013**: Outside a series, the setup screen MUST start on the episode settings the learner used
  last, or on the defaults the first time. Today's subject MUST NOT be carried over.

**Series settings**

- **FR-014**: Every series MUST have its own usual settings: format, length, the Episode settings
  (except Today's subject) and its hosts. A series' first episode MUST set them from that episode's
  choices.
- **FR-015**: A series episode's setup MUST start on the series' usual settings.
- **FR-016**: When the learner changes any setting of a series episode, they MUST choose Just this
  episode or This and later episodes for the change before starting. The setup screen MUST show which
  settings differ from the series' usual ones.
- **FR-017**: A Just-this-episode change MUST apply to that episode only; the series' usual settings
  MUST be unchanged. A This-and-later-episodes change MUST become the series' usual settings.
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
- **FR-022**: A guest MUST NOT become a series host: the next episode MUST return to the regular hosts,
  and the regular host who was away MUST NOT claim to remember the guest episode. The series' memory
  MUST still record the guest episode's topic and what the learner said.
- **FR-023**: Recasting a host for good MUST work as in 010 FR-009, offered beside the guest option, so
  the learner chooses between this episode and from now on.
- **FR-024**: The number of people in an episode MUST still not exceed three, the learner included
  (007 FR-004). A guest takes a host's place; it never adds a fourth person.

**Compatibility**

- **FR-025**: Episodes started before this feature MUST resume with the behaviour they started with.
  Existing series MUST keep their hosts, episode count and memory, and MUST start on the show's standard
  settings with the new defaults.
- **FR-026**: The new defaults (Balanced, Medium, Sometimes) MUST apply to new one-off and series
  episodes alike. Conversation, Short and Often together MUST reproduce today's behaviour for learners
  who prefer it.
- **FR-027**: Episode settings, series settings and guests MUST work with every conversation-partner
  provider the learner can select and with every practice language, without per-language changes
  beyond the existing language data.

### Key Entities *(include if feature involves data)*

- **Episode settings**: how an episode sounds: Style, Host lines, How often you're asked, Your role and
  an optional Today's subject. Fixed for an episode once it starts.
- **Series settings**: a series' usual format, length, Episode settings (without Today's subject) and
  hosts. Set by the first episode, changed by a This-and-later-episodes change, reset on request.
- **Episode override**: the settings of one series episode that differ from the series' usual ones,
  for that episode only.
- **Guest host**: a host who appears in one series episode in place of a regular host: personality,
  name, voice, and the host they replace. Never part of the series' cast.
- **Line kind**: what a host line does: react, explain, tell a story or example, invite the learner,
  answer the learner's question, open, wrap up or sign off.
- **Last-used settings**: the Episode settings the learner used last outside a series, offered on the
  next setup.

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
  following episodes 0 lines from the returning host claim to remember the guest episode.
- **SC-010**: All episodes, series, memories, conversations, vocabulary and settings that existed before
  the change are still present and usable afterwards.

## Assumptions

- **"The recommended changes" are the three from the earlier diagnosis**: longer lines at the same
  level, fewer questions in One host, and lines that explain or tell. They become the defaults for every
  new episode, so the learner's complaint is fixed without opening any settings.
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
  model may keep long Beginner lines simple less reliably than a larger one; SC-001 to SC-004 measure
  this and may lead to an experimental label.
- **Settings stay on the learner's machine** like the rest of their data; today's subject goes to the
  conversation partner as part of the episode context, under the existing provider notice.
