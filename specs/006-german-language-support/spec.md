# Feature Specification: German Language Support

**Feature Branch**: `006-german-language-support`
**Created**: 2026-09-26
**Status**: Draft
**Input**: User description: "Now let's expand the program. On top of Spanish, I want the ability to choose German. This can be configured in the settings as well. So most everything stays the same about the program, except there's an option to choose another language to have a conversation in. That language, for now will be German"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner practises a conversation in German (Priority: P1)

A learner who has been practising Spanish also wants to practise German. They open Settings, change
the practice language from **Spanish** to **German**, and save. Back on the home screen they pick a
scenario, such as *Order at a Restaurant*, and the conversation partner greets them in German. They
answer by typing or speaking German, and the partner replies in German, in character. The partner's
replies are read aloud in a German voice. Everything else works as it does in Spanish: the same
scenarios, custom prompts, suggestions, translation, alternative phrasing, word lookup, the
expression helper, corrections and conversation levels.

**Why this priority**: This is the feature. A German conversation that works end to end, in text
and in speech, is useful on its own, before flashcards or history know anything about languages.

**Independent Test**: Set the practice language to German, start any scenario, exchange five
messages (typed and spoken), and use each learning tool once. Every partner reply is in German, is
spoken in a German voice, and each tool gives German-aware results with explanations in English.

**Acceptance Scenarios**:

1. **Given** the practice language is German, **When** the learner starts a scenario conversation,
   **Then** the partner's opening message is entirely in German.
2. **Given** a German conversation, **When** the learner speaks a German sentence, **Then** it is
   transcribed as German, including ä, ö, ü and ß, and sent as the learner's message.
3. **Given** a German conversation, **When** the partner replies, **Then** the reply is played in a
   German voice.
4. **Given** a German conversation, **When** the learner asks for a translation, an alternative
   phrasing, a word lookup, a suggestion or help from the expression helper, **Then** the
   German-side text is German and any explanation is in English.
5. **Given** a German conversation with corrections on, **When** the learner writes a sentence with
   a German grammar mistake, **Then** the correction treats it as German. It judges the sentence by
   German grammar and does not compare it to Spanish.
6. **Given** a German conversation at a level below Natural, **When** the partner replies, **Then**
   the reply follows that level's limits, as it would in Spanish.
7. **Given** the learner writes entirely in English, **When** the partner replies, **Then** the
   partner asks them, in German, to use German.

---

### User Story 2 - Learner switches between Spanish and German without losing anything (Priority: P1)

The learner practises both languages on alternating days. When they switch the practice language,
nothing they did in the other language is lost or changed. Their past Spanish conversations stay in
Past Chats, labelled Spanish, and can still be continued in Spanish. Their Spanish voice choice is
remembered, so it is back when they switch back to Spanish.

**Why this priority**: The learner already has Spanish history, vocabulary and settings. If adding
German damaged any of that, the feature would be a regression. This carries the same weight as
Story 1.

**Independent Test**: With existing Spanish data, switch to German, hold a German conversation,
switch back to Spanish and continue an older Spanish conversation. All Spanish data is unchanged,
and the continued conversation stays in Spanish with a Spanish voice.

**Acceptance Scenarios**:

1. **Given** an existing install with Spanish data, **When** the app is updated to this version,
   **Then** the practice language is Spanish and all conversations, vocabulary, decks, practice
   history and settings are unchanged.
2. **Given** the practice language is German, **When** the learner opens a Spanish conversation from
   Past Chats and continues it, **Then** the partner keeps replying in Spanish, the replies play in a
   Spanish voice, and speech is transcribed as Spanish.
3. **Given** a conversation is open, **When** the learner changes the practice language in Settings,
   **Then** that conversation keeps its own language. Only conversations started afterwards use the
   new language.
4. **Given** the learner picked a particular Spanish voice, **When** they switch to German and then
   back to Spanish, **Then** their Spanish voice is selected again.
5. **Given** Past Chats contains conversations in both languages, **When** the learner views the
   list, **Then** each conversation shows which language it is in.

---

### User Story 3 - Learner studies German vocabulary with flashcards (Priority: P2)

While chatting in German, the learner saves words they did not know. On the Flashcards screen, with
German selected, they see only their German words, decks and practice statistics. They generate a
deck, practise it, and hear each word in a German voice. When they switch back to Spanish, the
Flashcards screen shows only their Spanish words again.

