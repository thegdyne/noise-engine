#!/bin/bash
# Update SSOT percentage badge in index.html
# Run: ./tools/update_ssot_badge.sh

REPO_DIR=~/repos/noise-engine
INDEX_FILE="$REPO_DIR/docs/index.html"
CHECK_SCRIPT="$REPO_DIR/tools/check_ssot.sh"

# Run SSOT check and extract percentage
OUTPUT=$("$CHECK_SCRIPT" --json 2>/dev/null)
JSON_LINE=$(echo "$OUTPUT" | grep "JSON_OUTPUT:" | sed 's/JSON_OUTPUT://')

if [ -z "$JSON_LINE" ]; then
    echo "❌ Failed to get SSOT percentage"
    exit 1
fi

# Extract percent from JSON
PERCENT=$(echo "$JSON_LINE" | grep -o '"percent":[0-9]*' | cut -d: -f2)

if [ -z "$PERCENT" ]; then
    echo "❌ Failed to parse percentage"
    exit 1
fi

echo "SSOT Compliance: ${PERCENT}%"

# Update index.html
if [ -f "$INDEX_FILE" ]; then
    # Update the SSOT badge percentage
    sed -i '' "s/SSOT <span class=\"pct\">[0-9]*%<\/span>/SSOT <span class=\"pct\">${PERCENT}%<\/span>/" "$INDEX_FILE"
    echo "✅ Updated $INDEX_FILE with SSOT ${PERCENT}%"
else
    echo "❌ index.html not found at $INDEX_FILE"
    exit 1
fi
