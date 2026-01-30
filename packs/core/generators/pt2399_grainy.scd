// core/pt2399_grainy — Lightweight end-stage generator
/*
PT2399 Grainy Generator
Bandpass-filtered noise through lo-fi delay - the "musical" version

Signal flow: Noise -> Bandpass(FRQ) -> Delay -> Light Degradation -> Filter -> ENV VCA -> Output

Custom params:
  - P1 delay_time: 0.001-0.5 s (short = comb, long = echo)
  - P2 feedback: 0.0-0.85 (stays stable)
  - P3 bandwidth: 0.01-1.0 (narrow = tonal, wide = noisy)
  - P4 tone: 0.0-1.0 (dark <-> bright delay character)
  - P5 grit: 0.0-1.0 (clean <-> lo-fi)
*/

SynthDef(\pt2399Grainy, { |out, freqBus, customBus0|
    var sig, source, freq;
    var p = In.kr(customBus0, 5);
    var delayTime, feedback, bandwidth, tone, grit;
    var delayed, dry, fbSig, panPos, pitchWobble, degraded;

    freq = In.kr(freqBus);

    delayTime = p[0];
    feedback = p[1];
    bandwidth = p[2];
    tone = p[3];
    grit = p[4];

    // === SOUND SOURCE ===
    source = WhiteNoise.ar(0.8);
    source = BPF.ar(source, freq.clip(20, 16000), bandwidth.linexp(0.01, 1, 0.01, 0.5)) * 4;

    dry = ~ensure2ch.(source);  // Dual mono for channel strip panning

    fbSig = LocalIn.ar(2);
    pitchWobble = LFNoise1.kr(2).range(0.998, 1.002);
    delayed = DelayC.ar(dry + (fbSig * feedback), 0.6, delayTime * pitchWobble);

    delayed = SelectX.ar(tone, [
        LPF.ar(delayed, 2000),
        delayed,
        HPF.ar(delayed, 500)
    ]);

    degraded = delayed.round(grit.linexp(0, 1, 0.0001, 0.1));
    degraded = degraded + (PinkNoise.ar * grit * 0.05);

    LocalOut.ar(degraded);

    sig = dry + degraded;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] pt2399Grainy loaded".postln;
