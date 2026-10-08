# Feature Specification: Language Switcher in the Header

**Feature Branch**: `009-language-switcher-header`
**Created**: 2026-10-07
**Status**: Draft
**Input**: User description: "can we upgrade the language selection feature? maybe feature a flag next to the language and create an easier way to switch language? Maybe something like duolingo has with the languages being learnt and then languages not being learnt later on in the selection list? also maybe we feature the current language at the top of the screen on the header instead of the awkward placement on the home screen"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner sees and switches their practice language from the header (Priority: P1)

A learner who practises Spanish and German opens the app. At the top of the screen, in the header,
they see the Spanish flag and "Spanish": the language they are practising, without hunting for it.
They want a German conversation today. They select the language in the header, a short list opens,
and they choose German. The list closes, the header now shows the German flag and "German", and the
scenario on the home screen is offered in German. They did not visit Settings or press Save.

The line under the navigation on the home screen ("Practising Spanish · Change in Settings") is gone:
the header replaces it.

**Why this priority**: This is the core of the request. Switching is today a trip to Settings, a
radio choice among every other setting, and a Save, and the current language sits in an awkward line
on the home screen only. A visible header control with a one-choice switch is the change the learner
feels every day.

**Independent Test**: With two or more languages catalogued, open the home screen, read the current
language in the header, switch to another language from the header, and confirm the header, the
saved practice language and the next new conversation all use the new language, with no visit to
Settings.

**Acceptance Scenarios**:

1. **Given** the practice language is Spanish, **When** the learner opens the home screen, **Then**
   the header shows the Spanish flag and the name "Spanish" as the current practice language, and the
   old home-screen line about the practice language is not shown.
2. **Given** the header shows Spanish, **When** the learner opens the language switcher and chooses
   German, **Then** the switcher closes, the header shows German with its flag, and German is the
   saved practice language (it is still German after a reload, and Settings shows German).
3. **Given** the learner has just switched to German, **When** they start a conversation from the
   home screen, **Then** the conversation is in German.
4. **Given** the switcher is open, **When** the learner dismisses it without choosing (Escape, or
   selecting outside it), **Then** it closes and the practice language is unchanged.
5. **Given** the switcher is open, **When** the learner chooses the language that is already
   current, **Then** it closes and nothing changes.
6. **Given** a keyboard-only or screen-reader learner, **When** they reach the header control,
   **Then** it announces the current language and that it opens a language list, the list can be
   opened, moved through and chosen from by keyboard, and focus returns to the control when it closes.

---

### User Story 2 - Languages being learned come first, other languages after (Priority: P2)

A learner opens the switcher. At the top, under **My languages**, are the languages they are
learning: the current one marked as selected, and any other language they have practised. Below,
under **Start a new language**, are the catalogued languages they have never practised. A learner
who has used only Spanish sees Spanish under My languages and German and Italian under Start a new
language. When they choose Italian, it becomes the practice language, and from their first Italian
conversation or flashcard deck onward Italian appears under My languages.

**Why this priority**: This is the Duolingo-style organisation the learner asked for. It keeps the
languages they actually use within one choice as the catalogue grows. Story 1 is still useful with a
flat list, so this builds on it.

**Independent Test**: With activity recorded in Spanish and German only, open the switcher and
confirm Spanish and German appear under My languages, Italian under Start a new language, and that
after an Italian conversation is started Italian moves to My languages.

**Acceptance Scenarios**:

1. **Given** the learner has conversations or flashcard decks in Spanish and German and none in
   Italian, **When** they open the switcher, **Then** Spanish and German are listed under My
   languages and Italian under Start a new language.
2. **Given** the practice language is Italian and the learner has never practised it, **When** they
   open the switcher, **Then** Italian is listed under My languages, marked as current.
3. **Given** a learner on a fresh install with no activity, **When** they open the switcher, **Then**
   only the current (default) language is under My languages and every other catalogued language is
   under Start a new language.
