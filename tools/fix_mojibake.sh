#!/bin/bash
# Fix mojibake (UTF-8 encoding corruption) in Noise Engine source files
#
# These are UTF-8 characters that were incorrectly decoded as Windows-1252.
# Running this script restores the proper Unicode characters.

set -e

# Files known to have corruption
FILES=(
    "src/gui/main_frame.py"
    "src/gui/fx_window.py"
    "docs/GENERATOR_PACK_SESSION.md"
)

fix_file() {
    local FILE="$1"
    
    if [ ! -f "$FILE" ]; then
        echo "  Skipping $FILE (not found)"
        return
    fi
    
    echo "  Fixing $FILE..."
    
    # Status indicator bullets (● → •)
    sed -i '' 's/Ã¢â€"Â /• /g' "$FILE"
    
    # Warning symbol (⚠)
    sed -i '' 's/Ã¢Å¡Â /⚠ /g' "$FILE"
    
    # Restart symbol (↻)
    sed -i '' 's/Ã¢â€ Â»/↻/g' "$FILE"
    
    # Em dash (—)
    sed -i '' 's/Ã¢â‚¬â€/—/g' "$FILE"
    
    # Bullet for dirty marker (•)
    sed -i '' 's/Ã¢â‚¬Â¢/•/g' "$FILE"
    
    # Arrow (→) 
    sed -i '' 's/Ã¢â€ â€™/→/g' "$FILE"
    
    # Horizontal line (─) in section comments
    sed -i '' 's/Ã¢â€â‚¬/─/g' "$FILE"
    
    # Check mark (✓) for PASS indicators
    sed -i '' 's/Ã¢Å"â€œ/✓/g' "$FILE"
}

echo "Fixing encoding corruption..."

for FILE in "${FILES[@]}"; do
    fix_file "$FILE"
done

echo ""
echo "Verifying... (should show no results)"
grep -rn "Ã¢" src/gui/main_frame.py src/gui/fx_window.py docs/GENERATOR_PACK_SESSION.md 2>/dev/null || echo "✓ All clean!"
echo ""
echo "Run the test to confirm: pytest tests/test_encoding.py -v"
