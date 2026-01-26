/*
FX Slot: Reverb - Plate/Room
UI Refresh Phase 1 - Canonical FX slot pattern

Adapted from reverb.scd to use generic p1-p4 parameters.

Parameter mapping:
  p1 = Size (0-1 room size)
  p2 = Decay (0-1)
  p3 = Tone (0-1 -> LPF freq)
  p4 = Damping (0-1)
  bypass = Bypass toggle (gates input, lets tail decay)

Note: Return level is handled in preMasterMixer, not here.
*/

SynthDef(\fxSlot_reverb, { |inBus, outBus,
                            p1=0.75, p2=0.65, p3=0.7, p4=0.5,
                            bypass=0,
                            p1Bus=(-1), p2Bus=(-1), p3Bus=(-1), p4Bus=(-1)|
    var sig, verb, toneFreq;
    var wet, bypassGate;
    var sizeEff, decayEff, toneEff, dampEff;

    // Bus unification support
    sizeEff = Select.kr(p1Bus >= 0, [p1, In.kr(p1Bus)]);
    decayEff = Select.kr(p2Bus >= 0, [p2, In.kr(p2Bus)]);
    toneEff = Select.kr(p3Bus >= 0, [p3, In.kr(p3Bus)]);
    dampEff = Select.kr(p4Bus >= 0, [p4, In.kr(p4Bus)]);

    // Smooth params
    sizeEff = Lag.kr(sizeEff, 0.05);
    decayEff = Lag.kr(decayEff, 0.05);
    toneEff = Lag.kr(toneEff, 0.02);
    dampEff = Lag.kr(dampEff, 0.02);

    // Map tone to LPF freq (2000-12000Hz)
    toneFreq = toneEff.linexp(0, 1, 2000, 12000);

    // Read input
    sig = In.ar(inBus, 2);

    // Bypass gates input (lets reverb tail decay naturally)
    bypassGate = 1 - Lag.kr(bypass, 0.02);
    sig = sig * bypassGate;

    // HPF to prevent low-end wash
    sig = HPF.ar(sig, 80);

    // FreeVerb (100% wet on send bus)
    verb = FreeVerb2.ar(sig[0], sig[1],
        mix: 1,
        room: sizeEff,
        damp: dampEff + ((1 - decayEff) * 0.5)  // Combine damping + decay
    );

    // Tone control
    wet = LPF.ar(verb, toneFreq);

    // Output wet only (return level handled in preMasterMixer)
    Out.ar(outBus, wet);
}).add;

"  [x] FX Slot: Reverb SynthDef ready".postln;