4. **Given** every catalogued language has been practised, **When** the learner opens the switcher,
   **Then** the Start a new language group is not shown.
5. **Given** the learner chooses a language from Start a new language, **When** the switch
   completes, **Then** it behaves exactly like any other switch (Story 1), with no extra setup step.

---

### User Story 3 - Every language is shown with its flag (Priority: P3)

Wherever the app lets the learner pick or read the practice language (the header, the switcher and
the practice-language choice on Settings), each language is shown with a flag beside its name, so
the learner recognises it at a glance. A language added later through the language kit gets its flag
with the rest of its data, with no screen to change.

**Why this priority**: The flag improves recognition but carries no information the name does not.
Stories 1 and 2 work without it.

**Independent Test**: Open the header, the switcher and Settings with three languages catalogued and
confirm each language name has its flag beside it, and that the flag is not read out as a separate
item by a screen reader.

**Acceptance Scenarios**:

1. **Given** Spanish, German and Italian are catalogued, **When** the learner opens the switcher,
   **Then** each language is shown with its own flag beside its name.
2. **Given** the Settings screen, **When** the learner views the practice-language choice, **Then**
   each option shows its flag beside its name.
3. **Given** a screen reader, **When** it reads a language in the header, switcher or Settings,
   **Then** it reads the language name once, not a description of the flag in addition.
4. **Given** a new language is onboarded with the language kit, **When** the onboarding is complete,
   **Then** its flag appears in the header, switcher and Settings without any change to those screens.

---

### Edge Cases

- **Switching while a conversation is open**: a conversation keeps the language it started in. In a
  conversation, podcast episode or flashcard practice session, the header shows that conversation's language and does not offer
  the switcher there, so a switch cannot appear to change an open conversation.
- **Voice not installed for the chosen language**: the switch still happens (practising by text
  works); the learner sees the same plain "voice unavailable" message they already get elsewhere,
  and no other language's voice is used.
- **Saving the switch fails**: the header keeps showing the previous language, the learner sees a
  message saying the language could not be changed and that they can try again, and nothing else
  changes.
- **The language list cannot be loaded**: the header does not show a wrong language; it shows a
  neutral placeholder, and the switcher says the languages could not be loaded.
- **Only one catalogued language**: the header still shows it with its flag; the switcher lists it
  alone (there is nothing to start).
- **Saved practice language no longer catalogued**: the header behaves as it does today for an
  unknown language (shows the code as its name, with no flag) and the switcher offers the catalogued
  languages.
- **Switching from a screen that shows per-language content** (Flashcards, podcast shows): that
  screen shows the new language's content after the switch, as if it had been opened fresh.
- **Narrow screens**: the header control stays usable at phone width; the language name may shorten
  to the flag alone, but the control keeps its accessible name.
- **Unsaved Settings changes**: switching from the header while Settings is open with unsaved edits
  does not discard or silently save those edits; the Settings practice-language choice reflects the
  new language.

## Requirements *(mandatory)*

### Functional Requirements

**Header and switcher**

- **FR-001**: Every top-level screen (Home, Podcasts, Past Chats, Flashcards, its decks and
  analytics screens, Settings) MUST show the current practice language, flag and name, in its header.
- **FR-002**: Selecting the header language MUST open a language switcher listing every catalogued
  practice language.
- **FR-003**: Choosing a language in the switcher MUST make it the saved practice language in one
  choice, with no separate Save, and the header MUST show it as soon as the change is saved.
- **FR-004**: The switch MUST have the same effect as changing the practice language on Settings:
  new conversations, podcast episodes and flashcard screens use the new language, existing
  conversations keep theirs, and each language keeps its own remembered voice.
- **FR-005**: The switcher MUST close on a choice, on Escape and on selecting outside it, and the
  last two MUST leave the practice language unchanged.
- **FR-006**: In a conversation, a podcast episode or a flashcard practice session, the header MUST
  show that activity's language with its flag, read-only, and MUST NOT offer the switcher.
