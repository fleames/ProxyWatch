#!/bin/bash
# ProxyWatch launcher — activates the virtual environment automatically
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[!] Virtual environment not found at $VENV_DIR"
    echo "    Set it up with: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Activate venv and launch
source "$VENV_DIR/bin/activate"
exec python "$SCRIPT_DIR/main.py" "$@"