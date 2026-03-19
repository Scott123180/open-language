# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Open-Language** is a language learning application being built using **SpecKit** (v0.3.0), a specification-driven development (SDD) framework. The repository currently contains the project scaffolding, governance rules, and workflow automation — application code is generated through the SDD workflow.

The application will incorporate speech-to-text features (see [reference/TRANSCRIPTION_INTEGRATION.md](reference/TRANSCRIPTION_INTEGRATION.md) for integration patterns using `faster-whisper` with CUDA).

## Development Workflow

All features follow a strict spec-first workflow enforced by the constitution. Use these SpecKit slash commands in order:

1. `/speckit.specify` — Write a feature spec from a natural language description
2. `/speckit.clarify` — Resolve ambiguities (max 3 clarification points)
3. `/speckit.plan` — Generate a technical implementation plan (includes a research phase)
4. `/speckit.tasks` — Break the plan into dependency-ordered tasks
5. `/speckit.implement` — Execute implementation in phases
6. `/speckit.checklist` — Validate quality gates before merging
7. `/speckit.analyze` — Cross-artifact consistency check

Helper scripts in [.specify/scripts/bash/](.specify/scripts/bash/) automate branch setup and context updates:
- `create-new-feature.sh` — Initialize a new feature branch
- `update-agent-context.sh` — Sync Claude context with current project state

## Constitution & Quality Gates

Governance is defined in [.specify/memory/constitution.md](.specify/memory/constitution.md) (v1.1.0, ratified 2026-03-15). Key non-negotiables:

- **TDD is mandatory** — tests written before implementation, always; test tasks are never optional
- **90% test coverage** minimum, zero skipped tests
- **Function length ≤ 20 lines**, SOLID principles enforced
- **Simple UI** — single primary action per screen, immediate feedback, accessibility required
- **Compartmentalization** — each feature domain has a defined public interface; no direct cross-module imports
- Linting must pass before any merge; UI changes require a manual accessibility check

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
- Python 3.11+ (backend), TypeScript/React 18 (frontend) + FastAPI, Uvicorn, SQLite (via SQLAlchemy), faster-whisper, Ollama Python client (llama3.1), Piper TTS, ffmpeg/pydub (audio conversion), React 18, Vite, React Query (001-speak-roleplay-chat)
- SQLite — conversations, messages, vocabulary items, user settings (001-speak-roleplay-chat)

## Recent Changes
- 001-speak-roleplay-chat: Added Python 3.11+ (backend), TypeScript/React 18 (frontend) + FastAPI, Uvicorn, SQLite (via SQLAlchemy), faster-whisper, Ollama Python client (llama3.1), Piper TTS, ffmpeg/pydub (audio conversion), React 18, Vite, React Query