- **FR-007**: The home-screen line "Practising … · Change in Settings" MUST be removed.
- **FR-008**: If saving a switch fails, the app MUST keep showing the previous language and MUST
  tell the learner the language could not be changed and that they can try again.

**Grouping**

- **FR-009**: The switcher MUST list languages in two groups: **My languages** (the current practice
  language plus every language with at least one conversation, podcast episode or flashcard deck)
  first, then **Start a new language** (every other catalogued language).
- **FR-010**: Within My languages, the current language MUST be first and marked as selected; the
  others MUST follow in catalogue order. Start a new language MUST follow catalogue order.
- **FR-011**: An empty group MUST NOT be shown.
- **FR-012**: A language MUST move to My languages once the learner has a conversation, podcast
  episode or flashcard deck in it, without any further action.

**Flags**

- **FR-013**: Every catalogued practice language MUST have a designated flag, held with the rest of
  that language's data, and onboarding a language MUST require one.
- **FR-014**: The flag MUST appear beside the language name in the header, in the switcher and in
  the practice-language choice on Settings.
- **FR-015**: Flags MUST be decorative for assistive technology: the language name is the accessible
  label, and the flag MUST NOT be announced separately.
- **FR-016**: Flags MUST look the same on every supported desktop platform (Linux, macOS, Windows)
  and in light and dark mode.

**Accessibility and design**

- **FR-017**: The header control and the switcher MUST be fully usable by keyboard and screen reader:
  the control announces the current language and that it opens a list, the list is navigable with
  arrow keys, and focus returns to the control when the list closes.
- **FR-018**: The header control MUST meet the app's minimum touch-target size and contrast rules in
  light and dark mode, following the design system.

**Settings**

- **FR-019**: Settings MUST keep its practice-language choice, now with flags, and it MUST stay
  consistent with the header: a change in either is the same saved setting.

### Key Entities *(include if feature involves data)*

- **Practice language**: an existing catalogued language (code, name, catalogue order, voices). It
  gains a **flag**, designated per language as part of its language data.
- **Learner's languages ("My languages")**: not stored on its own; derived from the current practice
  language and the languages of the learner's existing conversations, podcast episodes and flashcard
  decks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From any top-level screen, a learner can change the practice language in at most two
  selections (open the switcher, choose a language), down from opening Settings, choosing, and saving.
- **SC-002**: The current practice language is visible, with its flag, on 100% of top-level screens
  without scrolling.
- **SC-003**: In the switcher, every language the learner has practised appears above every language
  they have not, in 100% of tested combinations of activity.
- **SC-004**: A language onboarded with the language kit shows its flag on the header, switcher and
  Settings with zero changes to those screens.
- **SC-005**: The switch is reflected in the header within 1 second of choosing, on a local install.
- **SC-006**: The header control and switcher pass the app's manual accessibility check (keyboard
  only, screen reader, contrast in light and dark mode).

## Assumptions

- **"Learning" is derived from activity**, as Duolingo's course list is: a language counts as being
  learned when it is current or has at least one conversation, podcast episode or flashcard deck.
  There is no separate "add course" or "remove course" step; removing a language from My languages
  is out of scope.
- **One flag per language**, chosen to match the country of the language's default voice: Spain for
  Spanish, Germany for German, Italy for Italian. Regional variants (e.g. Mexican Spanish) are out of
  scope.
- **The switcher is not offered inside a conversation, podcast episode or flashcard practice
  session**, because those keep their own language; the learner switches from any top-level screen.
- **Flags are images shipped with the app**, not relied on from the operating system, because some
  desktop platforms do not render flag characters; no network access is needed to show them.
- **No new learner data is stored**: the practice language and per-language voice choice are the
  existing settings; the groups are computed from existing records.
- **The shared header is introduced by this feature** for the top-level screens; screens that keep a
  task-specific header (a conversation, a podcast episode, a flashcard practice session) keep it and
  gain only the read-only language display (FR-006).
- The feature is a single-learner local app change; there are no accounts or permissions involved.
