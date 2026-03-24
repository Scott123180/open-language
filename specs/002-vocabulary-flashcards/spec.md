# Feature Specification: Vocabulary Flashcards

**Feature Branch**: `002-vocabulary-flashcards`
**Created**: 2026-03-22
**Status**: Draft
**Version**: 1.1

## Overview

The Flashcards feature enables users to practice vocabulary they have saved from chat conversations. It provides a dedicated section of the app—accessible from the home screen—where users can manage saved words, generate custom practice decks, and study using multiple exercise modes. The feature tracks learning progress over time and supports audio, written, and spoken practice.

The feature is language-agnostic. All references to a "target language" and "native language" are determined by the user's language configuration in the app. The app's TTS engine and LLM integration already support the configured languages, so no language-specific logic is needed within the flashcard feature itself. All LLM and TTS infrastructure runs locally as part of the existing project — no internet connectivity is required.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Word Library Management (Priority: P1)

A user who has been chatting with the AI tutor has accumulated saved vocabulary words. They open the Flashcards section to review their word library, browse all saved words with their translations and learning status, filter by classification or date, and manually adjust a word's classification if needed.

**Why this priority**: The word library is the foundation of the entire feature. Without a usable, browsable word list, no other flashcard functionality can be demonstrated or tested independently.

**Independent Test**: Can be tested by adding words to the library via the existing chat "Add word" action and verifying they appear with correct fields in the Word List screen. No deck generation or practice is required to validate this story.

**Acceptance Scenarios**:

1. **Given** a user has saved words from chat, **When** they open the Flashcards section, **Then** they see a scrollable list of all saved words with word, translation, date added, and classification displayed for each.
2. **Given** the Word List is open, **When** the user applies a "Difficult" classification filter, **Then** only words classified as Difficult are displayed.
3. **Given** the Word List is open, **When** the user types in the search field, **Then** the list narrows to matching words in real time.
4. **Given** a word classified as "Not Practiced", **When** the user manually sets it to "Difficult", **Then** the classification updates immediately in the list.
5. **Given** the Word List is open, **When** the user taps "Select All", **Then** all currently visible words are selected for deck generation.

---

### User Story 2 - Basic Flashcard Practice (Recall Mode) (Priority: P1)

A user selects words from their library, generates a deck in Recall mode, and works through the cards one at a time: viewing the target-language word, attempting to recall the translation (by speaking or typing), flipping the card to see the answer, then self-grading their recall.

**Why this priority**: This is the core learning loop. All other practice modes are variations of this flow. Delivering Recall mode alone provides a complete, usable vocabulary practice feature.

**Independent Test**: Can be tested end-to-end by: saving words from chat → opening Word List → generating a Recall deck → completing a full session → verifying session summary is shown.

**Acceptance Scenarios**:

1. **Given** words are selected, **When** the user configures and generates a Recall deck, **Then** the deck is saved and the user can begin practicing immediately.
2. **Given** a Recall session is active, **When** a card is shown, **Then** the target-language word is displayed as the prompt.
3. **Given** a card is shown, **When** the user taps the microphone button and speaks, **Then** the spoken input is captured as their response.
4. **Given** a card is shown, **When** the user taps "Flip Card", **Then** the native-language translation is revealed.
5. **Given** the answer is revealed, **When** the user taps "Knew It", **Then** the rating is recorded and the next card is shown.
6. **Given** all cards in a deck are completed, **When** the last card is graded, **Then** the Session Summary screen is displayed with score breakdown and encouragement.

---

### User Story 3 - Deck Generation with Smart Algorithms (Priority: P2)

A user opens the deck configuration panel and chooses a generation algorithm to build a targeted practice deck. The system selects words according to the chosen strategy (e.g., prioritize Difficult words, introduce Not Practiced words, or produce a Mixed Review) and notifies the user if fewer words than requested are available.

**Why this priority**: Smart deck generation transforms the feature from a simple card viewer into an adaptive learning tool. It depends on the word library (P1) but does not require analytics or additional practice modes to deliver standalone value.

**Independent Test**: Can be tested by having words in multiple classification states and verifying each algorithm selects words according to its defined priority order.

**Acceptance Scenarios**:

