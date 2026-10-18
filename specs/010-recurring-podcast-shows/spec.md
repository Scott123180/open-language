# Feature Specification: Recurring Podcast Shows

**Feature Branch**: `010-recurring-podcast-shows`
**Created**: 2026-10-17
**Status**: Draft
**Input**: User description: "The personality drop-down on the podcast setup screen (Expert, Contrarian, …)
is on theme when closed, but its open list of options is not. The recent visual improvements are good.
There are two use cases: you go in and want just a regular podcast, or you want to interact with
someone and build a relationship. I want a more consistent persona option. The podcast themes are the
same every time, and that consistency is good — here's the original list. I can imagine Big Little
Questions with Hugo, the curious interviewer, as a long-running podcast: here's the next episode of Big
Little Questions, we already went through one episode, and people can have favourite podcasts. And if
they want something new, maybe a refresh button that finds your next podcast."

## Overview

Podcast mode (007) treats every episode as a one-off: the learner picks a show, the hosts are cast,
and the episode ends. Nothing carries over. This feature adds the second use case the learner
described — **a show as a series**, where the same hosts return episode after episode, remember the
learner and what was said, and become familiar people to practise with. The quick one-off episode
stays as it is today.

It also keeps the fixed list of ready-made shows as the stable starting point, lets the learner mark
favourite shows, offers a way to **find a new show** when they want something different, and fixes
the personality drop-down whose open list ignores the app's theme.

## Clarifications

### Session 2026-10-17

- Q: Should episodes recorded before this feature start series? → A: No. Every show starts a fresh
  series; earlier episodes stay in Past Chats but are not counted or remembered (FR-022).
- Q: If the hosts' memory of the last episode is still being updated when the learner starts the
  next one, should the start wait? → A: Yes. The setup screen tells the learner the hosts are
  catching up, waits, then starts. If the update fails or takes too long, the learner can try
  again or start without it. FR-006 and SC-006 concern the episode once it starts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner continues a show as a series with the same hosts (Priority: P1)

