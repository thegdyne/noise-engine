// q121/blades — Lightweight end-stage generator
SynthDef(\forge_q121_blades, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spin, mass, wood, air, sweep;
    var bowNoise, bowPressure, dopplerLFO, dopplerFreq, resonBody, turbulence;

    spin = p[0];
    mass = p[1];
    wood = p[2];
    air = p[3];
    sweep = p[4];

    freq = In.kr(freqBus);

    // Doppler LFO - blade rotation creates pitch sweep
    dopplerLFO = SinOsc.kr(spin.linexp(0, 1, 0.1, 4)).range(0, 1);
    dopplerFreq = freq * (1 + (dopplerLFO * sweep.linlin(0, 1, 0.02, 0.15)));

    // Bowing excitation - continuous friction noise
    bowPressure = mass.linlin(0, 1, 0.3, 0.9);
    bowNoise = PinkNoise.ar(0.3) + LFNoise1.ar(spin.linexp(0, 1, 2, 40) * 0.2);
    bowNoise = bowNoise * bowPressure;

    // Wooden body resonance - comb filtering for wood character
    resonBody = CombL.ar(bowNoise, 0.05, dopplerFreq.reciprocal.clip(0.0005, 0.05), wood.linlin(0, 1, 0.05, 0.4));
    resonBody = resonBody + CombL.ar(bowNoise, 0.05, (dopplerFreq * 2.3).reciprocal.clip(0.0005, 0.05), wood.linlin(0, 1, 0.03, 0.25));

    // Air turbulence layer
    turbulence = BPF.ar(PinkNoise.ar(1), dopplerFreq * 4, 0.5) * air * 0.4;
    turbulence = turbulence + (BrownNoise.ar(0.2) * air * 0.3);

    // Mix
    sig = (resonBody * 0.7) + turbulence;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_blades loaded".postln;
