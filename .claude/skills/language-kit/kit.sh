#!/usr/bin/env bash
# The language kit's entry point: runs `python -m language_kit` in the backend venv.
# Usage: .claude/skills/language-kit/kit.sh <command> [args]   (kit.sh --help lists the commands)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  echo "backend/.venv is missing: run ./run.sh --setup" >&2
  exit 2
fi
export LANGUAGE_KIT_CWD="$PWD"
cd "$ROOT/backend" && exec .venv/bin/python -m language_kit "$@"
