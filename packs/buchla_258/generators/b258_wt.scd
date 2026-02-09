// buchla_258/b258_wt — Wavetable Morph Generator
/*
B258 WT - Buchla 258 Wavetable Clone

WAVETABLE SYNTHESIS from actual hardware waveform captures.

Each morph table contains 128 single-cycle waveform frames (2048 samples each)
interpolated from 26-point hardware CV sweeps via per-sample cubic spline.
Source waveforms are 1024-sample captures from the Buchla 258 clone's audio
output, resampled to 2048 for SuperCollider wavetable playback.

These are the REAL hardware waveforms, not synthesized approximations.

=== WAVETABLE SPECIFICATION ===

128 frames x 2048 samples per frame, 48 kHz, float32 WAV
SAW buffer (b258_wt_saw.wav): sine→saw morph
SQR buffer (b258_wt_sqr.wav): sine→square morph

Hardware source:
  SAW sweep: morph_map_buchla_258_20260206_140115.json (39.3 Hz, 26 pts)
  SQR sweep: morph_map_buchla_258_20260206_140441.json (49.8 Hz, 26 pts)

=== CONTROL MAPPING ===

P0 SAW: Sine→Saw morph (selects frame 0-127 in SAW wavetable)
P1 SQR: Sine→Square morph (selects frame 0-127 in SQR wavetable)
P2 MIX: Crossfade between SAW and SQR oscillator outputs

=== BUFFER LOADING ===

Buffers are loaded automatically from WAV files alongside this .scd file.
Buffer numbers are baked into the SynthDef at compile time.
Generate WAVs with: python tools/generate_b258_wavetables.py
*/

(
var packDir = thisProcess.nowExecutingPath.dirname;
var sawPath = packDir +/+ "b258_wt_saw.wav";
var sqrPath = packDir +/+ "b258_wt_sqr.wav";
var sawBuf, sqrBuf;

if (File.exists(sawPath).not or: { File.exists(sqrPath).not }) {
    "  [!] b258_wt SKIPPED — wavetable WAV files not found".postln;
    ("      Expected: " ++ sawPath).postln;
    ("      Expected: " ++ sqrPath).postln;
    "      Run: python tools/generate_b258_wavetables.py".postln;
} {
    // Load wavetable buffers — bufnums assigned immediately (client-side)
    sawBuf = Buffer.read(s, sawPath);
    sqrBuf = Buffer.read(s, sqrPath);

    // Store in environment for debugging/reference
    ~wtBuffers = ~wtBuffers ? IdentityDictionary.new;
    ~wtBuffers[\b258_wt_saw] = sawBuf;
    ~wtBuffers[\b258_wt_sqr] = sqrBuf;

    SynthDef(\b258_wt, { |out, freqBus, customBus0|
        var sigSaw, sigSqr, sig, freq;
        var params, sawMorph, sqrMorph, mix;
        var phasor, sawPos, sqrPos;
        var frameSize = 2048;
        var numFrames = 128;

        // =======================================================
        // INPUTS
        // =======================================================
        params = In.kr(customBus0, 5);
        sawMorph = Lag.kr(params[0], 0.05).clip(0, 1);
        sqrMorph = Lag.kr(params[1], 0.05).clip(0, 1);
        mix      = Lag.kr(params[2], 0.05).clip(0, 1);

        freq = In.kr(freqBus).clip(5, 20000);

        // =======================================================
        // PHASE TRACKING
        // Phasor sweeps 0..frameSize at the desired frequency,
        // giving us one cycle per period.
        // =======================================================
        phasor = Phasor.ar(0, freq * frameSize / SampleRate.ir, 0, frameSize);

        // =======================================================
        // SAW WAVETABLE READ
        // Frame offset = sawMorph * (numFrames - 1) * frameSize
        // Read position = frame_offset + phasor
        // BufRd with cubic interpolation for smooth inter-sample reading
        // =======================================================
        sawPos = (sawMorph * (numFrames - 1)).round(1) * frameSize + phasor;
        sigSaw = BufRd.ar(1, sawBuf.bufnum, sawPos, 0, 4);

        // =======================================================
        // SQR WAVETABLE READ
        // Same approach with sqrMorph selecting frame
        // =======================================================
        sqrPos = (sqrMorph * (numFrames - 1)).round(1) * frameSize + phasor;
        sigSqr = BufRd.ar(1, sqrBuf.bufnum, sqrPos, 0, 4);

        // =======================================================
        // MIX - Crossfade between SAW and SQR outputs
        // =======================================================
        sig = XFade2.ar(sigSaw, sigSqr, mix * 2 - 1); // XFade2 takes -1..+1

        // Scale to reasonable output level
        sig = sig * 2.5;

        // Safety
        sig = LeakDC.ar(sig);
        sig = sig.clip(-1.5, 1.5);

        // --- MANDATORY TAIL ---
        sig = NumChannels.ar(sig, 2);
        ReplaceOut.ar(out, sig);
    }).add;

    "  [x] b258_wt loaded (128-frame wavetable morph from hardware captures)".postln;
    ("      SAW buf: " ++ sawBuf.bufnum ++ " → " ++ sawPath).postln;
    ("      SQR buf: " ++ sqrBuf.bufnum ++ " → " ++ sqrPath).postln;
};
)
