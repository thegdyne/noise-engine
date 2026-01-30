// glacialis/borealis — Lightweight end-stage generator
// BOREALIS - Aurora sweep and shimmer
// AM chorus with phase spread for curtain-like motion

SynthDef(\forge_glacialis_borealis, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wave, sweep, curtain, glow, phase;
    var voices, sweepLFO, carrier, am, voiceSig;

    wave = p[0];  // Waveform
    sweep = p[1];  // Sweep rate
    curtain = p[2];  // Voice layers
    glow = p[3];  // Saturation
    phase = p[4];  // Phase spread

    freq = In.kr(freqBus);

    // Main sweep LFO
    sweepLFO = SinOsc.kr(sweep.linexp(0, 1, 0.03, 0.5));

    // Multiple voice layers with phase offset - 6 voices with crossfade
    voices = Mix.fill(6, { |i|
        var voicePhase, detune, amRate, voiceAmp, osc;

        // Voice amplitude based on curtain parameter
        voiceAmp = (curtain * 6 - i).clip(0, 1) * (6 - i).reciprocal;

        // Phase offset per voice
        voicePhase = i * phase * pi / 3;

        // Slight detune per voice
        detune = 1 + (i * 0.003 * phase);

        // AM rate varies per voice
        amRate = sweep.linexp(0, 1, 0.5, 4) * (1 + (i * 0.2));

        // Carrier oscillator - blend between sine and triangle based on wave
        osc = (SinOsc.ar(freq * detune, voicePhase) * (1 - wave)) +
              (LFTri.ar(freq * detune, voicePhase / (2pi)) * wave);

        // AM modulation
        am = SinOsc.kr(amRate, i * 0.5).range(0.3, 1);

        osc * am * voiceAmp
    });

    sig = voices * 0.4;

    // Soft saturation for glow
    sig = (sig * (1 + glow)).tanh * (1 + glow).reciprocal;

    // Sweep filter modulation
    sig = RLPF.ar(sig,
        sweepLFO.range(freq * 2, freq * 8).clip(100, 16000),
        0.5
    );

    // Stereo phase spread
    sig = [
        sig + (DelayC.ar(sig, 0.05, phase.linlin(0, 1, 0.003, 0.02)) * 0.3),
        sig + (DelayC.ar(sig, 0.05, phase.linlin(0, 1, 0.005, 0.025)) * 0.3)
    ];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_borealis loaded".postln;
