# Feature Specification: Language Onboarding Kit

**Feature Branch**: `008-language-onboarding-kit`
**Created**: 2026-10-06
**Status**: Draft
**Input**: User description: "So, you've seen what it takes now to add another language, German. This process must have involved a lot of repeated steps. And so, what I want you to do is to create a feature for adding new languages. Language support, for example, we might be adding Italian as the next language supported. And what I want to do is to have this language support. And you can still use an LLM and a bunch of other stuff. But we need a repeatable pattern for adding these languages. So, it can be a skill, but heavily lean in on the scripting part of things as well. This is to save token cost and make things faster. And so, there may be a bunch of tasks that are repetitive between adding different languages. And also, we may eventually add more features as well. This skill should be updated with scripts. And yeah, it should be updated when the new features are added. If anything else is added, it needed to be added for individual languages."

## Overview

Adding German (006) built the app's multi-language foundation: conversations carry their own
language, every aid takes the language from the conversation, flashcards and voices are scoped by
language, and the language catalogue is the one place a language is defined. Podcasts (007) then
added more per-language data (host name banks, guest labels, a voice-sample line).

What remains when the next language arrives is a known, repeated list of steps:

- choosing and fetching the language's local voices, and listing them where the app and the setup
  script expect them;
- writing the language's catalogue entry (name, default voice, host names by voice gender, guest
  labels, the voice-sample line);
