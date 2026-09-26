# Feature Specification: Conversation Difficulty Level

**Feature Branch**: `005-conversation-difficulty-level`
**Created**: 2026-09-26
**Status**: Draft
**Input**: User description: "Add a feature to modify the output of the model I'm working with. I'm a beginner in Spanish — not a super beginner, I've used apps for a couple of years — and I'd like to be able to have a simple conversation. That probably means tweaking a level for how advanced the conversation should be (what those levels are is worth researching). The person talking could still ask an advanced question anyway. The easy end should feel like speaking to a Spanish child, and it should go up to regular, unbounded, day-to-day speech as an option."

## Clarifications

### Session 2026-09-26

- Q: Where can the learner change the level: only on the Settings screen, also from a control on
  the conversation screen, or chosen per conversation at the start? → A: On the Settings screen and
  from a small control on the conversation screen. Both change the same learner-wide setting.
- Q: Should lower levels also slow down spoken playback? → A: No. The level changes the words only,
  and speaking speed stays governed by the chosen voice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner holds a conversation they can actually follow (Priority: P1)

A learner who has used language apps for a couple of years opens a scenario conversation. At
present the conversation partner answers the way a native adult would: long sentences, a mix of
tenses, idioms and less common words. The learner spends more time translating than talking. They
set the conversation level to **Elementary**. From then on the partner speaks in short, clear
sentences built from everyday words and a few basic tenses, so the learner can answer without
leaving the conversation to look things up. Later they set it to **Natural** and the partner speaks
as it does today.

**Why this priority**: This is the whole feature. A level the partner honours in its replies is
useful on its own, even before the level reaches any other part of the app.

**Independent Test**: Run the same scenario at Beginner and at Natural and send the same learner
messages. The Beginner replies should be clearly shorter and simpler (sentence length, tenses,
vocabulary; see FR-003), and the Natural replies should match what the app produces today.

**Acceptance Scenarios**:

1. **Given** the level is Beginner, **When** the partner opens a new scenario conversation,
   **Then** the opening message follows the Beginner rules: at most two short sentences, present
   tense only, everyday words, and one easy question for the learner.
2. **Given** the level is Elementary, **When** the learner sends a simple message, **Then** the
   reply stays within the Elementary rules and still moves the scenario forward in character.
3. **Given** the level is Natural, **When** the partner replies, **Then** no complexity limits
   apply and the reply reads like ordinary everyday native speech.
4. **Given** any level, **When** the partner replies, **Then** the reply is still entirely in the
   target language. Simplifying never introduces the learner's native language.

---

### User Story 2 - Learner steps the level down (or up) when a conversation gets hard (Priority: P2)

The learner is partway through a conversation at Intermediate and gets lost. Without leaving the
conversation screen, they use the level control there to lower the level to Elementary. The partner's very next reply is simpler. The conversation does not restart, its
history is kept, and the character and scenario stay the same. When things feel easy again, they
raise the level and the next reply follows the higher level.

**Why this priority**: Learners misjudge their own level, and the right level changes from topic to
topic. Adjusting without losing the conversation is what keeps the setting useful after the first
day. It builds on Story 1.

**Independent Test**: Start a conversation at Intermediate, exchange two turns, change the level to
Beginner, send another message, and confirm that the next reply follows the Beginner rules, that
earlier messages are unchanged, and that the conversation continues.

**Acceptance Scenarios**:

1. **Given** a conversation in progress at Intermediate, **When** the learner changes the level to
   Beginner from the conversation screen and sends a message, **Then** the next reply follows the
   Beginner rules and refers naturally to what was said before.
2. **Given** a conversation in progress, **When** the level changes, **Then** replies already shown
   are left as they were and nothing restarts.
3. **Given** a saved conversation started at one level, **When** the learner reopens it after the
   level was changed, **Then** new replies follow the current level.
4. **Given** the learner changed the level from the conversation screen, **When** they open the
   Settings screen, **Then** it shows the same level, and a change made on Settings likewise shows
   on the conversation screen.

---

### User Story 3 - Learner aids speak at the same level (Priority: P3)

Besides the partner's replies, the app writes target-language text for the learner to read or say:
suggested replies, alternative phrasings of the learner's own sentence, and the expression helper's
"how do I say…" answers. At Beginner, a suggested reply built from advanced grammar is as unhelpful
as an advanced partner reply. With this story, those aids follow the same level.

**Why this priority**: It keeps the experience consistent, but the aids are used less often than the
conversation itself, and Stories 1 and 2 are valuable without it.

**Independent Test**: At Beginner, request reply suggestions, alternative phrasings, and a helper
answer, and confirm that every piece of target-language text follows the Beginner rules.

**Acceptance Scenarios**:

1. **Given** the level is Beginner, **When** the learner asks for reply suggestions, **Then** every
   suggestion follows the Beginner rules.
2. **Given** the level is Elementary, **When** the learner asks the expression helper how to say
   something, **Then** the target-language phrase it offers follows the Elementary rules, choosing a
   simpler way to express the idea over a more precise but advanced one.