1. **Given** a user selects the "Unknown / Difficult" algorithm, **When** the deck is generated, **Then** the deck contains Difficult words first, filled with Not Practiced words if more slots remain.
2. **Given** a user requests a deck of 20 cards but only 12 eligible words exist, **When** the deck is generated, **Then** the deck contains 12 cards and the user sees a notification explaining the adjusted size.
3. **Given** a "Mixed Review" algorithm is selected, **When** a deck of 20 cards is generated from a sufficient word pool, **Then** roughly 8 Difficult, 6 Almost Learned, 4 Not Practiced, and 2 Learned words are included.
4. **Given** a deck is generated, **When** the user navigates to "My Decks", **Then** the saved deck appears with its name, card count, mode, algorithm, and creation date.

---

### User Story 4 - Additional Practice Modes (Priority: P2)

A user generates decks in Listen, Produce, or Fill-in-the-Blank modes to vary their practice. In Listen mode, audio plays automatically instead of showing the word. In Produce mode, the native-language word is the prompt and the user must supply the target-language translation. In Fill-in-the-Blank mode, a sentence with a missing word is displayed and the user supplies the blank.

**Why this priority**: These modes meaningfully deepen learning by testing different recall directions and modalities. They depend on the core card interaction loop (P1) and deck generation (P2).

**Independent Test**: Each mode can be independently tested by generating a deck in that mode and completing a session, verifying the correct prompt type is displayed.

**Acceptance Scenarios**:

1. **Given** a Listen mode session, **When** a card appears, **Then** audio plays automatically and no text prompt is shown.
2. **Given** a Listen mode session, **When** the user taps "Slow Speed", **Then** the audio replays at a reduced speed.
3. **Given** a Produce mode session, **When** a card appears, **Then** the native-language word is the prompt.
4. **Given** a Fill-in-the-Blank session, **When** a card appears, **Then** a target-language sentence with a blank is shown and the correct word is not visible.
5. **Given** a Fill-in-the-Blank session, **When** the user submits an answer, **Then** the complete sentence with the correct word highlighted is revealed.

---

### User Story 5 - Classification & Spaced Repetition (Priority: P2)

After completing a practice session, word classifications are automatically recalculated based on the rolling history of ratings. Words that were consistently known progress toward "Learned"; words that were missed regress toward "Difficult". Additionally, deck generation incorporates time-based scheduling so that Learned words are resurfaced after a configurable number of days, preventing vocabulary decay.

**Why this priority**: Automatic classification and spaced repetition are what distinguish an effective learning tool from a simple flashcard viewer. They require completed sessions (P1) to function.

**Independent Test**: Can be tested by completing multiple sessions with controlled ratings and verifying that word classifications in the Word List reflect the expected state transitions.

**Acceptance Scenarios**:

1. **Given** a word is rated "Knew It" in 3 consecutive sessions, **When** classification is recalculated, **Then** the word is marked "Learned".
2. **Given** a word classified as "Learned" is rated "Didn't Know" in the next session, **When** classification is recalculated, **Then** the word regresses to "Difficult".
3. **Given** a word classified as "Learned" was last practiced more than N days ago, **When** a new deck is generated, **Then** the spaced-repetition scheduler includes that word as eligible for review.
4. **Given** a manual classification override is set, **When** the word appears in the next practice session, **Then** the automatic system resumes control after that session and the manual override is cleared.

---

### User Story 6 - Contextual Word Information (Priority: P2)

After revealing an answer on any card, the user can tap contextual information buttons (All Meanings, Usage & Sentences, Common Phrases, Similar Words) to deepen their understanding. The content is generated by the LLM on first request and cached per word so subsequent views are instant.

**Why this priority**: Contextual information is a valuable learning enrichment feature. It depends on the card interaction loop (P1) but does not block any other story.

**Independent Test**: Can be tested by completing a card flip and tapping each contextual button, verifying LLM content is returned, and then tapping again to confirm the cached response is served without a new LLM call.

**Acceptance Scenarios**:

1. **Given** a card answer has been revealed, **When** the user taps "All Meanings", **Then** LLM-generated definitions and parts of speech are displayed.
2. **Given** "All Meanings" was previously requested for a word, **When** the user taps it again in a subsequent session, **Then** the cached content is shown without a new LLM request.
3. **Given** the user's language configuration changes, **When** a cached LLM response for a word is retrieved, **Then** the cache is invalidated and new content is generated for the current language.

---

### User Story 7 - Session Summary & Post-Session Actions (Priority: P2)

After completing or exiting a session, the user sees a summary screen showing their score breakdown, session duration, streak count, and an LLM-generated encouragement message. They can practice again, drill only the words they missed, or navigate back to their decks or word list.

