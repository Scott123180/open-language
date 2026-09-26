<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0
Bump type: MINOR — one new principle (VI) and one new quality gate. The other edits are
corrections: a title typo, removed command names, and an internal contradiction on function length.

Modified principles:
  - I. Clean Code          → function-length rule restated as a hard limit of 20 lines, with longer
                             functions allowed only with documented justification (was "≤ 20 lines
                             as a guideline", contradicting the 30-line quality gate)
  - II. SOLID Principles   → unchanged
  - III. TDD               → unchanged
  - IV. Simple UI & UX     → unchanged
  - V. Extensibility       → unchanged

Added sections:
  - VI. Provider Independence (local by default, cloud opt-in, no credentials held, no silent
    fallback)
  - Quality Gates: "New AI capabilities and providers MUST satisfy Principle VI"

Modified sections:
  - Title: "Open-Langua Constitution" → "Open-Language Constitution" (typo)
  - Quality Gates: function-length gate 30 → 20 lines, scoped to new or modified functions so
    that existing code is brought into line when touched (Boy Scout Rule) rather than failing every
    branch at once. At amendment time 45 of 337 backend functions exceed 20 lines and 20 exceed 30,
    so the old 30-line gate was not being enforced either.
  - Development Workflow: /speckit.specify, /speckit.plan, /speckit.tasks → /speckit-specify,
    /speckit-plan, /speckit-tasks (the dot forms were removed on 2026-08-25)

Removed sections: N/A

Templates reviewed (not modified by this command):
  - .specify/templates/plan-template.md      ✅ — Constitution Check is filled dynamically; picks up VI
  - .specify/templates/spec-template.md      ✅ — no changes required
  - .specify/templates/tasks-template.md     ✅ — no changes required
  - .specify/templates/checklist-template.md ✅ — dynamic; no changes required

Dependent documents needing follow-up (outside this command's scope):
  - CLAUDE.md — cites "v1.1.0, ratified 2026-03-15" and lists the non-negotiables; update to v1.2.0
    and add Principle VI
  - specs/004-llm-provider-selection/plan.md — add a Principle VI row to the Constitution Check
    table (004 already satisfies it: FR-004, FR-010/011, FR-026, FR-029)

Follow-up TODOs: None — all placeholders resolved. Template resolution was done by reading
.specify/templates/constitution-template.md directly: resolve-template.sh fails on the known
missing resolve_template_content function, and that file is the only layer in the stack.
-->

# Open-Language Constitution

## Core Principles

### I. Clean Code

All code MUST be written to be read by humans first and computers second.

- Functions and methods MUST do one thing and do it well, and MUST NOT exceed 20 lines. A longer
  function is permitted only with a documented justification (see Quality Gates).
- Names MUST be intention-revealing: variables, functions, and classes should communicate their
  purpose without requiring a comment.
- Magic numbers and strings MUST be replaced with named constants.
- Code MUST be left cleaner than it was found (Boy Scout Rule).
- Comments MUST explain *why*, never *what*; if a comment is needed to explain *what* the code does,
  the code MUST be refactored instead.
- Dead code MUST be deleted, not commented out.

**Rationale**: Readable code reduces cognitive load, lowers defect rates, and makes onboarding new
contributors faster — critical for an open-source language-learning project.

### II. SOLID Principles

All non-trivial classes and modules MUST adhere to the five SOLID principles:

- **Single Responsibility**: A class or module MUST have one, and only one, reason to change.
- **Open/Closed**: Entities MUST be open for extension but closed for modification; prefer
  composition over inheritance.
- **Liskov Substitution**: Subtypes MUST be substitutable for their base types without altering
  correctness.
- **Interface Segregation**: Clients MUST NOT be forced to depend on interfaces they do not use;
  prefer small, focused interfaces.
- **Dependency Inversion**: High-level modules MUST NOT depend on low-level modules; both MUST
  depend on abstractions.

Violations MUST be documented in the Complexity Tracking section of the implementation plan with
explicit justification.

**Rationale**: SOLID design keeps the codebase flexible and testable as the feature set grows,
preventing the tight coupling that makes language-learning apps hard to extend with new exercise
types, content sources, or gamification layers.

### III. Test-Driven Development (NON-NEGOTIABLE)

TDD is mandatory on this project. No production code may be written before a failing test exists
for it.

- The Red-Green-Refactor cycle MUST be followed strictly:
  1. **Red** — write a failing test that defines the desired behaviour.
  2. **Green** — write the minimum production code to make the test pass.
  3. **Refactor** — clean up code and tests while keeping all tests green.
- Tests MUST be written at the appropriate level: unit tests for isolated logic, integration tests
  for component interactions, contract tests for public interfaces.
- A feature is NOT complete until all associated tests pass and coverage for new code is ≥ 90%.
- Tests MUST be committed alongside the production code they cover — never after.

**Rationale**: TDD forces clear requirement thinking before implementation, acts as living
documentation, and provides a safety net for refactoring in an evolving educational platform.

### IV. Simple UI & Good User Experience

User interfaces MUST be simple, purposeful, and immediately learnable.

- Every screen or view MUST have a single primary action; secondary actions MUST be visually
  subordinate.
- UI MUST provide immediate, clear feedback for every user action (loading states, success,
  errors).
- Error messages MUST be written in plain language and MUST tell the user what to do next — not
  just what went wrong.
- Interactions MUST be consistent: the same gesture, affordance, or control MUST always produce
  the same result across the application.
- Flows MUST be designed mobile-first and MUST remain usable at any viewport size.
- Accessibility MUST NOT be an afterthought: contrast ratios, touch target sizes, and screen-
  reader semantics are non-negotiable quality requirements, not optional polish.

**Rationale**: A language-learning application is only effective if learners can focus on the
language, not the interface. Friction in the UI directly reduces learning outcomes.

### V. Extensibility & Compartmentalization

The system MUST be designed so that new exercise types, content sources, languages, and
integrations can be added without modifying existing modules.

- Each feature domain (e.g., vocabulary, grammar, listening, transcription) MUST be encapsulated
  in its own module with a clearly defined public interface; cross-domain coupling MUST go through
  that interface only.
- Plugin / extension points MUST be declared as abstractions (protocols, interfaces, or abstract
  base classes) before any concrete implementation is written.
- Shared state MUST be minimised; prefer passing data explicitly over relying on global or
  ambient context.
- Adding a new content type or exercise MUST NOT require changes to existing, unrelated modules
  (Open/Closed reinforcement at the architectural level).
- Feature flags or capability checks MUST be the only mechanism for toggling in-development
  functionality — never `if debug:` guards scattered through domain logic.

**Rationale**: Language learning is an inherently open-ended domain. The application will need to
accommodate new languages, pedagogical approaches, and third-party content over time. Tight
compartmentalisation makes that growth additive, not disruptive.

### VI. Provider Independence

Every AI capability MUST be replaceable without touching the features that use it, and the learner
MUST always know, and choose, where their words go.

- **Behind an interface.** Every AI capability (language model, speech-to-text, text-to-speech, and
  any future one) MUST sit behind a provider interface. Feature code MUST NOT import a concrete
  provider. A provider identifier MUST become behaviour in exactly one place, a registry or factory,
  and nowhere else.
- **Local by default, cloud opt-in.** The fully local stack MUST be the default configuration. A
  provider that sends data off the learner's machine MUST be used only after the learner explicitly
  selects it, and selecting it MUST show a plain-language notice of what data leaves the machine
  and what stays.
- **No credentials held.** The application MUST NOT store, log, or return provider credentials.
  Authentication MUST be delegated to the provider's own tooling, and the application MAY expose
  only whether a provider is usable, never the credential or account details behind it.
- **No silent fallback.** The provider the learner selected MUST be the one used. When it fails,
  the learner MUST be told what happened and what to do next (Principle IV). The application MUST
  NOT quietly switch to a different provider.

**Rationale**: Practising a language means saying clumsy, personal things thousands of times, which
is why the local stack is the default. A swappable provider layer lets the learner trade privacy for
capability knowingly rather than by accident, and lets new backends be added without touching any
feature (Principle V applied to AI services).

## Quality Gates

The following gates MUST pass before any feature branch is merged:

- All tests pass (zero failures, zero skips without documented reason).
- New code meets ≥ 90% line coverage.
- No new SOLID violations without documented justification in Complexity Tracking.
- No new or modified function longer than 20 lines without documented justification in Complexity
  Tracking. Existing longer functions are brought within the limit when next modified.
- No commented-out code.
- Linter and formatter report zero errors.
- UI changes MUST pass a manual accessibility check (contrast, touch targets, screen-reader
  labels).
- New feature domains MUST expose a defined interface; no direct cross-module imports.
- New AI capabilities and new providers MUST satisfy Principle VI.

## Development Workflow

1. Specifications MUST be written and reviewed before implementation begins
   (`/speckit-specify` → `/speckit-plan`).
2. Tasks MUST be generated from the approved plan (`/speckit-tasks`) and worked in priority order.
3. TDD cycle MUST be applied to every implementation task — test tasks are never optional.
4. Each user story MUST be independently testable and demonstrable before moving to the next.
5. Code review MUST verify SOLID compliance, test coverage, and UI/UX quality gates before merge.
6. New modules MUST document their public interface contract before implementation begins.

## Governance

This constitution supersedes all other project-level practices and style guides. Any practice not
addressed here defaults to clean-code community standards.

**Amendment procedure**:
- MAJOR bump: removal or redefinition of a core principle — requires team consensus and a
  migration plan.
- MINOR bump: new principle or section added — requires documented rationale.
- PATCH bump: clarifications, wording, or typo fixes — can be merged by any maintainer.

All pull requests and code reviews MUST verify compliance with this constitution. Complexity that
violates a principle MUST be justified in the implementation plan's Complexity Tracking table
before the plan is approved.

**Version**: 1.2.0 | **Ratified**: 2026-03-15 | **Last Amended**: 2026-09-25
