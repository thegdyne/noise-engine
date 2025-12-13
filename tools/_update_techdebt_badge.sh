#!/bin/bash
# Update tech debt badge in index.html based on check_tech_debt.py output
# Usage: _update_techdebt_badge.sh <score>

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX_FILE="$REPO_ROOT/docs/index.html"
SCORE="${1:-0}"

if [ ! -f "$INDEX_FILE" ]; then
    echo "❌ index.html not found at $INDEX_FILE"
    exit 1
fi

# Determine badge class based on score
if [ "$SCORE" -eq 100 ]; then
    BADGE_CLASS="badge techdebt perfect"
    BACKHOE='<span class="backhoe">🚜</span>'
else
    BADGE_CLASS="badge techdebt"
    BACKHOE=""
fi

# Update the badge using sed
# Match: <span class="badge techdebt...">...</span>
sed -i.bak -E "s|<span class=\"badge techdebt[^\"]*\">.*?DEBT.*?</span>|<span class=\"$BADGE_CLASS\">$BACKHOE""DEBT <span class=\"pct\">$SCORE%</span></span>|g" "$INDEX_FILE"

rm -f "$INDEX_FILE.bak"

echo "✅ Updated $INDEX_FILE with Tech Debt $SCORE%"
