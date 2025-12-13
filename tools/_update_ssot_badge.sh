#!/bin/bash
# Update SSOT percentage badge in index.html
# Usage: ./tools/_update_ssot_badge.sh <percentage>
# Example: ./tools/_update_ssot_badge.sh 100

REPO_DIR=~/repos/noise-engine
INDEX_FILE="$REPO_DIR/docs/index.html"

# Get percentage from argument
PERCENT=$1

if [ -z "$PERCENT" ]; then
    echo "❌ Usage: $0 <percentage>"
    echo "   Example: $0 100"
    exit 1
fi

echo "SSOT Compliance: ${PERCENT}%"

# Update index.html
if [ -f "$INDEX_FILE" ]; then
    # Update the SSOT badge percentage
    sed -i '' "s/SSOT <span class=\"pct\">[0-9]*%<\/span>/SSOT <span class=\"pct\">${PERCENT}%<\/span>/" "$INDEX_FILE"
    
    # Update the architecture section percentage
    sed -i '' "s/Single Source of Truth ([0-9]*%)/Single Source of Truth (${PERCENT}%)/" "$INDEX_FILE"
    
    # Add or remove 'perfect' class based on 100%
    if [ "$PERCENT" -eq 100 ]; then
        # Add 'perfect' class if not already there
        sed -i '' 's/class="badge ssot"/class="badge ssot perfect"/' "$INDEX_FILE"
        echo "👑 PERFECT SCORE! Crown activated!"
    else
        # Remove 'perfect' class if present
        sed -i '' 's/class="badge ssot perfect"/class="badge ssot"/' "$INDEX_FILE"
    fi
    
    echo "✅ Updated $INDEX_FILE with SSOT ${PERCENT}%"
else
    echo "❌ index.html not found at $INDEX_FILE"
    exit 1
fi
