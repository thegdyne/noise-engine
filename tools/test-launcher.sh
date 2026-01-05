#!/usr/bin/env bash
set -euo pipefail
STATE="$HOME/Library/Application Support/NoiseEngine/state/ready.json"

if [[ -f "$STATE" ]] && grep -q '"status": "ready"' "$STATE"; then
  echo "PASS: ready.json exists and status is ready"
  cat "$STATE"
  exit 0
else
  echo "FAIL: ready.json missing or status not ready"
  [[ -f "$STATE" ]] && { echo "--- ready.json ---"; cat "$STATE"; }
  exit 1
fi