**Why this priority**: The summary screen closes the learning loop and motivates continued practice. It depends on completed sessions but does not block the core practice flow.

**Independent Test**: Can be tested by completing a session and verifying the summary screen shows correct counts, streak data, and the "Practice Missed Words" action generates a mini-deck containing only the missed words.

**Acceptance Scenarios**:

1. **Given** a session is completed, **When** the summary screen appears, **Then** it shows counts and percentages for Knew It, Guessed Correctly, and Didn't Know, plus total session duration.
2. **Given** the user has practiced on consecutive days, **When** the summary screen appears, **Then** the current streak count is displayed.
3. **Given** the summary screen is shown, **When** the user taps "Practice Missed Words", **Then** a mini-deck is generated containing only the words rated "Didn't Know" from that session.
4. **Given** a session ended early, **When** the summary screen appears, **Then** "X of Y cards reviewed" is displayed.

---

### User Story 8 - Deck Refresh (Priority: P3)

A user can "refresh" an existing deck to swap out Learned words for new, unpracticed words without creating an entirely new deck. This keeps a favorite deck configuration relevant as vocabulary progresses.

**Why this priority**: Deck refresh is a convenience feature that enhances the experience for returning users with large vocabularies. It depends on saved decks and classification states.

**Independent Test**: Can be tested by having a saved deck where some words are now "Learned", refreshing it, and confirming Learned words were replaced by Not Practiced or Difficult words while deck size and configuration remain the same.

**Acceptance Scenarios**:

1. **Given** a saved deck contains words now classified as "Learned", **When** the user taps "Refresh Deck", **Then** Learned words are replaced with words from the eligible pool according to the original algorithm.
2. **Given** a refresh is performed, **When** the deck is shown in "My Decks", **Then** the deck name and configuration are unchanged but the card composition reflects the refresh.

---

### User Story 9 - Analytics Dashboard (Priority: P3)

A user opens the Analytics Dashboard to review their learning progress over time. They see at-a-glance stats (total words saved, words learned, current streak, sessions this week), time-series charts of accuracy and daily activity, a classification distribution chart, a list of hardest words, and a breakdown of accuracy by practice mode.

**Why this priority**: Analytics provide motivation and insight but are not required for the core learning flow. They depend on sufficient session history to be meaningful.

**Independent Test**: Can be tested independently by seeding session history and verifying each chart and stat card displays the correct aggregated values.

**Acceptance Scenarios**:

1. **Given** the user opens the Analytics Dashboard, **When** the page loads, **Then** at-a-glance stats (total words, learned count, streak, sessions this week) are displayed.
2. **Given** the user selects the "30-day" time range toggle, **When** the accuracy trend chart updates, **Then** it displays one data point per session within the last 30 days.
3. **Given** the user taps a word in the "Hardest Words" table, **When** they are navigated away, **Then** the Word List opens with that word's detail highlighted.
4. **Given** sessions have been recorded in multiple modes, **When** the Mode Performance chart is displayed, **Then** accuracy is shown separately for each of the four practice modes.

---

### Edge Cases

- What happens when a word is saved from chat that already exists in the library (same word, same target language)? → The existing record is updated (source chat, date); classification and history are preserved; a "Already saved" notification is shown. No duplicate is created.
- What happens to session history when a word is deleted from the library? → Historical CardResult records are retained as orphaned records; past analytics remain intact. The word no longer appears in the Word List or future deck generation.
- What happens to session history when a deck is deleted? → PracticeSession and CardResult records are retained as orphaned records; analytics (accuracy trends, mode performance) remain intact. The deck no longer appears in My Decks.
- What happens when the word library is empty and the user taps "Generate Deck"? → A message is shown explaining that words must be saved from chat before generating a deck. The Generate button is disabled.
- What happens when a requested deck size exceeds the total word pool? → The deck is created with all available eligible words and the user is notified of the adjusted size.
- What happens when all words in the pool are already "Learned" and the selected algorithm targets Difficult/Not Practiced? → The fallback chain is applied; if no eligible fallback words exist, the user is notified and prompted to choose a different algorithm or word source.
- What happens if the LLM is unavailable when a contextual info button is tapped? → A friendly error message is shown; the user can retry. The card session is not interrupted.
- What happens if Fill-in-the-Blank sentence generation fails for a word during deck creation? → That word falls back to standard Recall mode display for that card; the user sees a note that the sentence was unavailable.
- What happens when a user exits a session mid-way? → The session is recorded as incomplete. Cards already rated are saved and classification is recalculated for those words immediately. Remaining unrated cards are not processed. The summary screen still appears showing partial results.
- What happens if the spaced-repetition interval N is not yet configured? → A sensible default interval (e.g., 7 days for Learned words) is applied.
- What happens when two sessions complete simultaneously for the same word (e.g., app resumed from background)? → The most recently completed session's rating takes precedence for classification recalculation.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Navigation & Entry Point

