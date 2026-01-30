// rakshasa/wild_mane — Lightweight end-stage generator
// Wild Mane -- Chaotic hair texture with granular noise
// Role: motion | Family: texture

SynthDef(\forge_rakshasa_wild_mane, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wild, frizz, tangle, whip, static;
    var strands, crackle, chaos, tangled, layers;
    var whipRate, chaosLFO, panMod;

    // Standard bus reads
    freq = In.kr(freqBus);

    // Custom parameters
    wild = p[0].linlin(0, 1, 0.1, 1);  // Chaos amount
    frizz = p[1].linexp(0, 1, 10, 200);  // Grain density
    tangle = p[2].linlin(0, 1, 1, 5);  // Number of layers
    whip = p[3].linexp(0, 1, 0.5, 30);  // Movement rate
    static = p[4].linlin(0, 1, 0, 0.5);  // HF crackle mix

    // Whipping movement
    whipRate = whip;
    chaosLFO = LFNoise2.kr(whipRate) * wild;

    // Hair strand layers -- filtered noise bursts
    strands = Dust.ar(frizz) * WhiteNoise.ar;
    strands = RLPF.ar(strands, freq * (1 + (chaosLFO * 2)).clip(0.5, 4), 0.3);

    // Tangled complexity -- multiple detuned layers
    layers = Mix.fill(8, { |i|
        var detune, rate, strand, ampScale;
        ampScale = ((tangle * 8) > i).asInteger;
        detune = LFNoise1.kr(whipRate * 0.3).range(0.8, 1.2);
        rate = frizz * LFNoise0.kr(2).range(0.5, 1.5);
        strand = Dust.ar(rate) * BrownNoise.ar;
        RLPF.ar(strand, freq * detune * (1 + (i * 0.2)), 0.4 + (i * 0.1)) * ampScale
    }) / 8;

    // High frequency static/crackle
    crackle = Dust2.ar(frizz * 3) * 0.3;
    crackle = HPF.ar(crackle, 4000);

    // Mix all elements
    sig = (strands * 0.5) + (layers * 0.4) + (crackle * static);

    // Wild stereo movement
    panMod = LFNoise2.kr(whipRate * 0.7) * wild;
    sig = Pan2.ar(sig, panMod);

    sig = sig * 4;  // gain boost

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_rakshasa_wild_mane loaded".postln;
