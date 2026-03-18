# Feature Specification: Speak — Role-Play Conversation Chat

**Feature Branch**: `001-speak-roleplay-chat`
**Created**: 2026-03-17
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Select a Scenario and Start a Conversation (Priority: P1)

A user opens Open Language and sees a home screen presenting a role-play scenario (e.g., "Buying
a train ticket"). They can shuffle to a different scenario by pressing a button, then tap "Start
Chat" to begin. The AI opens the conversation in the target language with a spoken and displayed
opening message. The user is immediately immersed in the role-play.

**Why this priority**: This is the core MVP — without scenario selection and conversation start,
no other chat feature has any value. It is the entry point to every other user story.

**Independent Test**: Can be fully tested by opening the app, shuffling through scenarios,
starting a chat, and verifying the AI's first message appears on screen and is spoken aloud.

**Acceptance Scenarios**:

1. **Given** the home screen is loaded, **When** the user views the current scenario card,
   **Then** one of the 10 hard-coded scenarios is displayed with a title and brief description.
2. **Given** a scenario is displayed, **When** the user taps "New Scenario",
   **Then** a different scenario from the list is shown (never the same one consecutively).
3. **Given** a scenario is selected, **When** the user taps "Start Chat",
   **Then** the chat screen opens, the AI generates an opening message in the target language,
   displays it as text, and reads it aloud automatically.

---

### User Story 2 — Respond by Voice or Text (Priority: P1)

After the AI speaks, the user records a voice response in the target language or types a reply
via keyboard. They press a button to stop recording; the spoken audio is transcribed and sent to
the AI. The AI responds in character, continuing the role-play.

**Why this priority**: Without user input, the conversation is one-sided. Voice-plus-text input
is the core interaction loop of the feature and shares P1 priority with scenario start.

**Independent Test**: Can be fully tested by starting a chat, recording a voice reply, stopping
recording, and confirming the transcription appears and the AI continues the conversation.

**Acceptance Scenarios**:

1. **Given** the chat screen is open with the AI's first message displayed, **When** the user
   taps the record button, **Then** audio recording begins with a visible indicator.
2. **Given** recording is in progress, **When** the user taps stop, **Then** the audio is
   transcribed locally, the transcribed text appears as the user's message, and the AI generates
   the next response.
3. **Given** the chat screen is open, **When** the user types in the keyboard input field and
   submits, **Then** the typed text is sent as the user's message and the AI responds.
4. **Given** the user replies in a language other than the target language, **When** the AI
   detects the mismatch, **Then** the AI replies asking the user to respond in the target
   language before continuing.

---

### User Story 3 — Per-Message Learning Tools (Priority: P2)

For each user message, the user can access a feedback button (grammatical accuracy), a translate
button (translate their own message), and an alternative phrasing button. For each AI message,
the user can access a translate button and request a slower spoken replay of that message.

**Why this priority**: These tools deliver the learning value of the conversation — without them
the app is a chat app, not a language-learning tool. They build naturally on top of P1.

**Independent Test**: Can be fully tested by completing a two-turn conversation and triggering
each per-message action (grammar feedback, translate, alternative phrasing, slow replay) and
verifying a result panel appears for each.

**Acceptance Scenarios**:

1. **Given** the user's message is visible in chat, **When** the user taps "Grammar Feedback",
   **Then** a panel appears with a grammatical accuracy assessment in the user's native language.
2. **Given** the user's message is visible, **When** the user taps "Translate",
   **Then** a translation of the user's message into their native language is shown.
3. **Given** the user's message is visible, **When** the user taps "Alternative Phrasing",
   **Then** one or more alternative ways to express the same idea in the target language are shown.
4. **Given** an AI message is visible, **When** the user taps "Translate",
   **Then** a translation of the AI's message into the user's native language is shown.
5. **Given** an AI message is visible, **When** the user taps "Play Slower",
   **Then** the AI's message is spoken at a reduced speed.

---

### User Story 4 — In-Chat Word and Phrase Translation (Priority: P2)

The user can select any word or phrase in any chat message (their own or the AI's) and request a
translation. This acts as an in-context dictionary lookup.

**Why this priority**: Vocabulary lookup during a conversation is a core learning behaviour. It
does not block P1 but greatly enhances the learning loop.

**Independent Test**: Can be tested by long-pressing or selecting text in a message and tapping
"Translate Selection", then verifying a translation popover or panel appears.

**Acceptance Scenarios**:

1. **Given** any message is visible, **When** the user selects one or more words and taps
   "Translate Selection", **Then** the translation(s) of those words appear in a tooltip or
   panel immediately without navigating away.
2. **Given** a phrase (multiple words) is selected, **When** the user requests translation,
   **Then** a phrase-level translation is returned, not just word-by-word.

---

### User Story 5 — Suggested Responses Panel (Priority: P3)

A collapsed panel in the chat screen, when expanded by the user, shows a set of contextually
appropriate suggested replies in the target language. The user may tap a suggestion to insert it
into their input (for speaking or typing), or ignore it entirely.

**Why this priority**: Helpful for learners who are stuck, but the conversation works without it.
It is an enhancement on top of a fully functional P1/P2 conversation.

**Independent Test**: Can be tested by expanding the suggestions panel mid-conversation and
verifying that suggestions are returned and one can be inserted into the input.

**Acceptance Scenarios**:

1. **Given** the suggestions panel is collapsed, **When** the user taps the expand control,
   **Then** 3–5 contextually appropriate replies are shown in the target language.
2. **Given** suggestions are shown, **When** the user taps one, **Then** it is inserted into
   the voice/text input field for the user to speak or submit.
3. **Given** suggestions are shown, **When** the user taps "Close", **Then** the panel
   collapses without changing the input.

---

### User Story 6 — Native-Language Expression Helper (Priority: P3)

A collapsible sidebar or panel lets the user open a separate AI conversation in their native
language where they can ask "How do I say X?" The user can copy or send the result back into the
main role-play conversation input.

**Why this priority**: Useful for learners who lack vocabulary for a thought they want to express,
but is an advanced feature layered on top of the core conversation loop.

**Independent Test**: Can be tested by opening the sidebar, asking a question in the native
language, receiving a target-language suggestion, and using it in the main conversation.

**Acceptance Scenarios**:

1. **Given** the chat screen is open, **When** the user opens the expression-helper panel,
   **Then** a separate input area appears for native-language questions, independent of the main
   conversation.
2. **Given** a native-language question is submitted, **When** the AI responds,
   **Then** the response appears in the sidebar in the target language.
3. **Given** a response is shown in the sidebar, **When** the user taps "Use This",
   **Then** the text is inserted into the main conversation input field.

---

### User Story 7 — Pause, Resume, and Review Past Chats (Priority: P3)

The user can pause an active conversation and return to it later. Completed or paused
conversations are stored locally and accessible from a history screen. The user can read through
any past conversation.

**Why this priority**: Local persistence is important for continuity and review but does not block
the core conversation experience.

**Independent Test**: Can be tested by starting a conversation, pausing, restarting the app, and
verifying the conversation history is still accessible and readable.

**Acceptance Scenarios**:

1. **Given** a conversation is in progress, **When** the user taps "End Chat",
   **Then** the conversation is saved locally and the user is returned to the home screen.
2. **Given** the home screen is loaded, **When** the user navigates to "Past Chats",
   **Then** a list of previous conversations is shown with scenario name and date.
3. **Given** a past chat is selected, **When** the user opens it,
   **Then** the full conversation transcript is readable.

---

### User Story 8 — LLM Model Configuration (Priority: P3)

From a settings screen the user can view and change which LLM model is used for AI conversation
responses, grammar feedback, translation, alternative phrasing, and suggested responses.

**Why this priority**: Configurability is important for power users and future extensibility, but
the app ships functional with sensible defaults.

**Independent Test**: Can be tested by navigating to settings, selecting a different model, and
verifying subsequent AI responses come from the newly selected model.

**Acceptance Scenarios**:

1. **Given** the settings screen is open, **When** the user views the model configuration
   section, **Then** the currently selected model for each AI task is displayed.
2. **Given** the model configuration section is open, **When** the user selects a different
   available model and saves, **Then** subsequent AI requests use that model without an app
   restart.

---

### Edge Cases

- What happens when audio transcription fails or returns no text? The user sees a clear error
  message and can retry the recording or switch to keyboard input without losing the conversation.
- What happens when an LLM request times out or fails mid-conversation? The failed turn is
  flagged visually and the user can retry; previous conversation turns are preserved.
- What happens when the user has not selected a scenario and taps "Start Chat"? The button is
  disabled until a valid scenario is displayed.
- What happens when the device microphone permission is denied? Voice recording is hidden or
  disabled, keyboard input is offered as the only option, and a plain-language explanation is
  shown.
- What happens when local storage capacity is reached? The user is notified before a new
  conversation begins and offered the option to delete old chats.
- What happens when the user's selected text for translation spans across two messages? Only text
  within a single message bubble can be selected; cross-bubble selection is not supported.

---

## Requirements *(mandatory)*

### Functional Requirements

**Home Screen & Scenario Selection**

- **FR-001**: The home screen MUST display one role-play scenario at a time from a set of exactly
  10 hard-coded scenarios at initial delivery.
- **FR-002**: The scenario source MUST be implemented behind a `ScenarioProvider` interface so it
  can be replaced with an AI-generated or server-sourced provider without modifying the chat
  feature.
- **FR-003**: Users MUST be able to request a new scenario via a single button tap; the system
  MUST NOT show the same scenario twice consecutively.
- **FR-004**: Users MUST be able to start a conversation from the currently displayed scenario
  via a clearly labelled primary action button.

**Conversation & AI Interaction**

- **FR-005**: Upon starting a chat, the system MUST generate an AI opening message in the target
  language appropriate to the selected scenario, display it as text, and play it as speech.
- **FR-006**: Users MUST be able to start and stop a voice recording to capture a response.
- **FR-007**: Users MUST be able to type a response via keyboard as an alternative to voice input.
- **FR-008**: Transcribed or typed user messages MUST be sent to the AI to continue the
  conversation in-character within the role-play scenario.
- **FR-009**: The system MUST detect when the user's response is in a language other than the
  target language and the AI MUST redirect the user back to the target language.
- **FR-010**: The AI MUST maintain role-play character throughout the conversation unless
  delivering an explicit learning-tool result (feedback, translation, etc.).

**Per-Message Learning Tools**

- **FR-011**: Each user message MUST offer a "Grammar Feedback" action returning a grammatical
  accuracy assessment in the user's native language.
- **FR-012**: Each user message MUST offer a "Translate" action returning a translation of that
  message into the user's native language.
- **FR-013**: Each user message MUST offer an "Alternative Phrasing" action returning one or
  more alternative target-language expressions for the same intent.
- **FR-014**: Each AI message MUST offer a "Translate" action returning a translation into the
  user's native language.
- **FR-015**: Each AI message MUST offer a "Play Slower" action that replays the message's
  audio at a reduced speed.

**In-Chat Word/Phrase Translation**

- **FR-016**: Users MUST be able to select any contiguous text within a single message and
  request a translation of that selection.
- **FR-017**: Translation results for selected text MUST appear inline (tooltip or panel) without
  navigating away from the chat screen.

**Suggested Responses**

- **FR-018**: A collapsible suggestions panel MUST be available in the chat screen and MUST be
  collapsed by default.
- **FR-019**: When expanded, the suggestions panel MUST display 3–5 contextually appropriate
  replies in the target language based on the current conversation.
- **FR-020**: Users MUST be able to insert a suggestion into their input field with a single tap.

**Expression Helper**

- **FR-021**: A collapsible expression-helper panel MUST be available in the chat screen for a
  parallel native-language AI conversation.
- **FR-022**: The expression-helper conversation context MUST be separate from the main role-play
  thread.
- **FR-023**: Users MUST be able to transfer the AI's response from the expression-helper into
  the main conversation input with a single action.

**Persistence & History**

- **FR-024**: Users MUST be able to end a chat at any time; the full conversation MUST be saved
  locally before the user leaves the chat screen.
- **FR-025**: Users MUST be able to access a chronological list of past conversations from the
  home screen.
- **FR-026**: Each past conversation MUST be fully readable as a transcript.

**Settings & Model Configuration**

- **FR-027**: A settings screen MUST allow the user to view and change the LLM model used for
  each AI task (conversation, grammar feedback, translation, alternative phrasing, suggested
  responses).
- **FR-028**: The system MUST use an `LLMProvider` interface so any configured model can be
  substituted without modifying conversation or learning-tool logic.

### Key Entities

- **Scenario**: A role-play prompt with a title, brief description, and AI persona context.
  Sourced via the `ScenarioProvider` interface; the initial implementation is a static list of 10.
- **Conversation**: A session linking a Scenario to an ordered list of Messages, with start time,
  optional end time, and target language. Persisted locally.
- **Message**: A single turn in a Conversation — user or AI authored. Contains text, input source
  (voice/keyboard), timestamp, and any associated learning-tool results.
- **LearningToolResult**: A named result (grammar feedback, translation, alternative phrasing)
  attached to a Message. Cached so the user can re-read without re-fetching.
- **ModelConfiguration**: The user's selected LLM model identifiers per task type, persisted in
  local user settings.
- **ScenarioProvider** *(interface)*: Abstracts scenario loading — static list initially; future
  implementations may be AI-generated or server-sourced.
- **LLMProvider** *(interface)*: Abstracts LLM API calls — the configured model is injected at
  runtime via `ModelConfiguration`.

## Assumptions

- Target language and native language are set in user settings (not in scope for this spec);
  Spanish (target) / English (native) is the default for the initial implementation.
- Audio transcription runs locally using the faster-whisper library; no network is required for
  transcription.
- Text-to-speech for AI messages uses a system or bundled TTS engine; the specific engine is
  deferred to the planning phase.
- The 10 initial scenarios are common everyday situations: buying a train ticket, checking into a
  hotel, ordering at a restaurant, calling a doctor's office, asking for directions, interviewing
  for a job, renting a car, visiting a pharmacy, reporting a lost item, and boarding an airplane.
- LLM calls require internet access; all LLM-dependent features degrade gracefully when offline,
  showing a clear "unavailable" state rather than an error crash.
- Local storage is the only persistence mechanism for this proof-of-concept; cloud sync and
  backup are out of scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can open the app, select a scenario, and hear the AI's opening message
  within 5 seconds of tapping "Start Chat".
- **SC-002**: Voice transcription results appear on screen within 3 seconds of the user stopping
  a recording of 30 seconds or less.
- **SC-003**: All per-message learning tools (grammar feedback, translate, alternative phrasing,
  slow replay) return a visible result within 5 seconds of being tapped under normal network
  conditions.
- **SC-004**: Users can complete a 5-turn role-play conversation from scenario selection through
  "End Chat" without encountering a blocking error.
- **SC-005**: A new LLM model selected in settings takes effect on the next message without an
  application restart.
- **SC-006**: All previously completed conversations are retrievable and fully readable from the
  history screen after the application is restarted.
- **SC-007**: In usability testing, 90% of users can locate and successfully use the suggestions
  panel and expression-helper without being given explicit instructions.
