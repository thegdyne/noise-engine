/*
FX Slot: LoFi - Bitcrush/Downsample
UI Refresh Phase 1 - Canonical FX slot pattern

Bit depth and sample rate reduction using standard SC UGens.
No sc3-plugins dependency.

Parameter mapping:
  p1 = Rate (0-1 -> sample rate reduction, 1=clean, 0=crushed)
  p2 = Bits (0-1 -> bit depth, 1=16-bit clean, 0=2-bit destruction)
  p3 = Noise (0-1 -> analog hiss amount)
  p4 = Filter (0-1 -> post-LPF, 0=bright/harsh, 1=dark/smooth)
  bypass = Bypass toggle (gates input)

Note: Return level is handled in preMasterMixer, not here.
*/

SynthDef(\fxSlot_lofi, { |inBus, outBus,
                          p1=1.0, p2=1.0, p3=0.0, p4=0.0,
                          bypass=0,
                          p1Bus=(-1), p2Bus=(-1), p3Bus=(-1), p4Bus=(-1)|
    var sig, wet;
    var bypassGate;
    var rateEff, bitsEff, noiseEff, filterEff;
    var rateHz, bitDepth, steps;

    // Bus unification support
    rateEff = Select.kr(p1Bus >= 0, [p1, In.kr(p1Bus)]);
    bitsEff = Select.kr(p2Bus >= 0, [p2, In.kr(p2Bus)]);
    noiseEff = Select.kr(p3Bus >= 0, [p3, In.kr(p3Bus)]);
    filterEff = Select.kr(p4Bus >= 0, [p4, In.kr(p4Bus)]);

    // Smooth params
    rateEff = Lag.kr(rateEff, 0.02);
    bitsEff = Lag.kr(bitsEff, 0.02);
    noiseEff = Lag.kr(noiseEff, 0.02);
    filterEff = Lag.kr(filterEff, 0.02);

    // Read input
    sig = In.ar(inBus, 2);

    // Bypass gates input
    bypassGate = 1 - Lag.kr(bypass, 0.02);
    sig = sig * bypassGate;

    // Rate: 0-1 maps to 500Hz - 44100Hz (exponential)
    // At 1.0 = clean, at 0.0 = heavily crushed
    rateHz = rateEff.linexp(0, 1, 500, SampleRate.ir);

    // Bits: 0-1 maps to 2-16 bits
    // At 1.0 = 16-bit (clean), at 0.0 = 2-bit (destroyed)
    bitDepth = bitsEff.linlin(0, 1, 2, 16);
    steps = 2.pow(bitDepth);

    // Sample rate reduction via Latch
    wet = Latch.ar(sig, Impulse.ar(rateHz));

    // Bit depth reduction via round
    wet = (wet * steps).round / steps;

    // Optional noise/hiss (adds character, but also gated)
    wet = wet + (PinkNoise.ar(0.02) * noiseEff * bypassGate);

    // Post-filter: LPF to tame aliasing artifacts
    // 0 = no filter (18kHz), 1 = aggressive filter (1kHz)
    wet = LPF.ar(wet, filterEff.linexp(0, 1, 18000, 1000));

    // Output wet only (return level handled in preMasterMixer)
    Out.ar(outBus, wet);
}).add;

"  [x] FX Slot: LoFi SynthDef ready".postln;
