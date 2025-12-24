#!/bin/bash
# Patch existing pack .scd files with portamento support
# CORRECTED VERSION - properly adds var declaration
#
# Usage:
#   chmod +x patch_pack_portamento_v2.sh
#   ./patch_pack_portamento_v2.sh packs/my-pack/

if [ -z "$1" ]; then
    echo "Usage: $0 <pack_directory>"
    echo "Example: $0 packs/pizza-pup/"
    exit 1
fi

PACK_DIR="$1"
GENERATORS_DIR="${PACK_DIR}/generators"

if [ ! -d "$GENERATORS_DIR" ]; then
    echo "Error: $GENERATORS_DIR not found"
    exit 1
fi

echo "Patching pack: $PACK_DIR"
echo ""

PATCHED=0
SKIPPED=0

for f in "$GENERATORS_DIR"/*.scd; do
    [ -f "$f" ] || continue
    
    filename=$(basename "$f")
    
    # Check if already patched
    if grep -q "portamentoBus" "$f"; then
        echo "  Skip (already has portamentoBus): $filename"
        ((SKIPPED++))
        continue
    fi
    
    echo "  Patching: $filename"
    
    # 1. Add portamentoBus to SynthDef signature (after seed=)
    perl -i -pe 's/(seed=\d+)\|/\1, portamentoBus|/' "$f"
    
    # 2. Add portamento to var declaration (after clockRate)
    perl -i -pe 's/(var[^;]*clockRate)(;)/\1, portamento\2/' "$f"
    
    # 3. Add portamento read and Lag.kr after freq = In.kr(freqBus);
    perl -i -pe 's/(freq = In\.kr\(freqBus\);)/\1\n    portamento = In.kr(portamentoBus);\n    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));/' "$f"
    
    ((PATCHED++))
done

echo ""
echo "Done: $PATCHED patched, $SKIPPED skipped"
echo ""
echo "Verify with:"
echo "  grep 'var.*portamento' $GENERATORS_DIR/*.scd"
echo "  grep 'portamentoBus' $GENERATORS_DIR/*.scd"
