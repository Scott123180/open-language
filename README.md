# Open Language

A local, privacy-first language practice app. Have spoken role-play conversations with an AI partner in your target language — no cloud, no API keys, everything runs on your machine.

## Features

- **Role-play scenarios** — everyday situations (buying a train ticket, calling an estate agent, etc.)
- **Voice or text input** — speak and get transcribed via Whisper, or type
- **AI responses spoken aloud** — Piper TTS with slow-playback option
- **Learning tools** — grammar check, translation, alternative phrasing, word lookup per message
- **Vocabulary saving** — save unknown words for future flashcard practice
- **Suggested responses** — read-only hints you must speak or type yourself
- **Expression helper** — ask "how do I say X?" in a separate side panel
- **Conversation history** — all chats saved locally in SQLite

## Quick start

```bash
./run.sh          # install everything + start dev server
./run.sh --setup  # install only
./run.sh --start  # start (skip install)
./run.sh --prod   # production build, single port 8000
```

The script checks for prerequisites, creates the Python venv, installs deps, pulls the Ollama model, downloads the default Piper voice, and launches all services. Press `Ctrl+C` to stop.

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

### 5. Download a Piper voice

```bash
mkdir -p ~/.local/share/piper-voices
cd ~/.local/share/piper-voices

# Spanish (medium quality) — default
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json
```

Browse all available voices at [huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/tree/main).

### 6. Configure environment (optional)

Copy `.env.example` to `backend/.env` and adjust:

```bash
cp .env.example backend/.env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_LANGUAGE_DB_PATH` | `~/.open-language/app.db` | SQLite database file |
| `OPEN_LANGUAGE_TTS_VOICE` | `es_ES-davefx-medium` | Piper voice model name (without extension) |
| `OPEN_LANGUAGE_VOICE_DIR` | `~/.local/share/piper-voices` | Directory containing `.onnx` voice files |
| `OPEN_LANGUAGE_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OPEN_LANGUAGE_OLLAMA_MODEL` | `llama3.1:8b` | Ollama model (must match `ollama list`) |
| `OPEN_LANGUAGE_WHISPER_MODEL` | `base` | faster-whisper model size (`tiny`, `base`, `small`, `medium`, `large-v2`) |
| `OPEN_LANGUAGE_WHISPER_DEVICE` | `auto` | `cuda`, `cpu`, or `auto` |

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

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` requests to the backend on port 8000.

### Production (single process)

```bash
cd frontend
npm run build          # builds into ../backend/static/

cd ../backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000). FastAPI serves both the API and the built frontend from one port.

## Running tests

```bash
# Backend (from backend/)
source .venv/bin/activate
pytest --cov=app --cov-report=term-missing

# Frontend (from frontend/)
npm test
```

## Tech stack

- **Frontend**: React 18, TypeScript, Vite, TanStack React Query, React Router v6
- **Backend**: FastAPI, Uvicorn, SQLAlchemy (SQLite, WAL mode)
- **STT**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (local)
- **LLM**: [Ollama](https://ollama.ai) running llama3.1 (local)
- **TTS**: [Piper](https://github.com/rhasspy/piper) (local)
