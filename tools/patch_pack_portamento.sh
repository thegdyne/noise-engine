#!/bin/bash
# Patch existing pack generators with portamento support
# Usage: ./patch_pack_portamento.sh packs/pizza-pup

PACK_DIR="$1"

if [ -z "$PACK_DIR" ]; then
    echo "Usage: $0 <pack_directory>"
    echo "Example: $0 packs/pizza-pup"
    exit 1
fi

if [ ! -d "$PACK_DIR/generators" ]; then
    echo "Error: $PACK_DIR/generators not found"
    exit 1
fi

echo "Patching pack: $PACK_DIR"

for scd in "$PACK_DIR/generators"/*.scd; do
    echo "  Patching: $(basename "$scd")"
    
    # 1. Add portamentoBus to signature (after seed=...)
    perl -i -pe 's/seed=(\d+)\|/seed=$1, portamentoBus|/' "$scd"
    
    # 2. Add portamento to var line with clockRate (if not already there)
    if ! grep -q "portamento" "$scd"; then
        perl -i -pe 's/clockRate;$/clockRate, portamento;/' "$scd"
    fi
    
    # 3. Add portamento read and Lag.kr after freq = In.kr(freqBus);
    if ! grep -q "Lag.kr" "$scd"; then
        perl -i -pe 's/freq = In\.kr\(freqBus\);/freq = In.kr(freqBus);\n    portamento = In.kr(portamentoBus);\n    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));/' "$scd"
    fi
done

echo ""
echo "Verification:"
echo -n "  Files with portamentoBus: "
grep -l "portamentoBus" "$PACK_DIR/generators"/*.scd 2>/dev/null | wc -l | tr -d ' '
echo -n "  Files with Lag.kr: "
grep -l "Lag.kr" "$PACK_DIR/generators"/*.scd 2>/dev/null | wc -l | tr -d ' '

echo ""
echo "Done! Restart Noise Engine to reload the pack."