The learner has already done one episode of Big Little Questions with Hugo, the curious interviewer.
They open Podcasts and see that show marked with how many episodes they have done. Choosing it offers
**Episode 2** as the main action. The setup screen shows Hugo again — same name, same personality,
same voice — and the episode starts. Hugo greets the learner by name, says this is the next episode,
and brings up something from last time ("Last week you told me you hate mornings — so today: why do
we yawn?"). The topic is new; the people are the same.

**Why this priority**: This is the heart of the request: a long-running podcast with a host the
learner gets to know. Every other story builds on a show having episodes and hosts that persist.

**Independent Test**: Finish one episode of a ready-made show, then start that show again. Verify the
setup offers the next episode by number, the hosts' names, personalities and voices are unchanged,
and the opening lines refer to the learner and to something specific from the previous episode, on a
topic not already covered.

**Acceptance Scenarios**:

1. **Given** the learner has completed episode 1 of a show in the current practice language, **When**
   they choose that show, **Then** the setup screen offers "Episode 2" as its primary action and shows
   the same hosts (name, personality, voice) as episode 1.
2. **Given** a series episode has started, **When** the first host line is spoken, **Then** the host
   addresses the learner by the name the hosts call them (if one is set) and acknowledges that this is a
   continuing show.
3. **Given** a previous episode in which the learner shared something about themselves, **When** the
   next episode runs, **Then** at least one host line within the episode refers back to a specific point
   from an earlier episode, and the hosts do not repeat an earlier episode's topic.
4. **Given** a series in Spanish with Hugo as host, **When** the learner switches the practice language
   to German and opens the same show, **Then** it starts the German series of that show (episode 1 if
   none yet), with hosts whose names suit German; the Spanish series and its hosts are unchanged.
5. **Given** a series episode left unfinished, **When** the learner opens the show, **Then** they are
   offered to continue the unfinished episode before starting a new one.

---

### User Story 2 - Learner chooses a quick one-off episode instead (Priority: P1)

Some days the learner just wants a regular podcast for quick practice. From the same show, they choose
a one-off episode: hosts are cast as today, can be shuffled freely, and the episode neither uses nor
adds to the series' history.

**Why this priority**: The learner named two use cases. Making series the only way to listen would
break the quick-practice case that exists today, so the two must sit side by side from the start.

**Independent Test**: With a show that has a series in progress, start a one-off episode. Verify it is
labelled one-off, the hosts make no reference to earlier episodes, and afterwards the series' episode
count and memory are unchanged.

**Acceptance Scenarios**:

1. **Given** any show, **When** the learner opens it, **Then** they can start either the next series
   episode or a one-off episode, and the setup screen says which one they are starting.
2. **Given** a one-off episode, **When** it runs, **Then** no host line refers to earlier episodes or
   to what the learner said in them.
3. **Given** a one-off episode has finished, **When** the learner returns to the show, **Then** the
   series' next episode number and its remembered points are the same as before the one-off.
4. **Given** a one-off episode, **When** the learner shuffles a host or changes a personality, **Then**
   the change applies to that episode only, as today.

---

### User Story 3 - Hosts stay consistent unless the learner deliberately changes them (Priority: P1)

Once a series has started, its hosts are that show's people. The setup screen for a series episode
shows them without a casual Shuffle. If the learner really wants someone different, they can recast a
host on purpose; they are told plainly that the new host will not know the history, and the change
sticks for later episodes.

**Why this priority**: "A more consistent persona" is the learner's explicit request. Without it, a
single click on Shuffle would quietly replace Hugo and break the relationship the series is built on.

**Independent Test**: Start episode 2 of a series and verify there is no one-click Shuffle; recast one
host through the explicit action, confirm the notice, and verify episode 3 keeps the new host while the
other host and the episode count are unchanged.

**Acceptance Scenarios**:

1. **Given** a series with at least one episode, **When** the learner opens its next episode's setup,
   **Then** each host shows name, personality and a voice sample, and no one-click Shuffle is offered.
2. **Given** the learner chooses to recast a series host, **When** they are asked to confirm, **Then**
   the message says the new host joins without the earlier history; confirming applies the new host to
   this and every later episode; cancelling changes nothing.
3. **Given** a host has been recast, **When** the next episode runs, **Then** the other host still
   remembers the earlier episodes and the new host is introduced as new to the show.
4. **Given** a ready-made show that has never been played in this language, **When** the learner
   opens it, **Then** its hosts are the same names and personalities shown on its card, every time,
   until the first series episode is played.

---

### User Story 4 - Learner keeps favourite shows at the top (Priority: P2)

The learner marks Big Little Questions and Game Day as favourites. The Podcasts screen now shows a
**My shows** group first: favourites and shows with a series in progress, each with the next episode
number, so continuing takes one choice. Shows the learner made themselves (from an idea or Surprise
me) and played appear here too and can be favourited like ready-made ones.

**Why this priority**: Favourites make the series quick to get back to, but series continuity (US1)
already works without them by choosing the show from the full list.

**Independent Test**: Favourite a ready-made show and a generated show that has an episode; reload the
app. Verify both appear in My shows with their next episode numbers, that unfavouriting removes a show
from the group unless it has a series in progress, and that the ready-made list is unchanged.

**Acceptance Scenarios**:

1. **Given** any show card, **When** the learner marks it as a favourite, **Then** it appears in My
   shows, the mark is visible and announced to assistive technology, and it persists across restarts.
2. **Given** a show with a series in progress, **When** the learner opens Podcasts, **Then** it appears
   in My shows with the next episode number even if it is not a favourite.
3. **Given** a generated or surprise show from which the learner played an episode, **When** they open
   Podcasts, **Then** it appears in My shows and its next episode keeps the same hosts.
4. **Given** the learner has no favourites and no series, **When** they open Podcasts, **Then** My
   shows is not shown and the screen looks as it does today.

---

### User Story 5 - Learner finds a new show when they want something different (Priority: P2)

The ready-made list is the same every visit, which the learner likes. When they want something new,
they choose **Find a new show**. They get a small set of fresh show suggestions, shaped by their saved
interests and different from the shows they already have. They can start one, favourite it, or ask for
another set. The ready-made list itself never changes.

**Why this priority**: It answers "if they want something new" without giving up the stable list. It
depends on shows being keepable (US4) to be fully useful, so it comes after.

**Independent Test**: With interests saved, choose Find a new show twice. Verify each set contains
shows not already in My shows or the ready-made list, that the second set differs from the first, that
starting one opens setup as for any show, and that the ready-made list is the same before and after.

**Acceptance Scenarios**:

1. **Given** the Podcasts screen, **When** the learner chooses Find a new show, **Then** they see a
   small set of new shows, each with title, topic, premise and hosts, as on a show card.
2. **Given** a set of suggestions, **When** the learner asks for another set, **Then** the new set
   does not repeat a show from the previous set or from the learner's own shows.
3. **Given** a suggestion, **When** the learner favourites it or plays an episode, **Then** it is kept
   as one of their shows; suggestions they ignore are not kept.
4. **Given** saved interests, **When** suggestions are made, **Then** most of them relate to those
   interests; with no interests, they cover varied everyday topics.
5. **Given** the conversation partner cannot be reached, **When** the learner asks for new shows,
   **Then** they see a plain message with what to do, and the rest of the screen still works.

---

### User Story 6 - The personality drop-down matches the theme when open (Priority: P2)

On the setup screen, the learner opens a host's personality drop-down in dark mode. The open list of
options (Enthusiast, Expert, Contrarian, …) uses the same colours as the rest of the app, with the
current choice and the focused option clearly marked.

**Why this priority**: It is a small visual defect, independent of the series work, and quick to fix;
it does not block any journey but is visible on every podcast setup.

**Independent Test**: In light mode, dark mode and the system setting, open each drop-down on the
podcast setup screen and verify the options' background and text use the app theme with readable
contrast, and the selected and focused options are distinguishable.

**Acceptance Scenarios**:

1. **Given** dark mode, **When** the learner opens a personality drop-down, **Then** the options are
   drawn on the theme's surface colour with the theme's text colour, not the browser's default light
   list.
2. **Given** light mode, **When** the same drop-down is opened, **Then** it matches the light theme.
3. **Given** keyboard navigation, **When** the learner moves through the options, **Then** the focused
   option is visibly distinct from the others with readable contrast.
4. **Given** the other drop-downs in the app, **When** they are opened in either theme, **Then** they
   look consistent with the podcast drop-down.

---

### Edge Cases

- **A series host's voice is no longer installed**: the series keeps the host's name and personality.
  The learner is told plainly that this host's voice is missing and what to do, as today; the episode
  can run as text. The host is never silently given another voice.
- **The learner changes the name the hosts call them**: later episodes use the new name; hosts do not
  argue about it.
- **The learner's own name now clashes with a host's name**: the host keeps their name, and the setup
  screen points out the clash so the learner can choose another name to be called.
- **A series becomes long**: what hosts remember stays short — the most useful points across all
  episodes, not a full transcript — so episodes start as quickly as episode 1 did.
- **A previous episode was abandoned after a few lines**: it still counts as an episode of the series,
  and anything worth remembering from it is kept.
- **An episode is deleted from Past Chats**: the series' remembered points drawn only from that
  episode are forgotten, and the episode count reflects the remaining episodes.
- **Format differs between episodes**: a series can move between One host, Panel and Listen. Hosts not
  in a given episode (the second host in One host) keep their place for later episodes.
- **Listen episodes**: the learner does not speak, so hosts remember what was discussed but nothing
  new about the learner.
- **Provider changed between episodes**: the series carries on with the new provider; hosts, names and
  memory do not depend on which provider wrote earlier episodes.
- **Find a new show returns an unsuitable or duplicate idea**: it is dropped, as with today's generator,
  and never shown.
- **A ready-made show is favourited in one language**: favourites apply to the show in every language;
  series (episodes, hosts, memory) are per language.
- **Starting over**: the learner can reset a series, which clears its episode count and memory for
  that language after a confirmation; past episodes stay in Past Chats.

## Requirements *(mandatory)*

### Functional Requirements

**Series and continuity**

- **FR-001**: Every show — ready-made, generated or surprise — MUST be able to have a series per
  practice language: an ordered set of episodes with the same hosts.
- **FR-002**: Choosing a show MUST offer the next series episode, labelled with its episode number, as
  the primary action, and a one-off episode as a secondary action. When a series episode is unfinished,
  continuing it MUST be offered first.
- **FR-003**: A series episode MUST use the series' hosts: the same name, personality and voice as the
  previous episode, unless the learner recast a host (FR-009).
- **FR-004**: The system MUST keep, per series, a short record of what is worth remembering: topics
  covered, and things the learner shared about themselves (likes, plans, experiences, opinions).
- **FR-005**: In a series episode, the hosts MUST acknowledge the show is continuing, MUST be able to
  refer back to remembered points, and MUST choose a topic not already covered in that series.
- **FR-006**: The remembered record MUST stay bounded in size regardless of the number of episodes, so
  starting a later episode does not take noticeably longer than starting the first.
- **FR-007**: A one-off episode MUST NOT read from or add to any series' record or episode count, and
  hosts in it MUST NOT refer to earlier episodes.

**Consistent hosts**

- **FR-008**: The setup screen for a series episode after the first MUST show the hosts without a
  one-click Shuffle; one-off episodes and a series' first episode keep today's Shuffle and personality
  choice.
- **FR-009**: Learners MUST be able to recast a series host through an explicit action with a
  confirmation stating that the new host will not share the earlier history. The new host MUST apply to
  that and all later episodes; the other host MUST be unaffected.
- **FR-010**: A ready-made show's default hosts MUST be the same, for a given language, every time the
  show is shown or opened, until its first series episode fixes them.
- **FR-011**: Learners MUST be able to see, for a series, the episode count and the points the hosts
  remember, and to reset the series after a confirmation. Resetting MUST NOT delete past episodes.

**My shows and favourites**

- **FR-012**: Learners MUST be able to mark and unmark any show as a favourite; favourites MUST persist
  across restarts.
- **FR-013**: The Podcasts screen MUST show a "My shows" group above the ready-made list, containing
  favourites and shows with a series in progress in the current practice language, each with its next
  episode number. The group MUST be hidden when empty.
- **FR-014**: A generated or surprise show MUST be kept as one of the learner's shows once it is
  favourited or an episode of it is played, and MUST be startable again with the same title, premise and
  hosts.
- **FR-015**: The ready-made show list MUST stay the same, in the same order, on every visit.

**Find a new show**

- **FR-016**: Learners MUST be able to ask for a set of new show suggestions (at least three) from the
  Podcasts screen, and to ask for another set.
- **FR-017**: Suggestions MUST NOT duplicate a ready-made show, one of the learner's shows, or a show in
  the previous set, and MUST favour the learner's saved interests when there are any.
- **FR-018**: Suggestions MUST pass the same suitability rules as today's generator, and unsuitable ones
  MUST NOT be shown.
- **FR-019**: A suggestion MUST be kept only when the learner favourites it or plays an episode; others
  are discarded.
- **FR-020**: When suggestions cannot be made, the learner MUST see a plain message saying what
  happened and what to do; the app MUST NOT silently fall back to another provider.

**Theme**

- **FR-021**: Every drop-down in the app, and the podcast personality drop-down in particular, MUST
  draw its open list of options in the current theme's colours (light, dark, or the system setting),
  with the selected and focused options distinguishable and text contrast of at least 4.5:1.

**Compatibility**

- **FR-022**: Episodes recorded before this feature MUST keep working and appear in Past Chats as
  today, but MUST NOT belong to any series: every show starts a fresh series, whose first episode is
  numbered 1, after this change.
- **FR-023**: Series MUST work with every conversation-partner provider the learner can select, and
  with every practice language, without per-language changes beyond the existing language data.

### Key Entities *(include if feature involves data)*

- **Show**: what the learner can listen to — title, premise, topic, the learner's role and default
  host personalities. Ready-made shows are fixed; generated, surprise and suggested shows become the
  learner's own once kept.
- **Series**: one show in one practice language for this learner — its episode count, its hosts and its
  remembered points. Created by the first series episode; reset on request.
- **Series host**: a host belonging to a series — slot (lead or second), name, personality, voice, and
  whether they joined after earlier episodes (recast).
- **Remembered point**: one short thing worth recalling — a topic covered or something the learner
  shared — with the episode it came from.
- **Episode**: as in 007, plus whether it is a series episode (and its number) or a one-off.
- **Favourite**: a mark on a show that keeps it in My shows, across languages.
- **Show suggestion**: an unsaved show offered by Find a new show; becomes a Show when kept.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across consecutive episodes of a series, 100% of episodes use the same host names,
  personalities and voices as the previous episode, except where the learner recast a host.
- **SC-002**: In a review of at least 20 second-or-later series episodes on the default local setup,
  at least 80% contain a host line that correctly refers to a specific point from an earlier episode,
  and none presents an invented memory as fact.
- **SC-003**: In the same review, at least 90% of series episodes choose a topic not already covered in
  that series.
- **SC-004**: In a review of at least 20 one-off episodes of shows with a series in progress, 0 host
  lines refer to earlier episodes.
- **SC-005**: From opening the Podcasts screen, the learner can start the next episode of a favourite
  show in at most two choices.
- **SC-006**: The first host line of episode 10 of a series arrives within 20% of the time taken by
  episode 1's first line on the same setup.
- **SC-007**: Each Find a new show request shows at least three suitable suggestions, none a duplicate
  of a show the learner can already see, or a plain message, within 30 seconds on the default local
  setup.
- **SC-008**: Every drop-down's open option list passes a 4.5:1 text contrast check in light and dark
  themes, verified by the manual accessibility check.
- **SC-009**: All episodes, conversations, vocabulary and settings that existed before the change are
  still present and usable afterwards.

## Assumptions

- **The series is the main way into a show; one-off stays one choice away.** This keeps the
  relationship use case front and centre without removing quick practice.
- **Memory is about the learner and the show, not a transcript.** Hosts remember a few points, not
  everything; the learner can see and reset them. All of it stays on the learner's machine like the
  rest of their data, and goes to the conversation partner only as today's episode context does (so a
  cloud provider, when selected, receives it under the existing notice).
- **Series are per language, favourites are not.** Hosts are cast per language (names suit the
  language), so Hugo in Spanish and his German counterpart are different series of the same show.
- **The ready-made list is not expanded by this feature.** New variety comes from Find a new show,
  keeping the original list stable as the learner asked.
- **Find a new show uses the conversation partner,** like today's generator and Surprise me, so its
  quality and speed follow the selected provider; the default local model may give plainer ideas.
- **Episode-to-episode recall is model-dependent.** As with levels and corrections, the default local
  model may recall less reliably than a larger one; SC-002 measures this and may lead to an
  experimental label, as earlier features did.
- **No scheduling or notifications.** "Long-running" means the show continues when the learner comes
  back, not that new episodes are released on a timetable.
- **The drop-down fix is visual only;** the personality options and their rules (two hosts never share
  a personality) are unchanged.
