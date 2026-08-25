# Feature Specification: Corrective Feedback Mode

**Feature Branch**: `003-corrective-feedback-mode`
**Created**: 2026-08-24
**Status**: Draft
**Input**: User description: "A three-position setting (Off / Gentle / Strict) that controls whether the conversation partner corrects the learner's grammar mistakes as they happen, instead of the learner having to click the Grammar button afterwards."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner is told when they got it wrong and asked to try again (Priority: P1)

A learner is practising a scenario conversation. They turn correction mode to **Strict**. They say
or type a sentence with a real grammar mistake. Instead of the character understanding them
perfectly and carrying on, the conversation pauses: the learner is shown what was wrong, given the
corrected sentence, and asked to say it again. When they send a second attempt, the conversation
picks up where it left off.

**Why this priority**: This is the core problem the feature exists to solve. Today the learner only
finds out about a mistake if they already suspected one and clicked the Grammar button — which means
the mistakes they most need to learn about, the ones they did not notice, are exactly the ones they
never hear about. Strict mode closes that loop and is valuable on its own, with no other mode built.

**Independent Test**: Set the mode to Strict, send a sentence with a known conjugation error, and
confirm the learner receives an explicit correction with the fixed sentence and a prompt to retry,
and that the scenario does not advance until they respond.

**Acceptance Scenarios**:

1. **Given** correction mode is Strict, **When** the learner sends a sentence containing a
   substantive grammar error, **Then** a correction is shown identifying the error and giving the
   corrected sentence, along with a prompt to try again.
2. **Given** a correction is showing and the scenario is paused, **When** the learner sends a
   corrected second attempt, **Then** the conversation resumes from the paused point with the
   character responding to the content of the message.
3. **Given** correction mode is Strict, **When** the learner sends a grammatically correct sentence,
   **Then** no correction of any kind is shown and the conversation proceeds normally.
4. **Given** a Strict correction is displayed, **When** the character's reply is played aloud,
   **Then** the correction text is never spoken in the character's voice.

---

### User Story 2 - Learner is corrected without breaking the conversation (Priority: P2)

The same learner finds Strict mode too interruptive for fluency practice and switches to **Gentle**.
Now when they make a mistake, the character stays fully in character and continues speaking only the
target language, but naturally restates the corrected version inside its own reply — the way a
patient native speaker echoes back what you meant. The conversation never stops. The learner may not
consciously register that they were corrected, which is the intent.

**Why this priority**: Delivers the same pedagogical value with far less friction, and is the mode a
learner is likely to leave switched on day to day. It depends on the correction-detection capability
proven by Story 1, so it follows rather than leads.

**Independent Test**: Set the mode to Gentle, send a sentence with a known error, and confirm the
character's single reply contains the corrected form woven in naturally, is entirely in the target
language, and does not stop to ask the learner to repeat anything.

**Acceptance Scenarios**:

1. **Given** correction mode is Gentle, **When** the learner sends a sentence with a substantive
   error, **Then** the character's reply contains the corrected form of what the learner meant and
   still advances the conversation in the same turn.
2. **Given** correction mode is Gentle, **When** the character replies, **Then** the reply contains
   no words of the learner's native language.
3. **Given** correction mode is Gentle, **When** the learner sends a correct sentence, **Then** the
   reply is an ordinary in-character response with no restatement or correction.

---

### User Story 3 - Learner is not nagged (Priority: P3)

The learner practises for an extended session. The app corrects the mistakes that would actually
sound wrong or confuse a native speaker, and stays silent about everything else — no flagging of
missing accent marks, no flagging of phrasing that is valid but slightly unusual, no praise messages
when a sentence was fine. When a single sentence contains several problems, the learner sees the one
or two that matter most rather than an exhaustive list.

**Why this priority**: Restraint is what makes the feature usable over time rather than exhausting,
but it is a refinement of behaviour delivered by Stories 1 and 2, not a separate capability.

**Independent Test**: Send a batch of sentences covering correct text, trivial deviations (missing
diacritic, valid regional word choice) and multi-error text, and confirm corrections appear only for
substantive errors and never exceed two per message.

**Acceptance Scenarios**:

