#!/usr/bin/env bash
set -euo pipefail

OS="$(uname -s)"
if [[ "$OS" == "Darwin" ]]; then
  CFG_DIR="$HOME/Library/Application Support/NoiseEngine"
elif [[ "$OS" == "Linux" ]]; then
  CFG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/NoiseEngine"
else
  CFG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/NoiseEngine"
fi

STATE="$CFG_DIR/state/ready.json"

if [[ -f "$STATE" ]] && grep -q '"status": "ready"' "$STATE"; then
  echo "PASS: ready.json exists and status is ready"
  cat "$STATE"
  exit 0
else
  echo "FAIL: ready.json missing or status not ready"
  [[ -f "$STATE" ]] && { echo "--- ready.json ---"; cat "$STATE"; }
  exit 1
fi
