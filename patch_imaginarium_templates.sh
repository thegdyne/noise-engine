#!/bin/bash
# Patch all Imaginarium method templates with portamento support
# Run from noise-engine root

cd ~/repos/noise-engine

echo "Patching Imaginarium method templates with portamento..."
echo ""

PATCHED=0

for f in imaginarium/methods/*/*.py; do
    [ -f "$f" ] || continue
    
    # Skip base.py and __init__.py
    [[ "$f" == *"base.py" ]] && continue
    [[ "$f" == *"__init__.py" ]] && continue
    
    # Check if it's a template file with generate_synthdef
    if grep -q "def generate_synthdef" "$f"; then
        # Check if already patched
        if grep -q "portamentoBus" "$f"; then
            echo "  Skip (already patched): $(basename $f)"
            continue
        fi
        
        echo "  Patching: $f"
        
        # 1. Add portamentoBus to SynthDef signature (after seed=)
        perl -i -pe 's/(seed=\{seed\})\|/\1, portamentoBus|/' "$f"
        
        # 2. Add portamento to var declaration with clockRate
        # Match the line: var freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
        perl -i -pe 's/(var freq.*clockRate);/\1, portamento;/' "$f"
        
        # 3. Add portamento read and Lag.kr after freq = In.kr(freqBus);
        perl -i -pe 's/(freq = In\.kr\(freqBus\);)/\1\n    portamento = In.kr(portamentoBus);\n    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));/' "$f"
        
        ((PATCHED++))
    fi
done

echo ""
echo "Patched $PATCHED template files"
echo ""
echo "Verify with:"
echo "  grep -l 'portamentoBus' imaginarium/methods/*/*.py | wc -l"
