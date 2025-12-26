#!/bin/bash
# Fix missing 'portamento' in var declarations for ALL pack generators
# The patch script added portamento lines but forgot to declare the variable
#
# Run from noise-engine root:
#   chmod +x fix_all_portamento_vars.sh
#   ./fix_all_portamento_vars.sh

cd ~/repos/noise-engine

echo "============================================"
echo "Fixing portamento var declarations in packs"
echo "============================================"
echo ""

FIXED=0
ALREADY_OK=0
NEEDS_PATCH=0

for pack_dir in packs/*/; do
    pack_name=$(basename "$pack_dir")
    
    # Skip if no generators directory
    [ -d "${pack_dir}generators" ] || continue
    
    for f in "${pack_dir}generators/"*.scd; do
        [ -f "$f" ] || continue
        
        gen_name=$(basename "$f")
        
        # Check if file uses portamento
        if grep -q "portamento = In.kr" "$f"; then
            # Check if var declaration exists
            if grep -q "var.*portamento" "$f"; then
                ((ALREADY_OK++))
            else
                echo "[$pack_name] Fixing: $gen_name"
                
                # Add portamento to existing var declaration
                # Match var line containing clockRate and add portamento before semicolon
                perl -i -pe 's/(var[^;]*clockRate)(;)/\1, portamento\2/' "$f"
                
                # Verify it worked
                if grep -q "var.*portamento" "$f"; then
                    ((FIXED++))
                else
                    echo "  WARNING: Could not fix automatically - manual edit needed"
                fi
            fi
        else
            # No portamento code - needs full patch
            ((NEEDS_PATCH++))
        fi
    done
done

echo ""
echo "============================================"
echo "Summary:"
echo "  Fixed:        $FIXED"
echo "  Already OK:   $ALREADY_OK"  
echo "  Needs patch:  $NEEDS_PATCH (no portamento code at all)"
echo "============================================"
echo ""

if [ $FIXED -gt 0 ]; then
    echo "✓ Restart Noise Engine to reload SynthDefs"
fi

if [ $NEEDS_PATCH -gt 0 ]; then
    echo ""
    echo "NOTE: $NEEDS_PATCH generators have no portamento code."
    echo "Run patch_pack_portamento.sh on those packs first."
fi
