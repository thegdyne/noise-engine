#!/bin/bash
# Update tech debt badge in index.html based on check_tech_debt.py output
# Usage: _update_techdebt_badge.sh <score>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
INDEX_FILE="$REPO_ROOT/docs/index.html"
SCORE="${1:-0}"

if [ ! -f "$INDEX_FILE" ]; then
    echo "❌ index.html not found at $INDEX_FILE"
    exit 1
fi

echo "Tech Debt Score: ${SCORE}%"

# Cross-platform sed in-place edit
sedi() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# Update the percentage
sedi "s/DEBT <span class=\"pct\">[0-9]*%<\/span>/DEBT <span class=\"pct\">${SCORE}%<\/span>/" "$INDEX_FILE"

# Add or remove 'perfect' class based on 100%
if [ "$SCORE" -eq 100 ]; then
    # Add 'perfect' class if not already there
    sedi 's/class="badge techdebt"/class="badge techdebt perfect"/' "$INDEX_FILE"
    echo "🚜 CLEAN BUILD! Backhoe activated!"
else
    # Remove 'perfect' class if present
    sedi 's/class="badge techdebt perfect"/class="badge techdebt"/' "$INDEX_FILE"
fi

echo "✅ Updated $INDEX_FILE with Tech Debt ${SCORE}%"
