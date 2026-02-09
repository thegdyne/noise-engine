// buchla_258_wavetables/b258_wt — Wavetable morph from hardware telemetry
/*
B258 Wavetable — Buchla 258 Telemetry Wavetable Generator

Plays back captured 1024-sample waveforms from 26-point hardware telemetry
as wavetable sources using VOsc for click-free interpolation.

Two independent morph axes from real Buchla 258 hardware captures:
  SAW: 26-point sine→saw sweep (0-5V CV via CV.OCD)
  SQR: 26-point sine→square sweep (0-5V CV via CV.OCD)

Controls:
  P0 SAW: Position in sine→saw table set (interpolated across 26 tables)
  P1 SQR: Position in sine→square table set (interpolated across 26 tables)
  P2 MIX: Crossfade between SAW and SQR tracks

Processing policy: DC preserved, gain preserved (authentic amplitude rise),
phase alignment assumed from captures.

Data source: morph_map JSON captures from Buchla 258 hardware
*/

// === BUFFER ALLOCATION ===
// 26 wavetable buffers per set, 2048 frames (SC wavetable format for 1024-pt tables)
// Buffer.allocConsecutive assigns bufnums immediately (client-side)
~b258_wt_sawBufs = Buffer.allocConsecutive(26, s, 2048, 1);
~b258_wt_sqrBufs = Buffer.allocConsecutive(26, s, 2048, 1);
~b258_wt_sawStart = ~b258_wt_sawBufs[0].bufnum;
~b258_wt_sqrStart = ~b258_wt_sqrBufs[0].bufnum;
~b258_wt_sawLoaded = 0;
~b258_wt_sqrLoaded = 0;

// === OSC HANDLER: Receive waveform data from Python ===
// msg format: /noise/b258_wt/load [tableType(0=saw,1=sqr), tableIndex(0-25), ...1024 floats...]
// Python sends raw PCM samples; SC converts to wavetable format and loads into buffer.
OSCdef(\b258_wt_load, { |msg|
    var tableType = msg[1].asInteger;  // 0=saw, 1=sqr
    var tableIndex = msg[2].asInteger; // 0-25
    var rawSamples = FloatArray.newFrom(msg[3..]);
    var buf, sig, wt;

    buf = if(tableType == 0, {
        ~b258_wt_sawBufs[tableIndex]
    }, {
        ~b258_wt_sqrBufs[tableIndex]
    });

    // Convert raw PCM (1024 samples) to SC wavetable format (2048 values)
    sig = Signal.newFrom(rawSamples);
    wt = sig.asWavetable;
    buf.loadCollection(wt);

    // Track loading progress
    if(tableType == 0, {
        ~b258_wt_sawLoaded = ~b258_wt_sawLoaded + 1;
        if(~b258_wt_sawLoaded >= 26, {
            "  [x] b258_wt: SAW tables loaded (26)".postln;
        });
    }, {
        ~b258_wt_sqrLoaded = ~b258_wt_sqrLoaded + 1;
        if(~b258_wt_sqrLoaded >= 26, {
            "  [x] b258_wt: SQR tables loaded (26)".postln;
        });
    });

    if((~b258_wt_sawLoaded >= 26) && (~b258_wt_sqrLoaded >= 26), {
        "  [x] b258_wt: ALL 52 wavetables ready".postln;
    });
}, '/noise/b258_wt/load');

// === OSC HANDLER: Query buffer info ===
OSCdef(\b258_wt_info, { |msg, time, addr|
    addr.sendMsg('/noise/b258_wt/info',
        ~b258_wt_sawStart,
        ~b258_wt_sqrStart,
        ~b258_wt_sawLoaded,
        ~b258_wt_sqrLoaded
    );
}, '/noise/b258_wt/query');

// === SYNTHDEF ===
// Captures buffer start indices at compile time (integer constants in UGen graph)
(
var sawStart = ~b258_wt_sawStart;
var sqrStart = ~b258_wt_sqrStart;

SynthDef(\b258_wt, { |out, freqBus, customBus0|
    var p, sawMorph, sqrMorph, mix;
    var freq, sawBufPos, sqrBufPos;
    var sawSig, sqrSig, sig;

    p = In.kr(customBus0, 5);
    sawMorph = Lag.kr(p[0], 0.05);  // P0 SAW: table position
    sqrMorph = Lag.kr(p[1], 0.05);  // P1 SQR: table position
    mix      = Lag.kr(p[2], 0.05);  // P2 MIX: crossfade

    freq = In.kr(freqBus).clip(5, 20000);

    // VOsc: floating-point buffer index interpolates between adjacent tables
    // Range: bufStart to bufStart+25 (26 consecutive wavetable buffers)
    sawBufPos = sawStart + (sawMorph.clip(0, 1) * 25);
    sqrBufPos = sqrStart + (sqrMorph.clip(0, 1) * 25);

    sawSig = VOsc.ar(sawBufPos, freq);
    sqrSig = VOsc.ar(sqrBufPos, freq);

    // Crossfade: MIX 0 = pure SAW track, MIX 1 = pure SQR track
    sig = XFade2.ar(sawSig, sqrSig, mix.linlin(0, 1, -1, 1));

    // Gentle output scaling (authentic gain preserved in tables)
    sig = sig * 0.7;

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
);

"  [x] b258_wt loaded (wavetable morph from 26-pt hardware telemetry, 52 buffers allocated)".postln;
