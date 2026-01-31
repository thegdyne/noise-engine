// core/hw_assessment_tap — Hardware DNA Probe for external gear profiling
/*
Hardware Assessment Tap — Phase 1: Digital Twin Profiling

Routes external hardware audio (via MOTU M6 inputs) through the telemetry
system for real-time comparison with IdealOverlay. Use this to:
  - Profile a physical synth (Buchla 258, etc.) through the audio interface
  - Compare hardware waveforms against mathematical ideal
  - Extract DC bias, harmonic signature, and saturation curves
  - Build a "Digital Twin" calibration dataset

SAFETY: User must attenuate hardware signal with MOTU M6 front-panel
GAIN knobs until Stage 1 Peak stays below 0.95.

Phase tracking uses a Schmitt trigger (hysteresis ±0.05) for jitter-free
zero-crossing detection on noisy/complex hardware waveforms.

Custom params:
  - P0 input_chan: MOTU M6 input channel (0-5)
  - P1 input_gain: Level normalization multiplier (0-4x)
  - P2 mix: Reserved (unused in Phase 1)
  - P3 symmetry: Sent to telemetry for IdealOverlay bias alignment
  - P4 saturation: Sent to telemetry for IdealOverlay saturation matching

Telemetry taps (when telemetryRate > 0):
  - stage1: Raw hardware input (pre-normalization)
  - stage2: Normalized input (post-gain, clipped to ±1)
  - stage3: Output stage (same chain as B258/Reference Sine)
*/

SynthDef(\forge_core_hw_assessment_tap, { |out, freqBus, customBus0, slotIndex=0, telemetryRate=0|
    var sig, freq, p;
    var inputChan, inGain;
    var hw, stage1, stage2, stage3;
    var phase, badValue;

    // Schmitt trigger variables
    var schmittLo = -0.05, schmittHi = 0.05;
    var belowLo, aboveHi, armed, zc;
    var period, sampPerCycle, phaseInc;

    // Contiguous 5-channel custom bus read
    p = In.kr(customBus0, 5);

    // --- PARAMETER MAPPING ---
    inputChan = Lag.kr(p[0].round(1).clip(0, 5), 0.1);  // P0: Input channel (integer)
    inGain    = Lag.kr(p[1].clip(0, 4), 0.05);           // P1: Level normalization

    // Frequency from bus (used for reference only)
    freq = In.kr(freqBus).clip(5, 20000);

    // --- HARDWARE TAP ---
    // Read all 6 MOTU M6 inputs, select by channel param
    hw = Select.ar(inputChan, SoundIn.ar((0..5)));

    // Stage 1: Raw hardware input (DC-transparent for assessment)
    stage1 = hw;

    // --- SCHMITT-TRIGGERED PHASE SYNC ---
    // Hysteresis: must drop below -0.05 before allowing new +0.05 trigger
    // Prevents double-triggering on noisy or complex waveforms
    belowLo = hw < schmittLo;
    aboveHi = hw > schmittHi;

    // SetResetFF: arms (goes high) when signal drops below low threshold,
    // disarms (goes low) when signal rises above high threshold
    armed = SetResetFF.ar(belowLo, aboveHi);

    // Zero-crossing trigger: rising edge through schmittHi while armed
    zc = Trig1.ar(aboveHi * armed, SampleDur.ir);

    // Period measurement (Timer counts seconds between triggers)
    period = Timer.ar(zc).max(SampleDur.ir);
    sampPerCycle = (period * SampleRate.ir).clip(
        SampleRate.ir / 5000,  // Max 5kHz
        SampleRate.ir / 10     // Min 10Hz
    );

    // High-fidelity phase ramp for Python overlay alignment
    phaseInc = 1.0 / sampPerCycle;
    phase = Phasor.ar(zc, phaseInc, 0, 1);

    // --- NORMALIZED STAGE ---
    // Stage 2: Gain-adjusted, clipped to safe range
    stage2 = (hw * inGain).clip(-1, 1);

    // --- OUTPUT STAGE ---
    // Same chain as B258/Reference Sine for apples-to-apples comparison
    sig = LeakDC.ar(stage2, 0.9999) * 0.66;
    stage3 = sig;

    // Bad value detection
    badValue = CheckBadValues.ar(sig, post: 0);

    // === TELEMETRY (only active when telemetryRate > 0) ===
    SendReply.kr(Impulse.kr(telemetryRate) * (telemetryRate > 0), '/noise/telem/gen', [
        slotIndex,
        A2K.kr(1.0 / period.max(SampleDur.ir)),    // Detected frequency from hardware
        A2K.kr(phase),                               // Schmitt-triggered phase ramp
        p[0], p[1], p[2], p[3], p[4],              // P0-P4 raw values
        Amplitude.ar(stage1, 0.01, 0.1),            // RMS of raw hardware
        Amplitude.ar(stage2, 0.01, 0.1),            // RMS of normalized
        Amplitude.ar(stage3, 0.01, 0.1),            // RMS of output
        Peak.ar(stage1, Impulse.kr(telemetryRate.max(0.1))).lag(0.1),  // Peak of RAW input
        A2K.kr(badValue)
    ]);

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_hw_assessment_tap loaded (Hardware DNA Probe)".postln;
