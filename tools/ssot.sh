#!/bin/bash
# Run SSOT check, update badge, commit and push
# Always run from repo root

REPO_DIR=~/repos/noise-engine
cd "$REPO_DIR" || exit 1

"$REPO_DIR/tools/_check_ssot.sh"
"$REPO_DIR/tools/_update_ssot_badge.sh"

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
