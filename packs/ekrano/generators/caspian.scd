// ekrano/caspian — Lightweight end-stage generator
SynthDef(\forge_ekrano_caspian, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wave, chop, salt, depth, foam;
    var grainTrig, grainRate, grainFreq, grainSig, foamSig, saltSig;

    freq = In.kr(freqBus);

    wave = p[0].linexp(0, 1, 5, 80);
    chop = p[1].linlin(0, 1, 0.1, 0.9);
    salt = p[2];
    depth = p[3].linexp(0, 1, 0.5, 2);
    foam = p[4].linlin(0, 1, 0.1, 0.8);

    // Grain trigger with choppiness variation
    grainRate = wave * LFNoise1.kr(2).range(1 - (chop * 0.5), 1 + (chop * 0.5));
    grainTrig = Dust.ar(grainRate);

    // Grain frequency modulated by depth
    grainFreq = freq * LFNoise0.kr(10).range(1 / depth, depth);

    // Granular sine clouds - water wave character
    grainSig = GrainSin.ar(
        numChannels: 2,
        trigger: grainTrig,
        dur: LFNoise1.kr(3).range(0.02, 0.08),
        freq: grainFreq,
        pan: LFNoise1.kr(5).range(-0.8, 0.8)
    );

    // Foam layer - filtered noise bursts
    foamSig = BPF.ar(
        WhiteNoise.ar(Decay.ar(Dust.ar(wave * 0.5), 0.05)),
        freq * 3,
        0.5
    ) * foam;

    // Salt spray - high frequency crackle
    saltSig = HPF.ar(Dust.ar(wave * 2) * 0.3, 6000) * salt;

    sig = (grainSig * 0.5) + (foamSig * 0.3) + (saltSig * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_caspian loaded".postln;
