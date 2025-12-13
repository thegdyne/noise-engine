#!/bin/bash
# Run SSOT check, update badge, commit and push
# Always run from repo root

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR" || exit 1

# Run Python SSOT checker
python3 "$REPO_DIR/tools/check_ssot.py"
RESULT=$?

# Update badge based on result
if [ $RESULT -eq 0 ]; then
    "$REPO_DIR/tools/_update_ssot_badge.sh" 100
else
    "$REPO_DIR/tools/_update_ssot_badge.sh" 0
fi

# Check if index.html changed
if git diff --quiet docs/index.html; then
    echo "📋 No badge changes needed"
else
    echo ""
    echo "📤 Committing badge update..."
    git add docs/index.html
    git commit -m "Update SSOT badge"
    git push
    echo "✅ Badge committed and pushed to dev"
fi

exit $RESULT
