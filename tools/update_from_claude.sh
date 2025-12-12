#!/bin/bash
# Update noise-engine from Claude's zip export
# Usage: ./tools/update_from_claude.sh

REPO_DIR=~/repos/noise-engine
DOWNLOAD=~/Downloads/noise-engine-updated.zip
TEMP_DIR=~/repos/noise-engine-claude-temp
TARGET_BRANCH=dev

# Check zip exists
if [ ! -f "$DOWNLOAD" ]; then
    echo "❌ No file at $DOWNLOAD"
    exit 1
fi

# Ensure we're on the dev branch
cd "$REPO_DIR"
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]; then
    echo "🔀 Switching from $CURRENT_BRANCH to $TARGET_BRANCH..."
    git checkout "$TARGET_BRANCH" || { echo "❌ Failed to checkout $TARGET_BRANCH"; exit 1; }
fi

echo "📦 Extracting to temp directory..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
unzip -q "$DOWNLOAD" -d "$TEMP_DIR"

# Detect if zip has a subfolder or extracts to root
if [ -d "$TEMP_DIR/noise-engine-main" ]; then
    EXTRACT_DIR="$TEMP_DIR/noise-engine-main"
else
    EXTRACT_DIR="$TEMP_DIR"
fi

echo ""
echo "📋 Changes from Claude:"
echo "========================"
CHANGES=$(diff -rq "$REPO_DIR" "$EXTRACT_DIR" 2>/dev/null | grep -v ".git" | grep -v "venv" | grep -v "__pycache__" | grep -v "presets" | grep "^Files")
NEW_FILES=$(diff -rq "$REPO_DIR" "$EXTRACT_DIR" 2>/dev/null | grep "Only in $EXTRACT_DIR")

if [ -z "$CHANGES" ] && [ -z "$NEW_FILES" ]; then
    echo "No changes to apply."
    rm -rf "$TEMP_DIR"
    rm "$DOWNLOAD"
    echo "🧹 Cleaned up."
    exit 0
fi

[ -n "$CHANGES" ] && echo "$CHANGES"
[ -n "$NEW_FILES" ] && echo "$NEW_FILES"

echo ""
read -p "Apply these changes? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    cp -r "$EXTRACT_DIR/"* "$REPO_DIR/"
    echo "✅ Files updated"
    
    rm -rf "$TEMP_DIR"
    rm "$DOWNLOAD"
    echo "🧹 Cleaned up temp files and download"
    
    echo ""
    echo "Git status:"
    cd "$REPO_DIR" && git status --short
else
    rm -rf "$TEMP_DIR"
    echo "❌ Cancelled. Temp cleaned up, zip kept."
fi
