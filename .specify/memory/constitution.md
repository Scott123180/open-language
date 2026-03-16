<!--
SYNC IMPACT REPORT
==================
Version change: (template) → 1.0.0
New constitution — initial ratification.

Added sections:
- I. Clean Code
- II. SOLID Principles
- III. Test-Driven Development (NON-NEGOTIABLE)
- Quality Gates
- Development Workflow
- Governance

Removed sections: N/A (first version)

Templates reviewed:
- .specify/templates/plan-template.md  ✅ — Constitution Check section is dynamic; no changes needed
- .specify/templates/spec-template.md  ✅ — No conflicts; structure is compatible
- .specify/templates/tasks-template.md ⚠️  — "Tests are OPTIONAL" note conflicts with TDD mandate; updated below

Follow-up TODOs: None
-->

# Open-Langua Constitution

## Core Principles

### I. Clean Code

All code MUST be written to be read by humans first and computers second.

- Functions and methods MUST do one thing and do it well; keep them short (≤ 20 lines as a guideline).
- Names MUST be intention-revealing: variables, functions, and classes should communicate their purpose without requiring a comment.
- Magic numbers and strings MUST be replaced with named constants.
- Code MUST be left cleaner than it was found (Boy Scout Rule).
- Comments MUST explain *why*, never *what*; if a comment is needed to explain *what* the code does, the code MUST be refactored instead.
- Dead code MUST be deleted, not commented out.

**Rationale**: Readable code reduces cognitive load, lowers defect rates, and makes onboarding new contributors faster — critical for an open-source language-learning project.

### II. SOLID Principles

All non-trivial classes and modules MUST adhere to the five SOLID principles:

- **Single Responsibility**: A class or module MUST have one, and only one, reason to change.
- **Open/Closed**: Entities MUST be open for extension but closed for modification; prefer composition over inheritance.
- **Liskov Substitution**: Subtypes MUST be substitutable for their base types without altering correctness.
- **Interface Segregation**: Clients MUST NOT be forced to depend on interfaces they do not use; prefer small, focused interfaces.
- **Dependency Inversion**: High-level modules MUST NOT depend on low-level modules; both MUST depend on abstractions.

Violations MUST be documented in the Complexity Tracking section of the implementation plan with explicit justification.

**Rationale**: SOLID design keeps the codebase flexible and testable as the feature set grows, preventing the tight coupling that makes language-learning apps hard to extend with new exercise types, content sources, or gamification layers.

### III. Test-Driven Development (NON-NEGOTIABLE)

TDD is mandatory on this project. No production code may be written before a failing test exists for it.

- The Red-Green-Refactor cycle MUST be followed strictly:
  1. **Red** — write a failing test that defines the desired behaviour.
  2. **Green** — write the minimum production code to make the test pass.
  3. **Refactor** — clean up code and tests while keeping all tests green.
- Tests MUST be written at the appropriate level: unit tests for isolated logic, integration tests for component interactions, contract tests for public interfaces.
- A feature is NOT complete until all associated tests pass and coverage for new code is ≥ 90%.
- Tests MUST be committed alongside the production code they cover — never after.

**Rationale**: TDD forces clear requirement thinking before implementation, acts as living documentation, and provides a safety net for refactoring in an evolving educational platform.

## Quality Gates

The following gates MUST pass before any feature branch is merged:

- All tests pass (zero failures, zero skips without documented reason).
- New code meets ≥ 90% line coverage.
- No new SOLID violations without documented justification in Complexity Tracking.
- No functions longer than 30 lines without documented justification.
- No commented-out code.
- Linter and formatter report zero errors.

## Development Workflow

1. Specifications MUST be written and reviewed before implementation begins (`/speckit.specify` → `/speckit.plan`).
2. Tasks MUST be generated from the approved plan (`/speckit.tasks`) and worked in priority order.
3. TDD cycle MUST be applied to every implementation task.
4. Each user story MUST be independently testable and demonstrable before moving to the next.
5. Code review MUST verify SOLID compliance and test coverage before merge.

## Governance

This constitution supersedes all other project-level practices and style guides. Any practice not addressed here defaults to clean-code community standards.

**Amendment procedure**:
- MAJOR bump: removal or redefinition of a core principle — requires team consensus and a migration plan.
- MINOR bump: new principle or section added — requires documented rationale.
- PATCH bump: clarifications, wording, or typo fixes — can be merged by any maintainer.

All pull requests and code reviews MUST verify compliance with this constitution. Complexity that violates a principle MUST be justified in the implementation plan's Complexity Tracking table before the plan is approved.

**Version**: 1.0.0 | **Ratified**: 2026-03-15 | **Last Amended**: 2026-03-15
