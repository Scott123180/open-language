# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Open-Language** is a locally-run language learning application built using **SpecKit** (v1.0.1, skills-based integration), a specification-driven development (SDD) framework. All feature work goes through the SDD workflow below.

The application is implemented and running: a FastAPI backend in [backend/app/](backend/app/) and a Vite/React frontend in [frontend/src/](frontend/src/). Features shipped so far: roleplay chat (001), vocabulary flashcards (002), corrective feedback mode (003, experimental), and LLM provider selection with conversation sessions (004). Every AI capability sits behind a provider interface, and the app is local by default: Ollama for the LLM, Piper for TTS, faster-whisper for STT, SQLite for storage. Cloud providers are opt-in — today, Claude as the conversation partner through the learner's signed-in Claude Code. STT and TTS are always local.

Speech-to-text is implemented in [backend/app/services/stt/whisper.py](backend/app/services/stt/whisper.py); see [reference/TRANSCRIPTION_INTEGRATION.md](reference/TRANSCRIPTION_INTEGRATION.md) for the underlying `faster-whisper` + CUDA integration patterns.

## Development Workflow

All features follow a strict spec-first workflow enforced by the constitution. Use these SpecKit slash commands in order:

1. `/speckit-specify` — Write a feature spec from a natural language description
2. `/speckit-clarify` — Resolve ambiguities (max 3 clarification points)
3. `/speckit-plan` — Generate a technical implementation plan (includes a research phase)
4. `/speckit-tasks` — Break the plan into dependency-ordered tasks
5. `/speckit-implement` — Execute implementation in phases
6. `/speckit-checklist` — Validate quality gates before merging
7. `/speckit-analyze` — Cross-artifact consistency check

Also available: `/speckit-converge` (assess the codebase against spec/plan/tasks and append unbuilt
work), `/speckit-constitution`, `/speckit-taskstoissues`, `/speckit-agent-context-update`, and the
`/speckit-git-*` extension commands.

Names are hyphenated. The older dot-separated forms (`/speckit.tasks`) were removed on 2026-08-25;
the `command:` values inside `.specify/extensions.yml` and `.specify/workflows/` still use dots as
logical ids and are converted to hyphens at invocation.

Helper scripts in [.specify/scripts/bash/](.specify/scripts/bash/) back these commands:
- `create-new-feature.sh` — Initialize a new feature branch
- `update-agent-context.sh` — Sync Claude context with current project state
- `check-prerequisites.sh` — Report FEATURE_DIR and which design docs exist
- `setup-plan.sh` / `setup-tasks.sh` — Stage the plan/tasks templates for a feature
- `common.sh` — Shared path resolution, sourced by the others

**Known issue**: `setup-tasks.sh` calls `resolve_template_content`, which is not defined in
`common.sh` (only `resolve_template`, at line 183). `/speckit-tasks` therefore fails at setup with a
misleading "template not found" error; the template is present at
`.specify/templates/tasks-template.md` and can be read directly as a workaround.

## Constitution & Quality Gates

Governance is defined in [.specify/memory/constitution.md](.specify/memory/constitution.md) (v1.2.0, ratified 2026-03-15, amended 2026-09-25). Key non-negotiables:

- **TDD is mandatory** — tests written before implementation, always; test tasks are never optional
- **90% test coverage** minimum, zero skipped tests
- **Function length ≤ 20 lines**, SOLID principles enforced. The gate applies to every new or modified function; a longer one needs a justification in the plan's Complexity Tracking. Existing long functions are brought under the limit when next touched
- **Simple UI** — single primary action per screen, immediate feedback, accessibility required
- **Compartmentalization** — each feature domain has a defined public interface; no direct cross-module imports
- **Provider independence** (Principle VI) — every AI capability (LLM, STT, TTS) sits behind a provider interface, and feature code never imports a concrete provider. The local stack is the default, and cloud providers are opt-in with a notice of what leaves the machine. The app never stores or logs credentials, and never silently falls back to another provider
- Linting must pass before any merge; UI changes require a manual accessibility check
- **Playwright E2E tests are mandatory for all frontend changes** — run `npm run test:e2e` before marking any frontend task complete

