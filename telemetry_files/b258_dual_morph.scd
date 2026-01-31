// core/b258_dual_morph — Lightweight end-stage generator with telemetry
/*
B258 Dual Morph Generator
Digital reconstruction of Buchla 258 wavefolder with smooth sine→square→saw morphing.

Features:
  - Dual-branch topology: tanh-driven square + node-folded saw
  - Unified morph control (0=sine, 0.5=square, 1.0=saw)
  - Phase-locked telemetry for Python overlay sync
  - CheckBadValues for CORE LOCK detection
  - LeakDC at end with 0.995 coefficient (preserves flat tops)

Custom params:
  - P0 drive: Pre-fold gain (1-60x)
  - P1 shape: Saw blend in fold path
  - P2 morph: Sine (0) → Square (0.5) → Saw (1.0)
  - P3 sym: Symmetry offset (-0.5 to 0.5)
  - P4 sat: Output saturation (1-12x)

Telemetry taps:
  - stage1: Pure sine input
  - stage2: After fold/shape processing
  - stage3: Final output (post-LeakDC)

Reference: DIRECT_OSC_TELEMETRY_SPEC.md
*/

SynthDef(\forge_core_b258_dual_morph, { |out, freqBus, customBus0, telemetryRate=0|
    var sig, freq, p;
    var drive, shape, morph, sym, sat;
    var sine, sqrPart, sawPart;
    var stage1, stage2, stage3;  // Telemetry taps
    var phase, badValue;
    
    // Contiguous 5-channel custom bus read
    p = In.kr(customBus0, 5);
    
    // === PARAMETER MAPPING (Elastic Smoothing) ===
    // Smoothing prevents "zipper" noise during parameter sweeps
    drive = Lag.kr(p[0], 0.05);
    shape = Lag.kr(p[1], 0.05);
    morph = Lag.kr(p[2], 0.05);
    sym   = Lag.kr(p[3].linlin(0, 1, -0.5, 0.5), 0.06);
    sat   = Lag.kr(p[4], 0.08);
    
    // Frequency with safety clamp
    freq = In.kr(freqBus).clip(5, 20000);
    
    // Phase tracking for Python sync (normalized 0-1)
    phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);
    
    // === 1. THE SEED: High-precision Sine ===
    sine = SinOsc.ar(freq, 0);
    stage1 = sine;  // TAP: Pure input
    
    // === 2. THE SQUARE PATH: Tanh-driven ===
    // This prevents the "rounding" seen in naive square generation
    sqrPart = (sine + sym) * drive.linexp(0, 1, 1, 60);
    sqrPart = sqrPart.tanh;
    
    // === 3. THE SAW PATH: 258 "Node" Folding ===
    // Mixing Phasor with Sine and folding creates the sharp "snap"
    sawPart = (sine * (1 - shape)) + (LFSaw.ar(freq, 1) * shape);
    sawPart = (sawPart + sym).fold2(0.9);
    stage2 = sawPart;  // TAP: After fold
    
    // === 4. UNIFIED MORPH: Sine (0.0) → Square (0.5) → Saw (1.0) ===
    sig = SelectX.ar(morph * 2, [sine, sqrPart, sawPart]);
    
    // === 5. POST-PROCESSING: Final Warmth and DC Hygiene ===
    sig = (sig * sat.linexp(0, 1, 1, 12)).softclip;
    
    // CRITICAL: LeakDC at the very end with high coefficient
    // This preserves flat tops on square waves
    sig = LeakDC.ar(sig, 0.995);
    stage3 = sig;  // TAP: Final output
    
    // Bad value detection (catches NaN/inf from extreme settings)
    badValue = CheckBadValues.ar(sig, post: 0);
    
    // === TELEMETRY (only active when telemetryRate > 0) ===
    // Zero CPU overhead when disabled
    (telemetryRate > 0).if {
        SendReply.kr(Impulse.kr(telemetryRate), '/telem/gen', [
            \slotIndex.ir(0),       // Slot index for routing
            freq,                    // Current frequency
            A2K.kr(phase),          // Normalized 0-1 phase for Python sync
            p[0], p[1], p[2], p[3], p[4],  // P0-P4 raw values
            Amplitude.ar(stage1, 0.01, 0.1),  // RMS of pure sine
            Amplitude.ar(stage2, 0.01, 0.1),  // RMS after fold
            Amplitude.ar(stage3, 0.01, 0.1),  // RMS final output
            Peak.ar(sig, Impulse.kr(telemetryRate)).lag(0.1),  // Peak level
            A2K.kr(badValue)        // 0=clean, 1=NaN, 2=inf
        ]);
    };
    
    // === MANDATORY TAIL ===
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig * 0.75);  // Headroom trim
}).add;

"  [x] forge_core_b258_dual_morph loaded (with telemetry)".postln;