- **FR-001**: System MUST provide a "Flashcards" entry point accessible from the home screen as a top-level navigation destination.
- **FR-002**: Users MUST be able to navigate back to the Word List or home screen from any Flashcards sub-screen using a back button.

#### Word Library

- **FR-003**: System MUST display all saved vocabulary words in a scrollable list showing word, translation, date added, classification, and source chat reference.
- **FR-004**: System MUST support filtering the word list by classification (multi-select: Not Practiced, Almost Learned, Difficult, Learned), by date range (last 7 days, 30 days, custom), and by free-text search.
- **FR-005**: Users MUST be able to select individual words or use "Select All / Deselect All" controls for deck generation.
- **FR-006**: Users MUST be able to manually override a word's classification from the Word List; the override persists until the word next appears in a completed practice session.
- **FR-006b**: Users MUST be able to delete individual words from the Word List. Deletion removes the word from the library and all active decks; historical CardResult records referencing that word are retained as orphaned records and excluded from the Word List view but remain reflected in past session analytics.

#### Classification System

- **FR-007**: Every newly saved word MUST be assigned the "Not Practiced" classification by default.
- **FR-008**: System MUST automatically recalculate word classifications whenever a practice session ends — whether completed in full or exited early — for every card that was rated before the session ended, based on the rolling history of the last 5 ratings per word.
- **FR-009**: System MUST apply the following classification transitions, evaluated against the rolling last-5 ratings per word, in priority order: (1) "Knew It" in 3+ consecutive ratings → "Learned" (highest priority; overrides all other rules even if Didn't Knows exist in the same window); (2) "Learned" then "Didn't Know" in the next session → regresses to "Difficult"; (3) "Didn't Know" 2+ times in the last 5 ratings → "Difficult"; (4) at least 3 of the last 5 ratings are Guessed or Knew, with ≥1 Guessed and no 3+ consecutive Knew streak → "Almost Learned".
- **FR-010**: Classification recalculation MUST happen silently without interrupting the user; changes MUST be reflected immediately in the Word List.

#### Spaced Repetition

- **FR-011**: System MUST incorporate adaptive per-word spaced-repetition scheduling into deck generation: each "Learned" word has its own resurfacing interval with three distinct rating effects — "Knew It" advances the interval to the next stage (7 → 14 → 30 → 30 days), "Guessed Correctly" holds the current stage (no advance, no reset), and "Didn't Know" resets the interval to stage 1 (7 days).
- **FR-012**: Words whose spaced-repetition interval has elapsed MUST be treated as eligible candidates in deck generation algorithms.

#### Deck Generation

- **FR-013**: Users MUST be able to configure deck size (presets: 10, 20 default, 40; custom input), word source (all words, filtered subset, manually selected), practice mode, and generation algorithm before generating a deck.
- **FR-014**: System MUST support four generation algorithms: Not Practiced, Unknown / Difficult, Previously Guessed, and Mixed Review — each with the defined priority order and fallback behavior.
- **FR-015**: Within each priority tier, word selection MUST be randomized to ensure variety across sessions.
- **FR-016**: If the eligible word pool is smaller than the requested deck size, the system MUST create the deck with all available words and notify the user of the adjusted size.
- **FR-017**: Every generated deck MUST be persisted and shown in "My Decks" with its name, card count, mode, algorithm, dates, session history summary, and last-session accuracy.
- **FR-018**: Deck names MUST be auto-generated (e.g., "Deck — Mar 22, 2026") and editable by the user.
- **FR-019**: Users MUST be able to refresh an existing deck to replace Learned words with new eligible words, preserving the original deck configuration.
- **FR-019b**: Users MUST be able to delete a saved deck from "My Decks". Deletion removes the deck and its DeckCards; all PracticeSession and CardResult records for that deck are retained as orphaned records so analytics (accuracy trends, mode performance) remain intact.

#### Practice Modes

- **FR-020**: System MUST support four practice modes: Recall (target → native), Listen (audio → native), Produce (native → target), and Fill-in-the-Blank (gapped sentence → missing word).
- **FR-021**: In Recall mode, the target-language word MUST be displayed as the card prompt; response options MUST include speak (microphone) and type (text input).
- **FR-022**: In Listen mode, audio MUST play automatically when the card appears; the target-language word MUST NOT be shown visually; the user MUST be able to replay audio and use slow-speed playback.
- **FR-023**: In Produce mode, the native-language word MUST be the prompt; after the answer is revealed, the target-language word MUST be shown with audio pronunciation.
- **FR-024**: In Fill-in-the-Blank mode, LLM-generated sentences with the target word removed MUST be generated at deck creation time and cached with the deck; the correct word MUST be highlighted in the revealed answer.

#### Card Controls

- **FR-025**: Every card MUST provide a Listen button (TTS playback of the target word) and a Slow Speed button (reduced-speed replay).
- **FR-026**: Every card MUST provide Speak (microphone) and Type (text input) response options, plus a manual Flip Card control.
- **FR-027**: After the answer is revealed, contextual info buttons (All Meanings, Usage & Sentences, Common Phrases, Similar Words) MUST become available; content is generated by the LLM on first request and cached per word per language.
- **FR-028**: Every practice mode MUST include a help button ("?") that displays a contextual overlay explaining the exercise and controls.
- **FR-029**: After viewing the answer, users MUST self-grade using one of three ratings: Didn't Know, Guessed Correctly, Knew It.

#### Session Completion

- **FR-030**: Upon completing or exiting a session, users MUST be taken to a Session Summary screen showing score breakdown (Knew It / Guessed / Didn't Know counts and percentages), cards reviewed vs. total, session duration, current streak, words needing work, and an LLM-generated encouragement message.
- **FR-031**: From the Summary screen, users MUST be able to: Practice Again (same deck), Practice Missed Words (mini-deck of Didn't Know words only), Back to Decks, and Back to Word List.

#### Session Tracking

- **FR-032**: System MUST record for every session: date/time, deck reference, mode, algorithm, total/reviewed card counts, per-rating breakdown, per-card result (word, rating, response type, user response text), session duration, and completion status.

#### Analytics Dashboard

- **FR-033**: System MUST provide an Analytics Dashboard accessible from the Flashcards section showing at-a-glance stats: total words saved, words learned, current streak (consecutive days with at least one session), and sessions this week.
- **FR-034**: Analytics MUST include time-series charts (7-day, 30-day, all-time toggle): accuracy trend (line chart), daily activity in cards (bar chart), and classification distribution over time (stacked area chart).
- **FR-035**: Analytics MUST include a vocabulary breakdown section: classification donut chart, hardest words table (sorted by Didn't Know ratio, tappable to navigate to word detail), and recently learned words list.
- **FR-036**: Analytics MUST include a mode performance comparison showing accuracy per practice mode as a grouped bar chart.

#### LLM Integration & Caching

- **FR-037**: LLM-generated word content (All Meanings, Usage & Sentences, Common Phrases, Similar Words) MUST be cached after the first request and served from cache on subsequent requests for the same word and language configuration.
- **FR-038**: The LLM content cache MUST be invalidated when the user's language configuration changes.

### Key Entities

- **SavedWord**: A vocabulary word the user has saved from a chat conversation. Carries word text, translation, target and native language codes, date added (updated on re-save), current classification, source chat reference (updated on re-save), and a manual override flag. Word + target language is a unique combination per user — re-saving an existing word merges rather than duplicates.
- **WordClassification**: An enumerated state for a saved word: Not Practiced, Difficult, Almost Learned, Learned.
- **Deck**: A named, persisted collection of cards generated from the user's word library. Carries configuration (practice mode, generation algorithm, size), creation date, and references to its constituent cards and sessions.
- **DeckCard**: A single card within a deck. Links to a SavedWord and, for Fill-in-the-Blank mode, stores the pre-generated sentence with the blank.
- **PracticeSession**: A recorded instance of a user practicing a deck. Stores mode, algorithm, start/end times, total cards, cards reviewed, completion flag, and rating breakdown.
- **CardResult**: The outcome of a single card within a session. Records the saved word, self-assessment rating, response type (spoken/typed), and the user's response text.
- **WordLLMCache**: Cached LLM-generated content for a word. Keyed by word, cache type (meanings/usage/phrases/similar), and language. Stores the generated content and the date generated.
- **SpacedRepetitionSchedule**: Tracks the last-practiced date, current interval stage (7 / 14 / 30 / 30+ days), and calculated next-due date per word for adaptive resurfacing. "Knew It" advances stage; "Guessed Correctly" holds stage; "Didn't Know" resets to stage 1 (7 days).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can save a word from chat, open the Flashcards section, generate a deck, and complete a full practice session in under 3 minutes total from a cold start.
- **SC-002**: Word classifications accurately reflect the defined thresholds: a word rated "Knew It" exactly 3 consecutive times is classified as "Learned" with no additional sessions required.
- **SC-003**: Deck generation for any algorithm completes and the deck is ready to practice in under 5 seconds for a library of up to 1,000 saved words.
- **SC-004**: LLM-generated contextual content (All Meanings, Usage, etc.) is displayed within 10 seconds of the first request; subsequent views of cached content appear within 1 second.
- **SC-005**: Fill-in-the-Blank sentences are generated and cached at deck creation time such that no per-card LLM delay occurs during the practice session.
- **SC-006**: The Session Summary screen appears within 2 seconds of the user rating the final card in a deck.
- **SC-007**: Analytics data on the dashboard reflects completed session results within 5 seconds of a session ending.
- **SC-008**: The word library accurately displays all saved words without omission; filters reduce the displayed list to only matching words with no false positives.
- **SC-009**: 100% of completed session results are persisted and available in analytics; no data is lost on early session exit.
- **SC-010**: Spaced-repetition scheduling resurfaces "Learned" words in new decks after the configured interval, with no "Learned" word permanently excluded from future decks.

---

## Clarifications

### Session 2026-03-22

- Q: What is the exact threshold for "Almost Learned" classification given a 5-rating rolling window? → A: At least 3 of the last 5 ratings are Guessed or Knew, with ≥1 Guessed and no 3+ consecutive Knew streak.
- Q: When two classification rules fire simultaneously (e.g., 3 consecutive Knew Its AND 2 Didn't Knows in the last 5), which takes precedence? → A: Streak wins — 3 consecutive Knew Its always promotes to Learned, overriding any Didn't Knows in the same window.
- Q: Which self-assessment ratings count as "successful recall" for advancing the spaced repetition interval? → A: "Knew It" advances to the next stage; "Guessed Correctly" holds the current stage (no advance, no reset); "Didn't Know" resets to stage 1 (7 days).
- Q: Can users delete saved decks from My Decks? → A: Yes — allow deletion; PracticeSession and CardResult records are retained as orphaned records so analytics remain intact.
- Q: Is the spaced-repetition interval fixed (shared by all Learned words) or adaptive per word? → A: Adaptive per-word — interval starts at 7 days and grows (7 → 14 → 30 → monthly) after each successful recall; resets to 7 days on "Didn't Know".
- Q: What happens when a user saves a word that already exists in their library? → A: Merge — show a notification "Already saved", update source chat reference and date to the latest encounter, preserve existing classification and history.
- Q: Can users delete words from their library, and what happens to historical session data? → A: Yes — allow deletion; historical CardResult records referencing the deleted word are retained as orphaned records so analytics remain intact. Deleted words no longer appear in the Word List.
- Q: Should classification recalculate for cards rated before an early session exit? → A: Yes — recalculate classification for every card rated before exit, even in an incomplete session.

---

## Assumptions

- The existing "Add word to flashcard list" mechanism in the chat interface already saves words with their translation and source chat reference; no changes to that flow are in scope.
- TTS audio generation for target-language words uses the existing Piper TTS engine, which already supports the configured languages; no new TTS integration is required.
- Speech input (microphone) uses the existing faster-whisper transcription integration; the flashcard feature calls it as a dependency, not a new implementation.
- LLM interactions use the existing Ollama/llama3.1 client already present in the project; prompt design for flashcard-specific content is in scope but client integration is not.
- The app runs entirely offline; all LLM, TTS, and STT infrastructure is local. There is no cloud dependency.
- Slow-speed audio replay is achieved by reducing playback rate of the TTS audio; a 0.6× rate is a reasonable default.
- Spaced repetition uses an adaptive per-word interval schedule: 7 days → 14 days → 30 days → 30 days (monthly) for successive successful recalls; resets to 7 days on "Didn't Know". The starting interval (7 days) is the system default and is not user-configurable in this version.
- The "rolling history" used for classification recalculation considers the last 5 card results for a given word across all sessions.
- A "consecutive day streak" is defined as at least one completed or partial session on each calendar day with no gap days.
- Gamification (badges, XP) is explicitly out of scope for this version.
- User flagging of incorrect LLM content is explicitly out of scope.
