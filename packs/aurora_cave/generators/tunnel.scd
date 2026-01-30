// aurora_cave/tunnel — Lightweight end-stage generator
SynthDef(\forge_aurora_cave_tunnel, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wind, length, mouth, howl, cold;
    var breath, tube, hiss, modFreq;

    freq = In.kr(freqBus);

    wind = p[0];
    length = p[1];
    mouth = p[2];
    howl = p[3];
    cold = p[4];

    // Wind breath source - turbulent noise
    breath = LFNoise1.ar(wind.linexp(0, 1, 20, 200)) * wind;
    breath = breath + (LFNoise2.ar(wind.linexp(0, 1, 50, 400)) * wind * 0.5);
    breath = breath * LFNoise2.kr(wind.linexp(0, 1, 0.2, 2)).range(0.3, 1);

    // Tube resonance via waveguide
    tube = CombL.ar(
        breath,
        0.1,
        (freq * length.linlin(0, 1, 0.5, 2)).reciprocal,
        howl.linlin(0, 1, 0.5, 3)
    );

    // Add harmonics based on mouth opening
    tube = tube + CombL.ar(
        breath * mouth,
        0.05,
        (freq * 2 * length.linlin(0, 1, 0.5, 2)).reciprocal,
        howl.linlin(0, 1, 0.3, 2)
    ) * mouth;

    tube = tube + CombL.ar(
        breath * mouth * 0.5,
        0.033,
        (freq * 3 * length.linlin(0, 1, 0.5, 2)).reciprocal,
        howl.linlin(0, 1, 0.2, 1.5)
    ) * mouth * 0.7;

    // Howling modulation
    modFreq = SinOsc.kr(howl.linexp(0, 1, 0.1, 0.8)).range(0.97, 1.03);
    tube = DelayC.ar(tube, 0.02, (freq * modFreq).reciprocal.clip(0.0001, 0.02) * howl * 0.5);

    // Cold air hiss
    hiss = WhiteNoise.ar * cold * 0.15;
    hiss = HPF.ar(hiss, cold.linexp(0, 1, 2000, 6000));
    hiss = hiss * LFNoise2.kr(1).range(0.5, 1);

    // Mix
    sig = (tube * 0.4) + hiss;

    // Damping based on length (longer = darker)
    sig = LPF.ar(sig, length.linexp(0, 1, 4000, 1500));

    sig = sig * 4;
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_aurora_cave_tunnel loaded".postln;
