# Open Language

A privacy-first language practice app. Have spoken role-play conversations with an AI partner in your target language.

Every AI capability — the conversation partner, speech recognition, and the voice — sits behind a swappable provider interface. The app is **local by default**: out of the box everything runs on your machine through Ollama, faster-whisper, and Piper, with no account, no API key, and no audio leaving your computer. That default exists because speaking practice means recording yourself making mistakes, over and over, and that audio shouldn't have to go anywhere.

Cloud providers are opt-in. Today you can choose Claude as the conversation partner, through your own signed-in Claude Code — see [Enabling Claude (optional)](#enabling-claude-optional). Speech recognition and the voice stay local either way.

## Features

- **Spanish or German** — pick the practice language in Settings; each conversation keeps the language it started in, and flashcards show one language at a time
- **Role-play scenarios** — everyday situations (buying a train ticket, calling an estate agent, etc.)
- **Voice or text input** — speak and get transcribed via Whisper, or type
- **AI responses spoken aloud** — Piper TTS with slow-playback option
- **Learning tools** — grammar check, translation, alternative phrasing, word lookup per message
- **Vocabulary saving** — save unknown words for future flashcard practice
- **Suggested responses** — read-only hints you must speak or type yourself
- **Expression helper** — ask "how do I say X?" in a separate side panel
- **Conversation history** — all chats saved locally in SQLite
- **Choice of conversation partner** — a local Ollama model (the default) or Claude via Claude Code, switched on the Settings screen without a restart

## Quick start

```bash
./run.sh          # install everything + start dev server
./run.sh --setup  # install only
./run.sh --start  # start (skip install)
./run.sh --prod   # production build, single port 8000
```

The script checks for prerequisites, creates the Python venv, installs deps, pulls the Ollama model, downloads the Spanish and German Piper voices, and launches all services. Press `Ctrl+C` to stop.

---

## Prerequisites

| Dependency | Version | Install |
|------------|---------|---------|
| Python | 3.11+ | `pyenv install 3.11` or system package |
| Node.js | 20+ | `nvm install 20` or system package |
| FFmpeg | any recent | `sudo apt install ffmpeg` |
| espeak-ng | any recent | `sudo apt install espeak-ng` |
| Ollama | latest | [ollama.ai/download](https://ollama.ai/download) |

## Setup

### 1. Clone the repo

```bash
git clone <repo-url> open-language
cd open-language
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Frontend

```bash
cd frontend
npm install
```

### 4. Pull the Ollama model

```bash
ollama pull llama3.1
```

### 5. Download the Piper voices

`./run.sh --setup` downloads every voice below. To fetch one by hand, put its `.onnx` and `.onnx.json`
files in `~/.local/share/piper-voices`:

```bash
mkdir -p ~/.local/share/piper-voices
cd ~/.local/share/piper-voices

# Spanish (medium quality) — the Spanish default
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json

# German (medium quality) — the German default
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx.json
```

| Voice | Language | Notes |
|---|---|---|
| `es_ES-davefx-medium` | Spanish | Default for Spanish |
| `es_AR-daniela-high` | Spanish | Female, fast |
| `de_DE-thorsten-medium` | German | Default for German |
| `de_DE-kerstin-low` | German | Female, lower quality |

Each language remembers its own voice, chosen in Settings. A language whose voice isn't installed still
works in text; the chat says how to download the voice, and nothing is read aloud in another voice.

Browse all available voices at [huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/tree/main).

### 6. Configure environment (optional)

Copy `.env.example` to `backend/.env` and adjust:

```bash
cp .env.example backend/.env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_LANGUAGE_DB_PATH` | `~/.open-language/app.db` | SQLite database file |
| `OPEN_LANGUAGE_TTS_VOICE` | `es_ES-davefx-medium` | Not used: the voice is chosen per practice language in Settings |
| `OPEN_LANGUAGE_VOICE_DIR` | `~/.local/share/piper-voices` | Directory containing `.onnx` voice files |
| `OPEN_LANGUAGE_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OPEN_LANGUAGE_OLLAMA_MODEL` | `llama3.1:8b` | Ollama model (must match `ollama list`) |
| `OPEN_LANGUAGE_WHISPER_MODEL` | `base` | faster-whisper model size (`tiny`, `base`, `small`, `medium`, `large-v2`) |
| `OPEN_LANGUAGE_WHISPER_DEVICE` | `auto` | `cuda`, `cpu`, or `auto` |
| `OPEN_LANGUAGE_CLAUDE_EXECUTABLE` | `claude` | The Claude Code command, if you enable Claude |
| `OPEN_LANGUAGE_SESSION_IDLE_TTL_MINUTES` | `30` | How long an idle conversation keeps its model loaded (Ollama) or its process alive (Claude) |

## Running

### Development (two terminals)

**Terminal 1 — Ollama** (skip if already running):
```bash
ollama serve
```

**Terminal 2 — Backend**:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 — Frontend**:
```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` requests to the backend on port 8000. In development the backend serves only the API, so [http://localhost:8000](http://localhost:8000) itself returns 404.

### Production (single process)

```bash
cd frontend
npm run build          # builds into ../backend/static/

cd ../backend
source .venv/bin/activate
OPEN_LANGUAGE_MODE=production uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000). FastAPI serves both the API and the built frontend from one port. Production mode refuses to start if the frontend hasn't been built, rather than serving nothing.

## Enabling Claude (optional)

The conversation partner can be Claude instead of the local Ollama model. The app drives your own signed-in Claude Code, so usage counts toward **your Claude plan** — the app never asks for, uses, or stores an API key.

1. **Install Claude Code** — see [Claude Code's setup guide](https://docs.claude.com/en/docs/claude-code/setup). Check it's on your `PATH` with `claude --version`.
2. **Sign in with your Claude plan, not an API key.** Run `claude` in a terminal and sign in with your Claude account. An API-key login would bill a separate API account, so the app refuses to use one.
3. **Confirm the sign-in**: `claude auth status --text` should show you're logged in with your Claude account.
4. **Select Claude on the Settings screen.** Under *Language model*, choose *Claude (via Claude Code)*, then a model (Sonnet by default) and an effort level (Low by default — the fastest replies). Save.

If Claude Code is missing, signed out, or signed in with an API key, the Claude option is disabled and says which step is missing.

**What is sent to Anthropic**: the text of your conversations and of the learning-tool requests (grammar checks, translations, word lookups, corrections), under your Claude account. **What stays on your computer**: your voice recordings and all audio (speech recognition and the voice are always local), and your saved history and vocabulary.

Each request runs Claude Code as a plain chat model: no tools, no access to your files, no personal or project configuration, and no saved Claude session. If Claude Code is somewhere other than `claude` on your `PATH`, set `OPEN_LANGUAGE_CLAUDE_EXECUTABLE`.

To go back, choose *Ollama (local)* on the Settings screen. The app never switches providers on its own: if Claude stops working, you'll see a message saying what to do.

## Running tests

```bash
# Backend (from backend/)
source .venv/bin/activate
pytest --cov=app --cov-report=term-missing

# Frontend (from frontend/)
npm test
```

The default backend suite needs neither Ollama nor Claude Code. Tests that make real `claude -p` calls against your plan are opt-in: `pytest -m claude_live --no-cov`.

## Tech stack

- **Frontend**: React 18, TypeScript, Vite, TanStack React Query, React Router v6
- **Backend**: FastAPI, Uvicorn, SQLAlchemy (SQLite, WAL mode)
- **STT**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (local)
- **LLM**: [Ollama](https://ollama.ai) running llama3.1 (local, the default), or Claude through [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) (opt-in)
- **TTS**: [Piper](https://github.com/rhasspy/piper) (local)