**Why this priority**: Flashcards turn conversation practice into retained vocabulary, but a German
conversation is useful without them. Mixing languages in one practice deck would be confusing,
which is why the flashcard screens must follow the practice language.

**Independent Test**: Save three German words from a German conversation. With German selected,
generate a deck and practise it: only those words appear, with German audio and word details. Switch
to Spanish: only Spanish words, decks and statistics appear.

**Acceptance Scenarios**:

1. **Given** a German conversation, **When** the learner saves a word, **Then** it is saved as a
   German word.
2. **Given** the practice language is German, **When** the learner opens the word list, decks,
   practice or analytics, **Then** only German words and German decks appear, and the statistics
   count only German practice.
3. **Given** the practice language is German, **When** the learner generates a deck, **Then** the
   deck draws only on German words and belongs to German.
4. **Given** a German flashcard, **When** the learner plays its audio or opens its word details
   (meanings, usage, phrases, similar words), **Then** the audio uses a German voice and the details
   describe the German word, written in English.
5. **Given** the same spelling is saved in both languages, **When** the learner views either one,
   **Then** they are separate words with separate progress and details.

---

### User Story 4 - Learner chooses a German voice (Priority: P3)

In Settings, with German selected, the voice list offers only German voices. The learner can hear
the choice reflected in the next reply.

**Why this priority**: A sensible default German voice is enough for Stories 1–3. Choosing among
several voices is a refinement.

**Independent Test**: Select German in Settings. The voice list shows only German voices, one of them
already selected, and the chosen voice is used for the next partner reply.

**Acceptance Scenarios**:

1. **Given** the learner selects German in Settings, **When** they look at the voice list, **Then**
   it lists only German voices and one is already selected.
2. **Given** German is selected, **When** the learner picks a different German voice and saves,
   **Then** later German replies and flashcards use that voice.

---

### Edge Cases

- **German voice not installed or unusable**: German text conversations still work. Where speech
  would play, the learner sees a plain message saying the German voice is unavailable and what to do.
  The app never reads German text with a Spanish voice.
- **Language changed during a flashcard session**: the session in progress finishes in its own
  language. The change applies when the learner next opens a Flashcards screen.
- **Existing decks and practice history**: they were all built from Spanish words, so they belong to
  Spanish.
- **German typing**: the learner can type ä, ö, ü and ß (and their capitals), and word lookup, saving
  and flashcards keep them exactly as typed.
- **German noun capitalisation**: a capitalised German noun is not treated as a mistake or as a
  different word from its correct capitalised form.
- **Regional German**: corrections do not flag words or constructions that are standard in Austria
  or Switzerland as errors, in the same way Spanish corrections accept regional variants.
- **Learner speaks the other language**: in a German conversation, Spanish speech is transcribed as
  German as far as possible, not switched silently to Spanish. The partner answers in German.
- **Level and correction warnings**: the experimental warnings on conversation levels and
  corrections still show when German is selected, because the same model limits apply.
- **Chat header**: the conversation screen shows the conversation's language but offers no control to
  change it. A conversation's language is fixed when it starts.

## Requirements *(mandatory)*

### Functional Requirements

**Choosing the language**

- **FR-001**: The system MUST offer a practice language with two options, **Spanish** and
  **German**. Spanish is the default.
- **FR-002**: Learners MUST be able to change the practice language on the Settings screen. The
  change takes effect for new conversations and the flashcard screens without restarting the app.
- **FR-003**: The practice language MUST be a single learner-wide setting that is saved and kept
  between sessions.
- **FR-004**: The home screen MUST show which practice language new conversations will use.
- **FR-005**: The set of available languages MUST be defined in one place, so a later language can
  be added without changing the features that use it.

**Conversations**

- **FR-006**: A new conversation, whether from a scenario or a custom prompt, MUST use the practice
  language that is selected when it starts, and keep that language for its whole life.
- **FR-007**: All scenarios MUST be available in every practice language. The partner plays the
  scenario in the conversation's language.
- **FR-008**: Every conversation feature available in Spanish MUST work in German: the partner's
  replies, reply suggestions, translation, alternative phrasing, word lookup, the expression helper,
  corrections (Off, Gentle and Strict), conversation levels and conversation titles.
- **FR-009**: Every learning aid MUST use the conversation's own language, not the currently selected
  practice language. This matters when a learner continues an older conversation in the other
  language.
- **FR-010**: Explanations, translations and help text MUST stay in English (the learner's native
  language), whichever practice language is in use.
- **FR-011**: The app's interface MUST stay in English. Only the conversation content changes
  language. Labels that name the practice language (for example "English → German" in the expression
  helper) MUST name the conversation's language.