3. **Given** any level, **When** the learner asks for a grammar explanation, a translation or a word
   lookup, **Then** the output is unchanged by the level (those are written in the learner's native
   language).

---

### Edge Cases

- **The learner writes above the level**: the learner asks something complex or uses advanced
  grammar at Beginner. The partner understands and answers the question, but its own reply stays at
  Beginner. A learner writing well above the level never raises the level of the partner's replies.
  The partner may repeat back a word the learner has just used even when that word is above the
  level, because the learner already knows it.
- **The learner asks for simpler speech in the conversation**: the learner says the equivalent of
  "simpler, please" or "I don't understand". The partner simplifies further for that reply. The level
  is a ceiling, not a target: the partner may always speak more simply than the level allows, and
  never more complexly.
- **The scenario needs specialist words**: a doctor's visit or a bank scenario cannot avoid a few
  topic words (for example *receta* or *cuenta*) even at Beginner. The partner may use the few words
  that are essential to the scenario and keeps everything else at the level.
- **A custom scenario asks for complex speech**: a custom prompt such as "a university professor
  lecturing on history" describes a character who would naturally speak formally. The level wins,
  and the character keeps its role and personality while speaking within the level.
- **Interaction with correction mode**: the level does not change what counts as a grammar error in
  the learner's message. In Gentle mode the partner's restatement of the corrected form follows the
  level. Strict-mode correction notes are unaffected, since they explain in the native language.
- **Switching conversation partners**: the level applies in the same way whichever conversation
  partner (local or cloud) is selected, and switching partners keeps the level.
- **Changing the level while a reply is being written**: the reply already in progress finishes at
  the level it started with, and the new level applies from the next reply.
- **Target languages other than Spanish**: the levels are defined by features that every language
  has (sentence length, tense and mood range, vocabulary frequency, idioms), so they apply to any
  target language the app supports. Spanish is the reference example.

## Requirements *(mandatory)*

### Functional Requirements

**The levels**

- **FR-001**: The system MUST offer four conversation levels, ordered from easiest to hardest:
  **Beginner**, **Elementary**, **Intermediate** and **Natural**.
- **FR-002**: Each level MUST be presented to the learner with its name, a one-sentence
  plain-language description, and its approximate equivalent on the Common European Framework of
  Reference for Languages (CEFR), the standard scale that most courses and apps use: Beginner ≈ A1,
  Elementary ≈ A2, Intermediate ≈ B1, Natural = no limit.
- **FR-003**: Each level below Natural MUST limit the partner's replies as follows. Spanish examples
  illustrate each point; the limits themselves apply to any language:

  | Characteristic | Beginner (≈ A1) | Elementary (≈ A2) | Intermediate (≈ B1) | Natural |
  |---|---|---|---|---|
  | Feels like | Talking to a young child or to a visitor who is just starting | Talking to a patient friend | Talking to a clear, considerate adult | Ordinary everyday native speech |
  | Reply length | 1–2 sentences | 2–3 sentences | Up to 4 sentences | No limit |
  | Sentence length | Short, one idea per sentence (typically ≤ 8 words) | Short, joined only by simple connectors such as *y*, *pero* and *porque* (typically ≤ 12 words) | Connected sentences with at most one subordinate clause (typically ≤ 20 words) | No limit |
  | Tenses and moods | Present tense only | Present, the most common past tense (*preterite*) and the near future (*voy a…*) | All common indicative tenses; subjunctive only in fixed everyday phrases (*ojalá*, *quiero que…*) | No limit |
  | Vocabulary | The most common everyday words (roughly the top 500) | Common words about everyday life (roughly the top 1,500) | Topic-appropriate words; avoids rare or literary ones (roughly the top 3,000) | No limit |
  | Idioms and slang | None | None | Common, widely understood idioms only | Any, including slang and regional expressions |
  | Questions to the learner | One easy question per reply, often yes/no or either/or | One simple open question per reply | Open questions as the conversation needs | No limit |

- **FR-004**: At the **Natural** level the system MUST NOT limit the partner's replies in any way.
  Replies at Natural MUST be equivalent to the app's current behaviour.
- **FR-005**: A level MUST act as a ceiling, not a target. The partner MAY speak more simply than the
  level allows and MUST NOT speak more complexly (FR-012 is the only exception).

**Choosing and changing the level**

- **FR-006**: The learner MUST be able to choose the level in two places: the Settings screen,
  and a level control on the conversation screen. Both MUST read and change the same single
  learner-wide setting, so a change made in one place is shown in the other.
- **FR-007**: The chosen level MUST be saved and MUST still apply after the app is closed and
  reopened.
- **FR-008**: A change of level MUST take effect from the partner's next reply, without restarting
  the conversation, losing history, or restarting the app. This MUST hold even when a conversation is
  already in progress with the partner active.
- **FR-009**: When no level has ever been chosen, the level MUST be **Natural**, so that existing
  learners see no change in behaviour until they choose a level.