## Test-Driven Development (TDD)

TDD is non-negotiable. Every feature begins with a failing test.

**The Red → Green → Refactor cycle:**
1. **Red** — Write a failing test that specifies the desired behavior. Do not write implementation code until the test exists.
2. **Green** — Write the minimum code necessary to make the test pass. No more.
3. **Refactor** — Clean up the code without changing behavior. Tests must still pass.

**Rules:**
- No implementation code without a corresponding test written first
- Tests must be co-located or mirror the source tree (e.g., `tests/unit/`, `tests/integration/`)
- Mock external dependencies (DB, HTTP, file I/O) at boundaries — never deep in business logic
- Test names must describe behavior, not implementation: `test_returns_empty_list_when_no_results`, not `test_method_works`
- Each test covers exactly one behavior; use `Arrange / Act / Assert` structure

## UI Design System

All frontend UI work must follow the design system documented in [docs/design-system.md](docs/design-system.md). Key rules enforced by the design system:

- **Never hardcode hex colors** — use CSS custom property tokens from `index.css`
- **Never hardcode `#fff` as text on a primary background** — use `var(--color-text-on-primary)`
- **Navigation text uses `--color-text`**, not `--color-primary` (avoids the blue-on-dark-blue contrast failure in dark mode)
- **Cards use `--radius-lg` (12px)**, not `--radius` (8px)
- **Shadows use `--shadow-sm/md/lg`** (warm-tinted), not raw `box-shadow` values
- **Back links use `--color-text-muted`**, not `--color-primary`
- The design language is **warm minimal**: stone neutrals + teal primary, Plus Jakarta Sans typeface, generous line heights for reading contexts
- Refer to `docs/design-system.md` for the full token reference, component patterns, dark mode rules, and do/don't guide

## Frontend E2E Testing (Playwright)

All frontend changes **must** be accompanied by Playwright E2E tests and all existing tests must pass before a task is marked complete.

**Test location**: `frontend/e2e/` — one spec file per page/feature area.

**Commands**:
```bash
# Install browsers (first time only)
cd frontend && npx playwright install chromium

# Run all E2E tests (starts dev server automatically)
npm run test:e2e

# Run with browser UI for debugging
npm run test:e2e:headed

# Interactive UI mode
npm run test:e2e:ui

# Debug a specific test
npm run test:e2e:debug
```

**Rules**:
- Every new page or user-facing feature gets a corresponding spec file in `frontend/e2e/`
- All API calls are intercepted via `page.route()` — no real backend required
- SSE streaming endpoints use `route.fulfill({ headers: { 'Content-Type': 'text/event-stream' }, body: ... })` with the helpers in `frontend/e2e/fixtures.ts`
- Test names describe the observable behavior, not implementation details
- New shared mock data and SSE helpers go in `frontend/e2e/fixtures.ts`
- `npm run test:e2e` must pass with zero failures before any frontend PR is merged

## SOLID Principles

All code — backend and frontend — must adhere to SOLID. Violations are grounds to reject a task as incomplete.

**S — Single Responsibility**
Every class and function has exactly one reason to change. A class that both parses input *and* writes to the database violates SRP. Split it.

**O — Open/Closed**
Code is open for extension, closed for modification. Add behavior by subclassing or composing — not by editing existing classes. Use abstract base classes (`abc.ABC`) in Python and interfaces/generics in TypeScript.

**L — Liskov Substitution**
Subtypes must be substitutable for their base type without breaking behavior. If a subclass overrides a method and changes its contract (raises unexpected exceptions, returns a narrower type), it violates LSP.

**I — Interface Segregation**
No class should be forced to implement methods it does not use. Prefer many small, focused interfaces over one large one. In Python, use `Protocol` or `abc.ABC` with minimal method sets. In TypeScript, split large interfaces into composable ones.

**D — Dependency Inversion**
High-level modules must not depend on low-level modules — both depend on abstractions. Inject dependencies via constructor parameters or factory functions. Never instantiate collaborators (DB sessions, HTTP clients, AI clients) inside business logic classes.

## Object-Oriented Programming Conventions

