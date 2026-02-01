// core/reference_sine — Calibrated diagnostic generator
/*
Reference Sine — Pure calibrated sine for system verification.

Stripped-down generator that outputs a mathematically precise sine wave
through the same output chain as B258 Dual Morph. Use this to:
  - A/B test whether distortion comes from a generator or the system
  - Verify audio interface DC offset and clipping behavior
  - Validate the Python IdealOverlay math (any deviation = overlay bug)

No morphing, no saturation, no shaping. Just sine → LeakDC → output.

The output should match IdealOverlay's ideal_sine exactly when
all custom params are ignored (they exist only for bus compatibility).

Telemetry taps (when telemetryRate > 0):
  - stage1: Pure sine seed (pre-LeakDC)
  - stage2: Same as stage1 (no morphing)
  - stage3: Final output post-LeakDC + gain
*/

SynthDef(\forge_core_reference_sine, { |out, freqBus, customBus0, slotIndex=0, telemetryRate=0|
    var sig, freq, phase, stage1, stage3, badValue;

    // Frequency: Clamped to safe range
    freq = In.kr(freqBus).clip(5, 20000);

    // Phase tracking for Python sync (normalized 0-1)
    phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);

    // Pure sine seed (unit amplitude)
    sig = SinOsc.ar(freq, 0);
    stage1 = sig;

    // Output stage: same chain as B258 for apples-to-apples comparison
    sig = LeakDC.ar(sig, 0.9999) * 0.66;
    stage3 = sig;

    // Bad value detection
    badValue = CheckBadValues.ar(sig, post: 0);

    // === TELEMETRY handled by forge_internal_telem_tap (no embedded emission) ===

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_reference_sine loaded (diagnostic)".postln;
