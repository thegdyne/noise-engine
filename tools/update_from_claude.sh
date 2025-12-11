#!/bin/bash
# Update noise-engine from Claude's zip export
# Usage: ./tools/update_from_claude.sh

REPO_DIR=~/repos/noise-engine
DOWNLOAD=~/Downloads/noise-engine-updated.zip
TEMP_DIR=~/repos/noise-engine-claude-temp

# Check zip exists
if [ ! -f "$DOWNLOAD" ]; then
    echo "❌ No file at $DOWNLOAD"
    exit 1
fi

echo "📦 Extracting to temp directory..."
rm -rf "$TEMP_DIR"
unzip -q "$DOWNLOAD" -d "$TEMP_DIR"

echo ""
echo "📋 Changes from Claude:"
echo "========================"
CHANGES=$(diff -rq "$REPO_DIR" "$TEMP_DIR/noise-engine-main" 2>/dev/null | grep -v ".git" | grep -v "venv" | grep -v "__pycache__" | grep -v "presets" | grep "^Files")
NEW_FILES=$(diff -rq "$REPO_DIR" "$TEMP_DIR/noise-engine-main" 2>/dev/null | grep "Only in $TEMP_DIR")

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
    cp -r "$TEMP_DIR/noise-engine-main/"* "$REPO_DIR/"
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