**Class design:**
- Classes encapsulate state and behavior that belong together — avoid anemic models (data bags with no behavior)
- Prefer composition over inheritance; use inheritance only for true IS-A relationships
- Keep constructors simple: set fields, validate inputs, nothing else. Heavy initialization belongs in factory methods or `@classmethod` constructors
- Use `__slots__` on Python dataclasses/value objects where performance matters
- Name classes as nouns (`ConversationRepository`, `TranscriptionEngine`), methods as verbs (`fetch_session`, `transcribe_audio`)

**Encapsulation:**
- All mutable state is private by default (`_field` in Python, `private` in TypeScript)
- Expose state via explicit properties or getter methods, not direct field access from outside the class
- Domain objects validate their own invariants — invalid state must be unrepresentable

**Polymorphism:**
- Use abstract base classes / interfaces to define contracts; depend on the contract, not the concrete type
- Strategy and Repository patterns are the default way to swap implementations (e.g., `WhisperTranscriber` vs `MockTranscriber`)

**Module boundaries:**
- Each feature domain exports a single public interface (service class or set of functions)
- Internal implementation classes are never imported across domain boundaries
- Circular imports are a design error — fix the abstraction, do not add workarounds

## Clean Code Practices

**Naming:**
- Names must reveal intent. If you need a comment to explain a variable name, the name is wrong.
- Use full words, not abbreviations: `conversation_repository`, not `conv_repo` or `cr`
- Booleans are prefixed with `is_`, `has_`, or `can_`: `is_active`, `has_audio`, `can_retry`
- Avoid noise words: `data`, `info`, `manager`, `handler`, `utils` — name what the thing actually does

**Functions:**
- Functions do one thing. If you can describe it with "and", split it.
- Maximum 20 lines. If it's longer, extract a helper.
- No boolean flag parameters (`process(data, True)`) — create two named functions instead
- Arguments: prefer 0–2. More than 3 is a design smell; wrap in a dataclass or config object
- Functions either answer a question (query) or perform an action (command) — never both

**Comments:**
- Code should be self-documenting. Comments explain *why*, never *what*
- A comment that restates the code is noise — delete it
- Use docstrings for public API methods only; keep them concise (one line + params if needed)
- TODO comments must reference a ticket or issue; orphan TODOs are not allowed

**Error handling:**
- Never swallow exceptions silently (`except: pass` is forbidden)
- Raise specific exception types; never raise bare `Exception`
- Validate at system boundaries (API inputs, external service responses); trust internal contracts
- Error messages must describe what happened and what can be done about it

**Code structure:**
- The newspaper rule: high-level logic at the top of a file, details below
- No magic numbers or magic strings — use named constants
- Avoid deep nesting (max 2 levels); early returns and guard clauses flatten logic
- Dead code is deleted immediately — version control preserves history
- Duplication is a design signal: three or more repetitions → extract an abstraction

**Formatting & linting:**
- Python: `black` for formatting, `ruff` for linting — both must pass with zero warnings
- TypeScript: ESLint + Prettier — enforced in CI
- Imports are sorted and grouped (stdlib → third-party → local); no unused imports allowed

## Architecture & Templates

Feature artifacts live alongside the feature branch. Templates at [.specify/templates/](.specify/templates/) define the structure for each artifact:

| Template | Purpose |
|----------|---------|
| `spec-template.md` | User scenarios, functional requirements, edge cases, prioritized stories (P1/P2/P3) |
| `plan-template.md` | Technical context, constitution compliance gate, research/design/contract phases |
| `tasks-template.md` | Phased tasks (Setup → Foundational → Story-level), dependency ordering, exact file paths |
| `checklist-template.md` | Quality validation before completion |

## Python Environment

**Always use a virtual environment** — never install packages into the system Python or use `--break-system-packages`.

- The backend venv lives at `backend/.venv/`
- Create it if missing: `python3 -m venv backend/.venv`
- Activate before any pip commands: `source backend/.venv/bin/activate` (or use the full path `backend/.venv/bin/pip`)
- Install deps: `backend/.venv/bin/pip install -e ".[dev]"`
- Run tests and tools through the venv: `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff`, `backend/.venv/bin/black`