1. **Given** any correction mode is active, **When** the learner sends a sentence whose only defect
   is a missing accent mark or a regionally valid word choice, **Then** no correction is shown.
2. **Given** any correction mode is active, **When** the learner sends a sentence containing four
   substantive errors, **Then** at most two corrections are shown, prioritising the errors that most
   affect comprehension.
3. **Given** the learner spoke rather than typed and the transcription was uncertain, **When** the
   message is evaluated, **Then** no correction is produced for that message.

---

### Edge Cases

- **Repeated failure**: the learner's retry in Strict mode still contains the same error. The system
  corrects at most once more and then continues the conversation regardless, so the learner can never
  be trapped in a correction loop that blocks the scenario.
- **Speech laundering**: transcription tends to render a learner's spoken mistake as fluent,
  well-formed text, so some spoken errors will already be repaired before evaluation. This is an
  accepted limitation. The inverse — inventing a correction for a mistake the learner did not make
  because the transcription mis-heard them — must not happen.
- **Whole message in the native language**: the existing behaviour (a short target-language prompt
  asking the learner to switch) takes precedence; no grammar correction is produced.
- **Very short or fragmentary input** ("sí", "gracias", "mm"): treated as having nothing to correct.
- **Mode changed mid-conversation**: takes effect from the learner's next message only; corrections
  already received remain visible and past messages are not re-evaluated.
- **Evaluation unavailable or slow**: the character's reply is still delivered; the correction is
  omitted silently rather than blocking or failing the conversation turn.
- **Conversation reloaded later**: corrections received earlier are still visible in the transcript.
- **Learner abandons a paused Strict turn** and starts a new conversation: the pause does not persist
  into or block the new conversation.

## Requirements *(mandatory)*

### Functional Requirements

**Setting and scope**

- **FR-001**: System MUST provide a correction mode setting with exactly three values: Off, Gentle,
  and Strict.
- **FR-002**: The setting MUST default to Off, and with it Off the conversation experience MUST be
  identical to the behaviour before this feature existed.
- **FR-003**: The setting MUST persist across sessions and apply to subsequent conversations.
- **FR-004**: A change to the setting MUST take effect from the learner's next message onward, and
  MUST NOT add, remove, or alter corrections attached to messages already in the transcript.
- **FR-005**: Learners MUST be able to change the setting from the application's settings surface and
  receive immediate confirmation that the change took effect.

**Deciding what to correct**

- **FR-006**: When the mode is not Off, the system MUST evaluate each learner-authored message for
  errors before the conversation turn is presented as complete.
- **FR-007**: The system MUST treat as correctable only substantive errors — verb conjugation and
  tense, gender and number agreement, incorrect word choice, and incorrect word order — and MUST NOT
  raise corrections for missing diacritics, regionally valid variation, or phrasing that is correct
  but merely unidiomatic.
- **FR-008**: The system MUST surface at most two corrections for any single learner message,
  ordered by impact on comprehension.
- **FR-009**: When a learner message contains no substantive error, the system MUST show no
  correction and MUST NOT show any affirmation or praise in its place.
- **FR-010**: When a learner message originated from speech and the transcription is uncertain, the
  system MUST NOT produce a correction for that message.

**Gentle mode behaviour**

- **FR-011**: In Gentle mode the character's reply MUST remain in character and MUST contain no words
  of the learner's native language.
- **FR-012**: In Gentle mode the corrected form MUST appear as a natural restatement inside the
  character's reply, and the conversation MUST advance within that same turn.
- **FR-013**: Gentle mode MUST NOT pause the scenario or ask the learner to repeat themselves.

**Strict mode behaviour**

- **FR-014**: In Strict mode the system MUST present, for each correction: what was wrong, the
  corrected sentence, and a prompt for the learner to try again.
- **FR-015**: In Strict mode the explanation MAY be written in the learner's native language.
- **FR-016**: In Strict mode the scenario MUST pause — the character MUST NOT advance the scenario
  until the learner sends another message.
- **FR-017**: When the learner sends their next message after a Strict correction, the conversation
  MUST resume with the preceding context intact.
- **FR-018**: The system MUST NOT correct the same error on more than two consecutive attempts;
  after the second attempt the conversation MUST continue regardless of whether the error persists.

