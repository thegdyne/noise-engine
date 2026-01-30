// core/vca_ring — Lightweight end-stage generator
/*
VCA Ring Generator
VCA-based ring modulator (softer character)

Signal flow: Carrier through VCA controlled by modulator -> Filter -> ENV VCA -> Output

Custom params:
  - P1 mod_ratio: 0.1-10 (modulator frequency ratio)
  - P2 vca_bias: 0-1 (DC offset/carrier through)
  - P3 vca_response: 0-1 (linear <-> exponential)
  - P4 carrier_wave: 0-1 (sine <-> saw)
  - P5 lfo_mod: 0-1 (additional LFO modulation)
*/

SynthDef(\vcaRing, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var modRatio, vcaBias, vcaResponse, carrierWave, lfoMod;
    var carrier, modulator, modFreq, vcaControl, lfo;

    freq = In.kr(freqBus);

    modRatio = p[0];
    vcaBias = p[1];
    vcaResponse = p[2];
    carrierWave = p[3];
    lfoMod = p[4];

    // === SOUND SOURCE ===
    modFreq = freq * modRatio;

    carrier = SelectX.ar(carrierWave, [
        SinOsc.ar(freq),
        Saw.ar(freq)
    ]);

    modulator = SinOsc.ar(modFreq).range(0, 1);
    lfo = SinOsc.kr(freq * 0.01).range(0.5, 1) * lfoMod + (1 - lfoMod);

    vcaControl = modulator.linexp(0, 1, vcaResponse.linlin(0, 1, 0.01, 0.5), 1);
    vcaControl = (vcaControl * (1 - vcaBias)) + vcaBias;
    vcaControl = vcaControl * lfo;

    sig = carrier * vcaControl * 0.7;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] vcaRing loaded".postln;