Never run `pip install --break-system-packages`, `pip install --user`, or bare `pip install` outside a venv.

## Speech-to-Text Integration

When implementing transcription features, refer to [reference/TRANSCRIPTION_INTEGRATION.md](reference/TRANSCRIPTION_INTEGRATION.md) which documents:
- `AudioRecorder` class using `sounddevice` (16kHz mono float32)
- `TranscriptionEngine` class using `faster-whisper` with automatic CUDA/CPU fallback
- CUDA library preloading strategy and threading/asyncio patterns
- Dependencies: `faster-whisper`, `sounddevice`, `scipy`, `numpy` (plus optional NVIDIA CUDA packages)

## Active Technologies

**Backend** — Python (`requires-python = ">=3.11"`; the `backend/.venv` runs 3.12.3): FastAPI,
Uvicorn, SQLAlchemy 2.0 over SQLite, `faster-whisper` 1.2.1 (STT), Piper (TTS), the `ollama` client
(llama3.1), ffmpeg/pydub for audio conversion. Tested with pytest + pytest-cov.

**Optional runtime prerequisite** — the Claude Code CLI (`claude`, verified with 2.1.283), only when a
learner selects Claude. It is spawned as a subprocess, never a Python dependency, and the default test
suite needs neither it nor Ollama (`-m claude_live` runs the opt-in live tests).

**Frontend** — TypeScript 5.4 / React 18.3, Vite, react-router-dom v6, TanStack Query v5 (used by the
flashcards pages), Recharts (analytics), react-markdown. Tested with Vitest + Testing Library and
Playwright.

**Storage** — SQLite with WAL mode and foreign keys enabled. Schema changes are additive: new tables
via `create_all()`, new columns via `_add_column_if_missing()` in
[backend/app/database.py](backend/app/database.py). There is no migration framework.

**Domain modules** — `backend/app/flashcards/` (002) is the reference pattern for a compartmentalised
feature: its own models, schemas, router, and `services/` behind a storage ABC.
`backend/app/corrections/` (003) follows it, and adds a strategy seam: `build_correction_strategy()`
in its `__init__.py` is the only place a correction-mode string becomes behaviour.
`build_llm_provider()` in [backend/app/services/llm/registry.py](backend/app/services/llm/registry.py)
(004) is the same seam for providers: the only place a provider id (`ollama`, `claude`) becomes a
concrete class. Provider ids are listed once, in `services/llm/catalog.py`. Feature code depends on
`LLMProvider` / `StructuredLLMProvider` / `SessionCapableProvider` through `services/factory.py`.
`backend/app/services/conversation/` (004) is a domain service with no tables or routes:
`ConversationEngine` produces the next roleplay or helper reply through a bounded, expiring session
pool, with saved history as the source of truth.

## Recent Changes
- **004-llm-provider-selection**: the learner chooses the conversation partner — Ollama (local, the
  default) or Claude through their signed-in Claude Code, with a model and an effort level — on the
  Settings screen, with no restart. Adds the provider catalogue and registry, the isolated
  `claude -p` adapter (`services/llm/claude_code/`), conversation sessions (`services/conversation/`)
  that keep Ollama loaded and a Claude process alive between turns, provider errors surfaced as
  actionable messages (JSON endpoints return 503), and two `app_settings` columns
- **003-corrective-feedback-mode** (in progress): Off/Gentle/Strict grammar correction during
  conversation practice; adds a `corrections` domain module, transcription-confidence gating, and a
  `StructuredLLMProvider` ABC for constrained JSON output. **Shipped as experimental**: detection is
  good but restraint is not — `llama3.1:8b` falsely flags correct sentences, so the Settings screen
  carries a warning and a larger model is on the roadmap (docs/architecture.md § "Open items")
- **002-vocabulary-flashcards**: flashcard practice modes, smart deck generation, spaced repetition,
  and an analytics dashboard; added Recharts and 7 tables
- **001-speak-roleplay-chat**: the original roleplay conversation feature — scenarios, streaming
  chat over SSE, STT/TTS, and the per-message learning tools
