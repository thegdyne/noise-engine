#!/bin/bash
# Remove debug output added by debug_add.sh
# Usage: ./tools/debug_remove.sh

REPO_DIR=~/repos/noise-engine
BACKUP_DIR="$REPO_DIR/.debug_backup"

echo "🧹 Removing debug output..."

# ============================================
# RESTORE FROM BACKUPS (safest method)
# ============================================

if [ -d "$BACKUP_DIR" ]; then
    for backup in "$BACKUP_DIR"/*.bak; do
        if [ -f "$backup" ]; then
            filename=$(basename "$backup" .bak)
            
            # Find the original file location
            case "$filename" in
                "main_frame.py")
                    dest="$REPO_DIR/src/gui/main_frame.py"
                    ;;
                "generator_slot.py")
                    dest="$REPO_DIR/src/gui/generator_slot.py"
                    ;;
                "scratch.scd")
                    dest="$REPO_DIR/supercollider/scratch.scd"
                    ;;
                *)
                    echo "  ⚠️  Unknown backup: $filename"
                    continue
                    ;;
            esac
            
            if [ -f "$dest" ]; then
                cp "$backup" "$dest"
                echo "  ✓ Restored $filename"
            fi
        fi
    done
    
    # Clean up backup directory
    rm -rf "$BACKUP_DIR"
    echo "  ✓ Cleaned up backup directory"
else
    echo "  ℹ️  No backup directory found, using sed cleanup..."
    
    # Fallback: Remove DEBUG_MARKER lines with sed
    for pyfile in "$REPO_DIR/src/gui/main_frame.py" "$REPO_DIR/src/gui/generator_slot.py"; do
        if [ -f "$pyfile" ]; then
            # Remove lines containing DEBUG_MARKER or DEBUG [
            sed -i '' '/DEBUG_MARKER/d' "$pyfile"
            sed -i '' '/print(f"DEBUG \[/d' "$pyfile"
            echo "  ✓ Cleaned $pyfile"
        fi
    done
    
    # Remove SC debug block
    SCRATCH="$REPO_DIR/supercollider/scratch.scd"
    if [ -f "$SCRATCH" ]; then
        sed -i '' '/=== DEBUG_OSC_LISTENER ===/,/=== END DEBUG_OSC_LISTENER ===/d' "$SCRATCH"
        echo "  ✓ Cleaned scratch.scd"
    fi
fi

echo ""
echo "================================"
echo "✅ Debug output removed"
echo ""
echo "Don't forget to:"
echo "  git add -A && git commit -m 'Remove debug output'"
echo "================================"