**Presentation**

- **FR-019**: A correction MUST be presented as a distinct element attached to the learner's own
  message, visually distinguishable from character dialogue so it reads as a note from the app rather
  than something the character said.
- **FR-020**: Strict-mode correction text MUST NOT be sent to speech synthesis and MUST never be
  spoken in the character's voice.
- **FR-021**: A Gentle-mode recast forms part of the character's spoken reply and MUST be voiced
  normally along with the rest of that reply.
- **FR-022**: Corrections MUST persist with the conversation and remain visible when the conversation
  is reopened later.
- **FR-023**: The correction element MUST meet the project's accessibility requirements, including
  colour contrast and an accessible label identifying it as learning feedback rather than dialogue.

**Coexistence with existing tools**

- **FR-024**: The existing per-message Grammar, Translate, and Alternative Phrasing tools MUST remain
  available and unchanged in all three modes, including Off.
- **FR-025**: An automatic correction MUST NOT replace, pre-fill, or suppress the result the learner
  gets from invoking the on-demand Grammar tool on the same message.

**Resilience**

- **FR-026**: If correction evaluation fails or exceeds its time budget, the character's reply MUST
  still be delivered and the correction MUST be omitted without presenting an error that interrupts
  the conversation.

### Key Entities

- **Correction Mode Setting**: A single learner-level preference holding one of three values (Off,
  Gentle, Strict). Governs every conversation the learner starts.
- **Correction**: Feedback attached to exactly one learner-authored message. Carries the fragment
  that was wrong, the corrected form, an explanation, the category of error, and the mode under which
  it was produced. A message has zero, one, or two corrections.
- **Learner Message**: An existing conversation message authored by the learner, by speech or typing.
  Gains an association to zero or more corrections and an indication of whether it is awaiting a
  retry.
- **Character Reply**: An existing conversation message authored by the roleplay character. In Gentle
  mode it may carry a recast inside its own text; in Strict mode it is withheld until the learner's
  retry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can find and change the correction mode in under 15 seconds from the
  conversation screen.
- **SC-002**: With the mode Off, 100% of conversation turns are indistinguishable from the pre-feature
  experience — zero corrections, zero added delay, zero visual change.
- **SC-003**: Over a benchmark set of 20 learner sentences — 10 containing a deliberate substantive
  error and 10 fully correct — the system produces a correction for at least 8 of the 10 erroneous
  sentences and for 0 of the 10 correct ones.
- **SC-004**: Corrections arrive together with the character's reply, adding no more than 2 seconds
  to the learner's perceived wait for a turn.
- **SC-005**: Across a full test session, a Strict-mode correction is read aloud in the character's
  voice zero times.
- **SC-006**: 100% of Strict-mode practice sessions reach the end of the scenario without deadlocking
  on a correction the learner cannot satisfy.
- **SC-007**: In an extended session in Gentle mode, zero character replies contain the learner's
  native language.

## Assumptions

These are informed defaults chosen where the description did not specify. Each is a candidate for
review during `/speckit-clarify`.

- **Global, not per-conversation**: the mode is one learner-level preference alongside the existing
  language and voice preferences, not an override set per conversation.
- **Applies to conversation practice only**: both scenario roleplay and open chat are in scope, since
  both are conversation practice with a character. The expression helper is out of scope — its whole
  purpose is answering "how do I say this", where correcting the learner's native-language question
  would be nonsense.
- **Corrections are persisted**, not ephemeral, so they survive a reload and remain part of the
  learner's history.
- **Two attempts is the retry cap** in Strict mode before the conversation moves on regardless.
- **Two corrections is the per-message cap**, chosen to keep feedback actionable.
- **The learner's native language for Strict explanations** is the existing configured native
  language; no new language preference is introduced.
- **No new analytics or progress tracking** is implied by this feature; corrections are shown, not
  scored or aggregated.

## Out of Scope

- Scoring, streaks, or progress metrics derived from correction counts.
- Correcting pronunciation or accent from the audio signal itself.
- Improving transcription accuracy so that spoken errors survive to the correction step.
- Applying correction modes to vocabulary flashcard practice.
- Retroactively correcting conversations recorded before this feature existed.
