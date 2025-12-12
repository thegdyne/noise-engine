#!/bin/bash
# Run SSOT check and update badge
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/_check_ssot.sh"
"$SCRIPT_DIR/update_ssot_badge.sh"
