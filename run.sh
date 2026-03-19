#!/usr/bin/env bash
# run.sh — Set up and launch Open Language
#
# Usage:
#   ./run.sh            # install everything (if needed) then start all services
#   ./run.sh --setup    # install only, don't start
#   ./run.sh --start    # start only (assumes setup already done)
#   ./run.sh --prod     # production mode: build frontend, serve everything from port 8000

set -euo pipefail

# ── Colours ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ts()      { date '+%H:%M:%S'; }
info()    { echo -e "${CYAN}[open-language]${NC} $(ts) $*"; }
success() { echo -e "${GREEN}[open-language]${NC} $(ts) $*"; }
warn()    { echo -e "${YELLOW}[open-language]${NC} $(ts) $*"; }
die()     { echo -e "${RED}[open-language] ERROR:${NC} $(ts) $*" >&2; exit 1; }
add_timestamps() { while IFS= read -r line; do printf '%s %s\n' "$(date '+%H:%M:%S')" "$line"; done; }

# ── Defaults ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV="$BACKEND_DIR/.venv"
VOICE_DIR="${OPEN_LANGUAGE_VOICE_DIR:-$HOME/.local/share/piper-voices}"
TTS_VOICE="${OPEN_LANGUAGE_TTS_VOICE:-es_ES-davefx-medium}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"

usage() {
  echo ""
  echo "  Usage: ./run.sh [options]"
  echo ""
  echo "  Options:"
  echo "    (none)     Install dependencies if needed, then start in dev mode"
  echo "    --setup    Install dependencies only (venv, npm, model, voice)"
  echo "    --start    Start services only (skip install)"
  echo "    --prod     Production build + single-port server on :8000"
  echo "    --help     Show this message"
  echo ""
  echo "  Prerequisites (apt): ffmpeg, espeak-ng"
  echo "  Prerequisites (other): Python 3.11+, Node 20+, Ollama"
  echo ""
}

MODE="all"
PROD=false

if [[ $# -eq 0 ]]; then
  usage
fi

for arg in "$@"; do
  case "$arg" in
    --setup) MODE="setup" ;;
    --start) MODE="start" ;;
    --prod)  PROD=true ;;
    --help|-h) usage; exit 0 ;;
    *) usage; die "Unknown argument: $arg" ;;
  esac
done

