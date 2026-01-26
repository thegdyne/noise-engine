/*
FX Slot: Empty - Silent Passthrough
UI Refresh Phase 1 - Canonical FX slot pattern

Outputs silence. Used when slot is "empty" or as template for new effects.
Follows the canonical p1-p4 + bypass pattern.

Note: Return level is handled in preMasterMixer, not here.
*/

SynthDef(\fxSlot_empty, { |inBus, outBus,
                           p1=0.5, p2=0.5, p3=0.5, p4=0.5,
                           bypass=0,
                           p1Bus=(-1), p2Bus=(-1), p3Bus=(-1), p4Bus=(-1)|
    // Empty slot outputs silence
    // params are ignored but accepted for uniform interface
    Out.ar(outBus, Silent.ar(2));
}).add;

"  [x] FX Slot: Empty SynthDef ready".postln;