- **FR-012**: Past Chats MUST show the language of each conversation.

**Speech**

- **FR-013**: Speech from the learner MUST be transcribed in the conversation's language.
- **FR-014**: Partner replies and flashcard audio MUST be spoken in a voice for the language of the
  text being spoken.
- **FR-015**: The voice list in Settings MUST show only voices for the selected practice language.
- **FR-016**: The system MUST remember the learner's voice choice separately for each language. A
  language the learner has never chosen a voice for uses that language's default voice.
- **FR-017**: At least one German voice MUST be available, and all German speech MUST work on the
  learner's machine without an internet connection, like Spanish speech today.
- **FR-018**: If no usable voice exists for a language, the system MUST tell the learner in plain
  language and MUST NOT fall back to a voice for another language.

**Vocabulary and flashcards**

- **FR-019**: A word saved from a conversation MUST be saved in that conversation's language.
- **FR-020**: The word list, decks, practice, deck generation and analytics MUST show only the
  selected practice language's words, decks and practice history.
- **FR-021**: A new deck MUST belong to the practice language selected when it was created. Existing
  decks, words and practice history MUST belong to Spanish.
- **FR-022**: Word details and practice sentences for a flashcard MUST be about the word in its own
  language, with explanations in English.
- **FR-023**: The same spelling saved in two languages MUST be two separate words, each with its own
  progress, schedule and details.

**Preservation**

- **FR-024**: Updating to this version MUST keep all existing conversations, messages, vocabulary,
  decks, practice history and settings unchanged, and MUST set the practice language to Spanish.
- **FR-025**: Switching the practice language MUST NOT change or delete any data in either language.
- **FR-026**: All language-model providers the learner can select today MUST support German
  conversations. Selecting German MUST NOT change which provider is used.

### Key Entities *(include if feature involves data)*

- **Practice language**: a language the learner can practise, from a fixed set (Spanish, German). It
  has a display name, the voices available for it, and a default voice.
- **Learner settings**: now hold the selected practice language and the learner's chosen voice for
  each language, next to the existing settings (provider, level, correction mode and so on).
- **Conversation**: already carries a language. It is set from the practice language when the
  conversation starts and never changes.
- **Vocabulary word**: already carries a language, taken from the conversation it was saved from.
  The word and its language together identify it.
- **Deck**: now belongs to a practice language. Existing decks belong to Spanish.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From the home screen, a learner can switch to German and start a German conversation
  in under 30 seconds.
- **SC-002**: Across 10 German scenario conversations of 5 learner turns each, at least 95% of
  partner replies are entirely in German, with no English or Spanish words.
- **SC-003**: On a fixed set of 20 spoken German sentences, at least 90% are transcribed with their
  meaning intact and umlauts and ß spelled correctly.
- **SC-004**: 100% of conversation and flashcard features on a Spanish feature checklist also work
  in German (FR-008, FR-020, FR-022).
- **SC-005**: After updating, then switching to German and back to Spanish, 100% of pre-existing
  Spanish conversations, words, decks and practice records are present and unchanged.
- **SC-006**: With German selected, no Spanish word, deck or practice record appears on any
  Flashcards screen, and with Spanish selected, no German one appears.
- **SC-007**: With the network disconnected and the local defaults selected, a German conversation
  with spoken input and spoken replies completes normally.

## Assumptions

- **Native language stays English.** Only the practice language becomes selectable in this feature.
- **One active language at a time.** The practice language is chosen in Settings, not per
  conversation at start and not from the conversation screen. A conversation's language is fixed
  once it starts, so a mid-conversation language control would have nothing to change.
- **Flashcards follow the practice language.** Keeping flashcards per language is assumed to be what
  a learner of two languages wants. A combined view across languages is out of scope.
- **Standard German.** The partner speaks standard (High) German. Regional variants are accepted in
  the learner's input but are not a separate option.
- **Scenarios are shared.** The ten scenarios are not tied to any country, so they need no German
  versions. The partner sets them in a German-speaking context.
- **Quality limits carry over.** Conversation levels and corrections are experimental on the default
  local model for Spanish and are assumed to be at least as limited in German. Their existing
  warnings stay, and German-specific tuning of either is out of scope.
- **Voices are set up locally.** Like the Spanish voices, a German voice is fetched once during setup
  and then used offline.
- **Adding more languages later** (French, Italian and others) is out of scope, but FR-005 should
  make it a catalogue change.
