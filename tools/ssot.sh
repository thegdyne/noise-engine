#!/bin/bash
# Run SSOT check and update badge
# Always run from repo root

cd ~/repos/noise-engine || exit 1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/_check_ssot.sh"
"$SCRIPT_DIR/_update_ssot_badge.sh"