- writing an evaluation set (scripted learner turns for every scenario, dictation sentences that
  exercise the language's special letters, a loanword allowlist);
- running the language-adherence and transcription benchmarks and recording the results and the
  human review sheet;
- running the test suites and recording what was and was not checked.

This feature turns that list into a **language onboarding kit**: an agent skill that holds the
procedure, backed by scripts that do every mechanical step. The agent (or a person) only writes
what needs judgement or knowledge of the language, in one place; scripts check it, apply it, and
report. The kit also holds a **registry of per-language requirements**, so when a future feature
adds something every language must have, the kit is updated in the same change, and every existing
language is checked for it.

## Clarifications

### Session 2026-10-06

- Q: Does this feature ship the kit only, or also Italian? → A: Both. Italian is onboarded with the
  kit as the feature's acceptance test and ships as a supported practice language (FR-024).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintainer adds a new practice language with the kit (Priority: P1)

The maintainer wants learners to be able to practise Italian. They ask their coding agent to add
Italian using the kit. The agent runs the kit's first step, which checks that Italian can be
supported locally: that local voices exist for it, that the speech recogniser handles it, and that
the word lists the adherence check needs cover it. It then lists the candidate voices with their
gender and quality. The kit writes a blank language pack for Italian that lists every required item
with a short description and an example from an existing language. The agent fills in only the
Italian content: name, chosen voices, host names, guest labels, sample line, evaluation turns,
dictation sentences and loanword allowlist. The kit validates the pack, then applies it: it adds the
catalogue entry, the voice list entries, the setup script's voice downloads and the evaluation set,
fetches the voices, and runs the test suites. It ends with a short report. After the change is
merged and the app restarted, a learner opens Settings, sees Italian as a practice language, and
holds a conversation in it, with every learning tool, flashcards and podcasts working as they do in
Spanish and German.

**Why this priority**: This is the feature. A repeatable, mostly scripted path from "we want
language X" to a working language is the whole point; everything else supports it.

**Independent Test**: Starting from a clean branch, onboard one new language with the kit. Count
the files the agent edited by hand (only the language pack), confirm every other change came from a
script, and confirm the new language works end to end in the app.

**Acceptance Scenarios**:

1. **Given** a language that is not in the catalogue, **When** the kit's prerequisite step runs,
   **Then** it reports whether local voices, speech recognition and the adherence word lists cover
   the language, and lists each candidate voice with its gender, region and quality.
2. **Given** the prerequisites pass, **When** the kit scaffolds the language, **Then** it creates
   one language pack listing every item in the per-language requirement registry, each with its
   description, rules and an example from an existing language.
3. **Given** a filled language pack, **When** the kit validates it, **Then** every rule in the
   registry is checked and each failure names the item, the rule and what to change.
4. **Given** a valid language pack, **When** the kit applies it, **Then** all app, setup and test
   changes are made by scripts, and no file other than the language pack is edited by hand.
5. **Given** the language is applied, **When** the learner selects it in Settings, **Then** it
   behaves as German does: conversations, learning tools, corrections, levels, flashcards,
   podcasts with cast hosts, summaries and voices all work in that language.
6. **Given** an onboarding run, **When** it finishes, **Then** the kit writes a report that lists
   what was applied, which checks passed, which benchmarks were run and their results, and what was
   not checked.

---

### User Story 2 - The kit tells exactly what a language is missing (Priority: P1)

At any time, the maintainer (or the agent) runs the kit's completeness check, for one language or
for all of them. It checks each catalogued language against the per-language requirement registry
and prints a short table: each language, each requirement, and pass or fail with the reason. Spanish
and German pass from the day the kit ships.

**Why this priority**: Validation is what makes the pattern trustworthy and cheap. It is also how
the agent knows what to do next without reading application code.

**Independent Test**: Run the check on the current app: Spanish and German pass. Remove one required
item from German's data (for example, empty its female host names): the check fails and names
German, the item and the rule.

**Acceptance Scenarios**:

1. **Given** the kit is introduced, **When** the completeness check runs, **Then** Spanish and
   German pass every requirement.
2. **Given** a language with one required item missing or invalid, **When** the check runs,
   **Then** it fails, names that language, item and rule, and passes every other item.
3. **Given** the check runs on every language, **When** it finishes, **Then** its output fits on
   one screen for the current number of languages and ends with an overall pass or fail.
4. **Given** the check runs, **When** it inspects the app, **Then** it changes nothing.

---

### User Story 3 - Benchmarks run for any language with one command (Priority: P2)

The maintainer wants to know whether the local model stays in the new language and whether speech
in it is transcribed well, as was measured for German. They run the kit's benchmark step with the
language code. It runs the adherence benchmark (scripted turns across every scenario, checked for
words from other languages) and the transcription benchmark (dictation sentences spoken by the
language's local voices), then writes a results file and a review sheet of flagged replies for a
person to judge, in the same form as German's.

**Why this priority**: Benchmarks tell the maintainer whether a language is ready or should be
marked experimental. A language is usable without them, so this follows the core path.

**Independent Test**: Run the benchmark step for German. It produces results in the same format and
on the same evaluation data as 006's recorded run. Run it for a newly onboarded language: it
produces the same files for that language, with no benchmark code written for it.

**Acceptance Scenarios**:

1. **Given** a language with a complete evaluation set, **When** the benchmark step runs, **Then**
   it runs both benchmarks for that language and writes a results file and a review sheet in the
   language's feature folder.
2. **Given** German, **When** the benchmark step runs, **Then** it uses German's existing
   evaluation set and the existing thresholds (at least 95% of 50 replies free of foreign words; at
   least 18 of 20 dictation sentences transcribed acceptably).
3. **Given** a benchmark misses its threshold, **When** the step finishes, **Then** the results
   and review sheet are still written in full, and the report lists the miss as an open item.
4. **Given** the local model or the voices are not available, **When** the benchmark step runs,
   **Then** it stops with a message naming what is missing and how to get it, and writes nothing.

---

### User Story 4 - The kit stays current as features add per-language needs (Priority: P2)

Later, a new feature needs something per language, for example a set of greeting phrases per
language for a new warm-up mode. The feature's author adds a requirement to the kit's registry in
the same change: what it is, its rules, how it is validated, and how it is applied. The completeness
check then fails for every existing language until that item is filled. The kit's backfill step
lists the missing items per language and scaffolds a small pack with only those items, so the agent
fills just the new content, and the kit applies it.

If an author adds per-language data to the app without adding it to the registry, an automated
test fails and says that the kit must be updated.

**Why this priority**: Without this the kit goes stale after the next feature and the repeated
steps creep back. It matters as soon as the next per-language feature lands, not before.

**Independent Test**: Add a sample per-language field to the language data without registering it:
the guard test fails with a message that points to the registry. Register it: the completeness check
fails for Spanish and German, backfill scaffolds a pack with only that item for each, and after it
is filled and applied, the check passes.

**Acceptance Scenarios**:

1. **Given** a new per-language item is added to the registry, **When** the completeness check runs,
   **Then** every language that lacks it fails on that item only.
2. **Given** some languages are missing items, **When** the backfill step runs, **Then** it
   scaffolds, for each such language, a pack that holds only the missing items.
3. **Given** a filled backfill pack, **When** the kit applies it, **Then** only those items are
   added, and every other part of the language is left unchanged.
4. **Given** per-language data is added to the app outside the registry, **When** the test suite
   runs, **Then** a test fails and its message names the unregistered item and the registry.
5. **Given** a new requirement is registered, **When** the skill's instructions are read, **Then**
   the requirement appears in them without anyone editing the instructions by hand.

---

### Edge Cases

- **Language already catalogued**: the scaffold step refuses, says the language exists, and points
  to the completeness check and backfill.
- **English as a practice language**: refused, because English is the language explanations are
  written in.
- **No local voice for the language**: the prerequisite step stops before any change and says so.
  The kit never gives a language another language's voice (Principle VI; 006 FR-018).
- **Voices of only one gender**: allowed. The kit warns that podcasts will cast hosts of one gender
  only, and the pack needs host names only for the genders that have a voice.
- **Speech recogniser does not support the language**: the prerequisite step stops before any
  change.
- **No word list for the adherence check**: the language can still be onboarded. The adherence
  benchmark is marked "not run" with the reason, and the report lists it as an open item.
- **Scripts not supported by the kit**: a language written right to left, or without spaces between
  words (for example Arabic, Japanese or Chinese), is refused by the prerequisite step with an
  explanation, because the app's text handling and the adherence check assume left-to-right text
  with spaced words.
- **Regional variants**: a language is one catalogue entry with one code (for example `pt`), and may
  have voices from several regions (as Spanish has Spain and Argentina). Two variants of one
  language as separate practice languages are out of scope.
- **Invalid pack content**: duplicate host names, a sample line without exactly one `{name}`, an
  empty guest-label list, a scenario with fewer scripted turns than required, dictation sentences
  without any of the language's special letters, or a default voice not among the chosen voices.
  Validation names each problem; nothing is applied.
- **Interrupted or repeated run**: applying is all or nothing. Re-running any step on a language
  that is already complete reports "nothing to do" and changes nothing.
- **Network unavailable**: voice discovery and download need the network and say so. Validation,
  applying (except fetching voices) and the completeness check work offline.
- **Existing learner data**: onboarding a language never changes stored conversations, words, decks,
  practice history or settings. The current practice language stays selected.

## Requirements *(mandatory)*

### Functional Requirements

**The kit**

- **FR-001**: The kit MUST be an agent skill with a step-by-step procedure for onboarding a
  language, a step for checking completeness, a benchmark step and a backfill step.
- **FR-002**: Every step that does not need judgement or knowledge of the language MUST be done by
  a script, not by the agent: prerequisite checks, voice discovery and download, scaffolding,
  validation, applying changes, running tests and benchmarks, and writing reports.
- **FR-003**: The agent MUST be able to complete an onboarding run using only the skill's
  instructions and the scripts' output, without reading application source code.
- **FR-004**: Script output MUST be short and structured: a summary line per step, then only the
  items that need attention, so that an agent spends few tokens reading it.
- **FR-005**: Every script MUST support a dry run that reports what it would change without
  changing anything.
- **FR-006**: Every step MUST be safe to repeat: re-running it on a language where it has already
  been done changes nothing and says so.

**Per-language requirement registry**

- **FR-007**: The kit MUST hold one registry of everything a practice language needs. Each entry
  MUST state what the item is, which feature needs it, the rules it must satisfy, and whether it is
  written by the agent, chosen from options the scripts list, or derived by a script.
- **FR-008**: The registry MUST cover, at minimum, everything 006 and 007 need per language: the
  code and English name; the voices (at least one) and the default voice; host names for each voice
  gender present; guest labels; the voice-sample line; scripted learner turns for every scenario;
  dictation sentences; a loanword allowlist for the adherence check.
- **FR-009**: The language pack the scaffold step writes MUST be generated from the registry, so
  that a new registry entry appears in new packs, in validation and in the skill's instructions with
  no other edit.
- **FR-010**: An automated test MUST fail when the app's per-language data has an item that the
  registry does not list, and its message MUST name the item and say that the registry needs an
  entry for it.

**Prerequisites and voices**

- **FR-011**: The prerequisite step MUST check, before any change, that the language is not already
  catalogued, is not the explanation language, is written left to right with spaced words, is
  supported by the local speech recogniser, and has at least one local voice.
- **FR-012**: The prerequisite step MUST list the language's available local voices with gender,
  region and quality, so that the agent chooses from facts rather than from memory.
- **FR-013**: The prerequisite step MUST report, without stopping, whether the adherence check's
  word lists cover the language.

**Validation and applying**

- **FR-014**: Validation MUST check every registry rule and report each failure with the item, the
  rule and what to change. Nothing is applied while any failure remains.
- **FR-015**: Applying a valid pack MUST add the language to the language catalogue, to the voice
  list, to the setup script's voice downloads and to the evaluation data, and MUST fetch the
  language's voices.
- **FR-016**: Applying MUST be all or nothing: if any part fails, no part is left changed.
- **FR-017**: Applying MUST NOT change any other language's data, any stored learner data, or the
  learner's selected practice language.
- **FR-018**: After applying, the kit MUST run the backend and frontend test suites and the linters,
  and report their results.
- **FR-019**: A language added by the kit MUST need no language-specific application code: the app
  MUST offer it everywhere it offers Spanish and German, from the catalogue alone.

**Completeness check**

- **FR-020**: The completeness check MUST check one language or all catalogued languages against the
  registry, report pass or fail per language and item with a reason, and change nothing.
- **FR-021**: Spanish and German MUST pass the completeness check when the kit ships, with their
  existing data unchanged.

**Benchmarks**

- **FR-022**: The benchmark step MUST run the adherence and transcription benchmarks for any
  catalogued language from its evaluation data, with the thresholds 006 used, and write a results
  file and a human review sheet in the same form as 006's.
- **FR-023**: German's existing benchmarks MUST become runs of the language-independent benchmarks
  on German's evaluation data, producing the same results format.

**Scope**

- **FR-024**: This feature MUST ship Italian as a supported practice language, onboarded with the
  kit as its acceptance test: Italian's pack is the only hand-written change, its voices are
  fetched, its benchmarks are run and recorded, and its onboarding report is kept with the feature.

**Keeping the kit current**

- **FR-025**: The backfill step MUST list, per language, the registry items it lacks, and scaffold a
  pack holding only those items.
- **FR-026**: The development workflow documents (project instructions and the plan template's
  constitution check) MUST state that a feature adding per-language data registers it in the kit in
  the same change.

**Reporting**

- **FR-027**: Each onboarding or backfill run MUST write a report in the language's feature folder:
  what was applied, test and lint results, benchmark results or the reason they were not run, open
  items, and what was not checked (for example, a human listening test or a screen-reader pass).

### Key Entities

- **Per-language requirement**: one thing every practice language must have. Attributes: name,
  description, the feature that needs it, its rules, who produces it (agent-written, chosen from
  listed options, or script-derived), and an example from an existing language.
- **Requirement registry**: the full list of per-language requirements. It drives the language pack
  template, validation, the completeness check, backfill and the skill's instructions.
- **Language pack**: the content one language supplies for the registry's requirements. A full pack
  onboards a language; a partial pack backfills missing items. It is the only thing written by hand
  in an onboarding run.
- **Voice candidate**: a local voice available for a language, with its gender, region and quality.
- **Onboarding report**: the record of one run: the language, the steps run, what was applied, test
  and benchmark results, open items and what was not checked.
- **Benchmark result**: for one language and run, the adherence and transcription figures against
  their thresholds, the per-item detail, and the review sheet of flagged replies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In an onboarding run, the only file edited by hand is the language pack. Every other
  changed file is written by a kit script (checked against the run's change list).
- **SC-002**: An onboarding run, from the prerequisite step to a passing completeness check with
  tests run, takes under 30 minutes of working time, excluding voice download and benchmark run
  time.
- **SC-003**: In an onboarding run, the agent opens no application source file; it reads only the
  skill's instructions, the language pack and script output (checked from the session record).
- **SC-004**: The completeness check catches 100% of seeded omissions: removing or breaking any one
  registry item for any one language makes the check fail and name that item and language.
- **SC-005**: The guard test catches 100% of seeded unregistered per-language items.
- **SC-006**: Re-running every step on a completed language changes no file.
- **SC-007**: When the kit ships, Spanish and German pass the completeness check, every existing
  test passes, and the benchmark step run on German uses 006's evaluation data unchanged and writes
  its results and review sheet in 006's format.
- **SC-008**: A language onboarded with the kit works end to end in the app: a learner can select
  it, hold a spoken conversation, use every learning tool, practise flashcards and listen to a
  podcast in it, with no language-specific application code added.
- **SC-009**: Onboarding a language leaves every pre-existing stored conversation, word, deck,
  practice record and setting unchanged.

## Assumptions

- **Users of the kit** are the maintainer and their coding agent. Learners never see the kit; they
  see only the language it adds.
- **The agent writes the language content.** "You can still use an LLM" is read as: the coding
  agent running the skill writes the language pack (names, labels, sample line, evaluation
  sentences) from its knowledge of the language. The app's own local model is used only by the
  benchmarks.
- **006 and 007 left no language-specific code paths** beyond the language data the registry
  covers, and a unit test already forbids hard-coded language codes. If planning finds a remaining
  hard-coded per-language path, removing it is part of this feature.
- **The frontend is driven by the language catalogue**, so a new language needs no frontend change.
  The kit still runs the frontend and end-to-end tests to confirm it.
- **Scenarios, show premises and podcast personalities stay English interface text**, as in 006 and
  007, so they need no translation per language.
- **Explanations stay in English.** Adding another explanation language is out of scope.
- **Benchmark thresholds are 006's.** A missed threshold does not block onboarding; it is recorded
  as an open item, as German's transcription result was, and the maintainer decides whether to ship.
- **The local voice library and the speech recogniser are the ones the app already uses**, and the
  voice library publishes a catalogue the prerequisite step can read.
- **Removing a language** from the app is out of scope.
- **Italian is the first language onboarded with the kit.** Its benchmark results are recorded
  against 006's thresholds; a miss is an open item, as for German, not a reason to hold it back.