- **FR-010**: The conversation-screen level control MUST show the level currently in effect and
  MUST be visually secondary to sending a message, which stays the screen's single primary action.
  Changing the level there MUST NOT open another screen or interrupt the conversation, and MUST be
  confirmed immediately by the control showing the new level.

**How the level applies**

- **FR-011**: The level MUST apply to every reply the conversation partner writes in the target
  language, including the opening message, in scenario conversations and in custom-prompt
  conversations alike.
- **FR-012**: The partner MAY use a small number of words above the level only when (a) they are
  essential to the scenario's topic, or (b) the learner has just used them. All other text in the
  reply MUST stay within the level.
- **FR-013**: The level of the learner's own messages MUST NOT raise the level of the partner's
  replies. The partner MUST still respond to the substance of what the learner said.
- **FR-014**: When the learner asks in the conversation for simpler speech, the partner MUST simplify
  that reply further, within the current level.
- **FR-015**: The level MUST NOT weaken the existing rule that the partner writes only in the target
  language. At every level, including Beginner, replies MUST contain no words of the learner's native
  language.
- **FR-016**: The level MUST apply in the same way whichever conversation partner is selected, and
  MUST be kept when the learner switches partners.
- **FR-017**: The level MUST also apply to target-language text the app generates for the learner:
  reply suggestions, alternative phrasings of the learner's message, and the expression helper's
  suggested phrase.
- **FR-018**: The level MUST NOT change native-language outputs (grammar explanations, translations,
  word lookups), nor what the correction feature treats as an error. In Gentle correction mode, the
  partner's restatement of the corrected form MUST follow the level.
- **FR-019**: The level MUST change only the words of the partner's replies. It MUST NOT change how
  fast replies are spoken aloud, which stays governed by the chosen voice.

### Key Entities *(include if feature involves data)*

- **Conversation Level**: one of four fixed, ordered difficulty levels. Attributes: name, position in
  the order, plain-language description, approximate CEFR equivalent, and the limits in FR-003. The
  set of levels is fixed. Learners cannot define their own.
- **Learner Settings** (existing): gains the chosen conversation level. It is a single value that
  applies to all conversations and is kept between app sessions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

Levels are checked against a fixed evaluation set of at least 20 learner turns spread across at
least 4 scenarios, using the app's default local conversation partner. The checks must pass on the
default local partner, not only on a larger optional one.

- **SC-001**: At Beginner, at least 90% of partner replies in the evaluation set meet all of the
  Beginner limits for length, sentence length and tense.
- **SC-002**: At Elementary and at Intermediate, at least 85% of partner replies meet all of their
  level's limits for length, sentence length and tense.
- **SC-003**: Replies get measurably harder at each step up: average sentence length, and the share
  of words outside the most common 1,500, both rise from Beginner to Elementary to Intermediate to
  Natural.
- **SC-004**: 100% of partner replies at every level contain no words of the learner's native
  language (unchanged from today).
- **SC-005**: A level change is reflected in the very next partner reply in 100% of attempts, with no
  restart and no lost history.
- **SC-006**: From the conversation screen, a learner can change the level in at most two
  interactions and under 5 seconds, without leaving the conversation.
- **SC-007**: For the same learner and scenario, the learner asks for a translation of a partner
  reply at least 50% less often at Beginner than at Natural.
- **SC-008**: Choosing a level adds no perceptible delay: the first words of a reply appear within
  10% of the time they take at Natural under the same conditions.

## Assumptions

- **Level scheme**: the four levels follow the CEFR, the most widely used scale for language
  ability, but are simplified. A1 through B1 each get their own level, and B2 through C2 fall under
  Natural, because a learner at B2 and above can generally follow ordinary native speech, which is
  what the user described as the top option. Four choices keep the control simple (Constitution
  Principle IV). The word-count, tense and vocabulary figures in FR-003 are working targets drawn
  from common CEFR descriptors and graded-reader practice. Planning may tune them against the
  evaluation set, but the level order and the kind of limit each level sets are fixed.
- **Recommended starting point for the requesting learner**: a learner with a couple of years of app
  practice is typically around A2, so Elementary is the expected first choice. The app does not
  assess or recommend a level automatically; the learner chooses.
- **One setting for everything**: the level is a single learner-wide setting, as with the correction
  mode. It is not chosen per scenario or stored per conversation.
- **No automatic adjustment**: the app does not raise or lower the level based on how the learner is
  doing. Adaptive levelling would be a separate feature.
- **Best effort at the limits**: the partner is a language model, so the limits are strong
  instructions rather than guarantees. Occasional overshoots are expected and are why the success
  criteria use thresholds of 85–90% rather than 100%. The one exception is the no-native-language
  rule (SC-004), which is already held to 100%. If the default local partner cannot meet SC-001 and
  SC-002, the feature ships marked experimental, as correction mode did, rather than with the
  thresholds lowered.
- **Out of scope**: flashcard content, scenario descriptions and titles, the interface language, and
  spoken playback speed are not affected by the level. A separate speed control could be a later
  feature.