# ── Prerequisite checks ───────────────────────────────────────────────────────
check_prereqs() {
  info "Checking prerequisites..."

  local missing=()

  # Python 3.11+
  if command -v python3 &>/dev/null; then
    py_ver=$(python3 -c 'import sys; print(sys.version_info >= (3,11))' 2>/dev/null)
    [[ "$py_ver" == "True" ]] || missing+=("Python 3.11+ (found $(python3 --version))")
  else
    missing+=("Python 3.11+")
  fi

  # Node 20+
  if command -v node &>/dev/null; then
    node_major=$(node -e 'process.stdout.write(process.version.slice(1).split(".")[0])')
    [[ "$node_major" -ge 20 ]] 2>/dev/null || missing+=("Node.js 20+ (found $(node --version))")
  else
    missing+=("Node.js 20+")
  fi

  # npm
  command -v npm &>/dev/null || missing+=("npm")

  # ffmpeg
  command -v ffmpeg &>/dev/null || missing+=("ffmpeg  →  sudo apt install ffmpeg")

  # espeak-ng (required by Piper for phonemization)
  command -v espeak-ng &>/dev/null || missing+=("espeak-ng  →  sudo apt install espeak-ng")

  # ollama
  command -v ollama &>/dev/null || missing+=("Ollama  →  https://ollama.ai/download")

  if [[ ${#missing[@]} -gt 0 ]]; then
    die "Missing prerequisites:\n$(printf '  • %s\n' "${missing[@]}")"
  fi

  success "All prerequisites found."
}

# ── Backend setup ─────────────────────────────────────────────────────────────
setup_backend() {
  info "Setting up backend..."

  if [[ ! -d "$VENV" ]]; then
    info "Creating Python virtual environment..."
    python3 -m venv "$VENV"
  fi

  info "Installing Python dependencies..."
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -e "$BACKEND_DIR/.[dev]"

  # Copy .env if missing
  if [[ ! -f "$BACKEND_DIR/.env" && -f "$SCRIPT_DIR/.env.example" ]]; then
    cp "$SCRIPT_DIR/.env.example" "$BACKEND_DIR/.env"
    info "Created backend/.env from .env.example — edit it to customise settings."
  fi

  success "Backend ready."
}

# ── Frontend setup ────────────────────────────────────────────────────────────
setup_frontend() {
  info "Installing frontend dependencies..."
  npm --prefix "$FRONTEND_DIR" install --silent
  success "Frontend ready."
}

# ── Ollama model ──────────────────────────────────────────────────────────────
setup_ollama_model() {
  if ollama list 2>/dev/null | grep -qE "^${OLLAMA_MODEL}[[:space:]]"; then
    info "Ollama model '$OLLAMA_MODEL' already present."
  else
    info "Pulling Ollama model '$OLLAMA_MODEL' (this may take a while)..."
    ollama pull "$OLLAMA_MODEL"
    success "Model '$OLLAMA_MODEL' ready."
  fi
}

# ── Piper voice ───────────────────────────────────────────────────────────────
setup_piper_voice() {
  local onnx="$VOICE_DIR/${TTS_VOICE}.onnx"
  local json="$VOICE_DIR/${TTS_VOICE}.onnx.json"

  if [[ -f "$onnx" && -f "$json" ]]; then
    info "Piper voice '$TTS_VOICE' already present."
    return
  fi

  info "Downloading Piper voice '$TTS_VOICE'..."
  mkdir -p "$VOICE_DIR"

  # Derive the HuggingFace path from the voice name: lang_REGION-name-quality
  # e.g. es_ES-davefx-medium → es/es_ES/davefx/medium/
  local lang="${TTS_VOICE%%_*}"
  local region="${TTS_VOICE%%-*}"
  local rest="${TTS_VOICE#*-}"
  local name="${rest%-*}"
  local quality="${rest##*-}"
  local hf_base="https://huggingface.co/rhasspy/piper-voices/resolve/main/${lang}/${region}/${name}/${quality}"

  if command -v wget &>/dev/null; then
    wget -q -P "$VOICE_DIR" "${hf_base}/${TTS_VOICE}.onnx" \
      && wget -q -P "$VOICE_DIR" "${hf_base}/${TTS_VOICE}.onnx.json" \
      || { rm -f "$onnx" "$json"; die "Failed to download Piper voice '$TTS_VOICE'. Check the voice name and your network connection."; }
  elif command -v curl &>/dev/null; then
    curl -sSL --fail -o "$onnx" "${hf_base}/${TTS_VOICE}.onnx" \
      && curl -sSL --fail -o "$json" "${hf_base}/${TTS_VOICE}.onnx.json" \
      || { rm -f "$onnx" "$json"; die "Failed to download Piper voice '$TTS_VOICE'. Check the voice name and your network connection."; }
  else
    die "Neither wget nor curl found. Install one, then re-run setup."
  fi

  success "Piper voice '$TTS_VOICE' downloaded."
}

# ── Launch services (dev mode) ────────────────────────────────────────────────
PIDS=()

cleanup() {
  echo ""
  info "Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  info "Done."
}

start_dev() {
  trap cleanup INT TERM

  # Ollama
  if ! pgrep -x ollama &>/dev/null; then
    info "Starting Ollama..."
    ollama serve > >(add_timestamps >> /tmp/open-language-ollama.log) 2>&1 &
    PIDS+=($!)
    sleep 1   # give it a moment to bind
  else
    info "Ollama already running."
  fi

  # Backend
  info "Starting backend on http://localhost:8000 ..."
  cd "$BACKEND_DIR"
  PYTHONPATH="$BACKEND_DIR" \
    "$VENV/bin/uvicorn" app.main:app --reload --port 8000 \
    > >(add_timestamps >> /tmp/open-language-backend.log) 2>&1 &
  PIDS+=($!)

  # Frontend
  info "Starting frontend on http://localhost:5173 ..."
  npm --prefix "$FRONTEND_DIR" run dev -- --port 5173 \
    > >(add_timestamps >> /tmp/open-language-frontend.log) 2>&1 &
  PIDS+=($!)

  success "All services started."
  echo ""
  echo -e "  ${GREEN}App:${NC}      http://localhost:5173"
  echo -e "  ${GREEN}API:${NC}      http://localhost:8000/api"
  echo -e "  ${GREEN}Logs:${NC}     /tmp/open-language-{backend,frontend,ollama}.log"
  echo ""
  echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop."
  echo ""

  wait
}

# ── Launch (production mode) ──────────────────────────────────────────────────
start_prod() {
  trap cleanup INT TERM

  info "Building frontend..."
  npm --prefix "$FRONTEND_DIR" run build

  # Ollama
  if ! pgrep -x ollama &>/dev/null; then
    info "Starting Ollama..."
    ollama serve > >(add_timestamps >> /tmp/open-language-ollama.log) 2>&1 &
    PIDS+=($!)
    sleep 1
  fi

  info "Starting server on http://localhost:8000 ..."
  cd "$BACKEND_DIR"
  PYTHONPATH="$BACKEND_DIR" \
    "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 \
    > >(add_timestamps >> /tmp/open-language-backend.log) 2>&1 &
  PIDS+=($!)

  success "Production server started."
  echo ""
  echo -e "  ${GREEN}App:${NC}  http://localhost:8000"
  echo -e "  ${GREEN}Log:${NC}  /tmp/open-language-backend.log"
  echo ""
  echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop."
  echo ""

  wait
}

# ── Main ──────────────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR"

if [[ "$MODE" == "all" || "$MODE" == "setup" ]]; then
  check_prereqs
  setup_backend
  setup_frontend
  setup_ollama_model
  setup_piper_voice
  [[ "$MODE" == "setup" ]] && { success "Setup complete."; exit 0; }
fi

if [[ "$PROD" == true ]]; then
  start_prod
elif [[ "$MODE" == "start" || "$MODE" == "all" ]]; then
  start_dev
fi
