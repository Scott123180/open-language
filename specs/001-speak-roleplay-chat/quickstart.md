# Quickstart: Speak — Role-Play Conversation Chat

**Branch**: `001-speak-roleplay-chat`

## Prerequisites

| Dependency | Install |
|------------|---------|
| Python 3.11+ | `pyenv install 3.11` or system package |
| Node.js 20+ | `nvm install 20` or system package |
| FFmpeg | `sudo apt install ffmpeg` |
| Ollama | [ollama.ai/download](https://ollama.ai/download) |
| Piper TTS voices | See step 5 below |

## 1. Clone and set up

```bash
git clone <repo> open-language
cd open-language
git checkout 001-speak-roleplay-chat
```

## 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Frontend

```bash
cd frontend
npm install
```

## 4. Pull the Ollama model

```bash
ollama pull llama3.1
ollama serve   # keep running in a separate terminal
```

## 5. Download a Piper voice

```bash
# Example: Spanish (medium quality)
mkdir -p ~/.local/share/piper-voices
cd ~/.local/share/piper-voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls/medium/es_ES-mls-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls/medium/es_ES-mls-medium.onnx.json
```

Set the voice in settings or via environment:
```bash
export OPEN_LANGUAGE_TTS_VOICE=es_ES-mls-medium
export OPEN_LANGUAGE_VOICE_DIR=~/.local/share/piper-voices
```

## 6. Run (development)

Two terminals:

**Terminal 1 — Backend**:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend (hot reload)**:
```bash
cd frontend
npm run dev   # Vite dev server on :5173, proxies /api → :8000
```

Open [http://localhost:5173](http://localhost:5173).

## 7. Run (production build)

```bash
cd frontend
npm run build          # outputs to ../backend/static/

cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_LANGUAGE_DB_PATH` | `~/.open-language/app.db` | SQLite database file |
| `OPEN_LANGUAGE_TTS_VOICE` | `es_ES-mls-medium` | Piper voice model name |
| `OPEN_LANGUAGE_VOICE_DIR` | `~/.local/share/piper-voices` | Directory containing `.onnx` voice files |
| `OPEN_LANGUAGE_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OPEN_LANGUAGE_WHISPER_MODEL` | `base` | faster-whisper model size |
| `OPEN_LANGUAGE_WHISPER_DEVICE` | `auto` | `cuda`, `cpu`, or `auto` |

## Running tests

```bash
# Backend
cd backend
pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm run test
```

All tests must pass at ≥ 90% coverage before any merge.
