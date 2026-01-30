// q121/cavity — Lightweight end-stage generator
SynthDef(\forge_q121_cavity, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, modes, concrete, void, drift;
    var exciter, modalBank, driftMod, decayMod, modeRatios;

    depth = p[0];
    modes = p[1];
    concrete = p[2];
    void = p[3];
    drift = p[4];

    freq = In.kr(freqBus);

    // Spectral drift modulation
    driftMod = LFNoise1.kr(drift.linexp(0, 1, 0.05, 0.5)).range(0.98, 1.02);

    // Decay based on concrete damping
    decayMod = concrete.linexp(0, 1, 0.8, 0.2);

    // Excitation - low level continuous noise + void ambience
    exciter = PinkNoise.ar(0.15) + BrownNoise.ar(0.1);
    exciter = exciter + (LFNoise1.ar(void.linexp(0, 1, 0.5, 5)) * void * 0.1);

    // Modal bank - cylindrical tunnel modes
    modeRatios = [1, 1.59, 2.14, 2.65, 2.92, 3.16, 3.5, 3.87];
    modalBank = Mix.fill(8, { |i|
        var modeFreq = freq * modeRatios[i] * driftMod;
        var modeAmp = modes.linlin(0, 1, 0.5, 1) * (1 - (i * 0.1));
        var modeDecay = depth.linexp(0, 1, 0.1, 2) * decayMod * (1 - (i * 0.08));
        Ringz.ar(exciter, modeFreq.clip(20, 18000), modeDecay) * modeAmp * 0.15
    });

    // Add sub-bass void rumble
    sig = modalBank + (SinOsc.ar(freq * 0.5) * void * 0.2 * LFNoise2.kr(0.3).range(0.5, 1));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_cavity loaded".postln;
