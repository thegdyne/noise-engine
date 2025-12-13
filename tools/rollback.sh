#!/bin/bash
# Rollback the last commit (destructive - loses changes)
# Usage: ./tools/rollback.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR" || exit 1

echo "⚠️  This will PERMANENTLY undo the last commit:"
git log -1 --oneline
echo ""
read -p "Are you sure? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    git reset --hard HEAD~1
    echo "✅ Rolled back. Current state:"
    git log -1 --oneline
else
    echo "❌ Cancelled"
fi
