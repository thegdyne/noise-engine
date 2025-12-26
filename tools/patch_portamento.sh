#!/bin/bash
#
# patch_portamento.sh - Add portamentoBus to all pack generators
#
# Usage:
#   ./tools/patch_portamento.sh              # Dry run (show what would change)
#   ./tools/patch_portamento.sh --apply      # Actually apply changes
#
# This script patches SynthDef files to include portamentoBus in the signature
# and adds the Lag.kr portamento implementation.
#

set -e

APPLY=false
if [[ "$1" == "--apply" ]]; then
    APPLY=true
fi

PACKS_DIR="${PACKS_DIR:-packs}"
GENERATORS_DIR="${GENERATORS_DIR:-supercollider/generators}"

echo "=============================================="
echo "Portamento Bus Patcher"
echo "=============================================="
echo ""

if [[ "$APPLY" == "false" ]]; then
    echo "DRY RUN - use --apply to make changes"
    echo ""
fi

# Count files
total=0
needs_patch=0
already_patched=0

# Function to check and patch a file
patch_file() {
    local file="$1"
    local name=$(basename "$file")
    
    ((total++))
    
    # Check if already has portamentoBus
    if grep -q "portamentoBus" "$file"; then
        ((already_patched++))
        if [[ "$APPLY" == "false" ]]; then
            echo "  ✓ $name (already patched)"
        fi
        return 0
    fi
    
    # Check if it has the old signature pattern
    if ! grep -q "customBus4|" "$file" && ! grep -q "customBus4 |" "$file"; then
        echo "  ⚠ $name (unexpected signature format)"
        return 0
    fi
    
    ((needs_patch++))
    
    if [[ "$APPLY" == "false" ]]; then
        echo "  → $name (needs patching)"
        return 0
    fi
    
    # Apply patches
    echo "  Patching: $name"
    
    # 1. Add portamentoBus to signature (after customBus4)
    sed -i '' 's/customBus4|/customBus4, portamentoBus|/g' "$file"
    sed -i '' 's/customBus4 |/customBus4, portamentoBus|/g' "$file"
    
    # 2. Add portamento to var declaration if not present
    if ! grep -q "portamento" "$file"; then
        # Try to add after common var patterns
        sed -i '' 's/var sig, freq,/var sig, freq, portamento,/' "$file" 2>/dev/null || \
        sed -i '' 's/var sig,/var sig, portamento,/' "$file" 2>/dev/null || true
    fi
    
    # 3. Add portamento read and Lag.kr after freq read
    # This is tricky - only add if not already present
    if ! grep -q "In.kr(portamentoBus)" "$file"; then
        # Use a more careful approach - add after freq = In.kr(freqBus);
        sed -i '' '/freq = In.kr(freqBus);/a\
    portamento = In.kr(portamentoBus);\
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
' "$file" 2>/dev/null || echo "    ⚠ Could not auto-add Lag.kr - manual edit needed"
    fi
    
    echo "    ✓ Done"
}

# Patch core generators
if [[ -d "$GENERATORS_DIR" ]]; then
    echo "Core generators ($GENERATORS_DIR):"
    for file in "$GENERATORS_DIR"/*.scd; do
        [[ -f "$file" ]] && patch_file "$file"
    done
    echo ""
fi

# Patch pack generators
if [[ -d "$PACKS_DIR" ]]; then
    echo "Pack generators ($PACKS_DIR):"
    for pack_dir in "$PACKS_DIR"/*/; do
        pack_name=$(basename "$pack_dir")
        gen_dir="$pack_dir/generators"
        
        if [[ -d "$gen_dir" ]]; then
            echo "  Pack: $pack_name"
            for file in "$gen_dir"/*.scd; do
                [[ -f "$file" ]] && patch_file "$file"
            done
        fi
    done
    echo ""
fi

# Summary
echo "=============================================="
echo "Summary"
echo "=============================================="
echo "Total files scanned:  $total"
echo "Already patched:      $already_patched"
echo "Needs patching:       $needs_patch"
echo ""

if [[ "$APPLY" == "false" ]]; then
    if [[ $needs_patch -gt 0 ]]; then
        echo "Run with --apply to patch $needs_patch files"
    else
        echo "All files already patched!"
    fi
else
    echo "Patching complete."
    echo ""
    echo "Next steps:"
    echo "  1. Review changes: git diff"
    echo "  2. Test in Noise Engine"
    echo "  3. Commit: git add -A && git commit -m 'Add portamentoBus to all generators'"
fi
