<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump type: MINOR — two new principles added (IV and V).

Modified principles:
  - I. Clean Code          → unchanged
  - II. SOLID Principles   → unchanged
  - III. TDD               → unchanged

Added sections:
  - IV. Simple UI & Good User Experience
  - V. Extensibility & Compartmentalization

Removed sections: N/A

Templates reviewed:
  - .specify/templates/plan-template.md   ✅ — no changes required; Constitution Check is dynamic
  - .specify/templates/spec-template.md   ✅ — no changes required; SC / FR sections compatible
  - .specify/templates/tasks-template.md  ✅ — updated: removed "Tests are OPTIONAL" language that
                                               conflicted with the TDD mandate; test tasks are now
                                               mandatory per the Red-Green-Refactor cycle
  - .specify/templates/checklist-template.md ✅ — dynamic template; no changes required

Follow-up TODOs: None — all placeholders resolved.
-->

# Open-Langua Constitution

## Core Principles

### I. Clean Code

All code MUST be written to be read by humans first and computers second.

- Functions and methods MUST do one thing and do it well; keep them short (≤ 20 lines as a guideline).
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

## Quality Gates

The following gates MUST pass before any feature branch is merged:

- All tests pass (zero failures, zero skips without documented reason).
- New code meets ≥ 90% line coverage.
- No new SOLID violations without documented justification in Complexity Tracking.
- No functions longer than 30 lines without documented justification.
- No commented-out code.
- Linter and formatter report zero errors.
- UI changes MUST pass a manual accessibility check (contrast, touch targets, screen-reader
  labels).
- New feature domains MUST expose a defined interface; no direct cross-module imports.

## Development Workflow

1. Specifications MUST be written and reviewed before implementation begins
   (`/speckit.specify` → `/speckit.plan`).
2. Tasks MUST be generated from the approved plan (`/speckit.tasks`) and worked in priority order.
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

**Version**: 1.1.0 | **Ratified**: 2026-03-15 | **Last Amended**: 2026-03-17
