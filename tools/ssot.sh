#!/bin/bash
# Run SSOT check and update badge
# Always run from repo root

REPO_DIR=~/repos/noise-engine
cd "$REPO_DIR" || exit 1

"$REPO_DIR/tools/_check_ssot.sh"
"$REPO_DIR/tools/_update_ssot_badge.sh"
