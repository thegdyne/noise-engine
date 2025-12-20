#!/bin/bash
# Fix Generator Envelope Compliance
# Replaces `sig = sig * amp;` with proper ~envVCA call
# See: GENERATOR_ENVELOPE_COMPLIANCE.md

cd ~/repos/noise-engine

# Fix all pack generators
sed -i '' 's/sig = sig \* amp;/sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);/g' \
    packs/electric-shepherd/generators/*.scd \
    packs/rlyeh/generators/*.scd

# Verify fix applied
echo "Files still using 'sig * amp' (should be empty):"
grep -l "sig \* amp" packs/*/generators/*.scd 2>/dev/null || echo "  None - good!"

echo ""
echo "Files now using ~envVCA:"
grep -l "~envVCA" packs/*/generators/*.scd
