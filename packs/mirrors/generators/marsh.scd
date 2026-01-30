// mirrors/marsh — Lightweight end-stage generator
SynthDef(\forge_mirrors_marsh, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var windAmt, reeds, water, flat, chill;
    var windNoise, reedRustle, waterLow, space;

    windAmt = p[0];
    reeds = p[1];
    water = p[2];
    flat = p[3];
    chill = p[4];

    freq = In.kr(freqBus);

    // Marsh wind - broad filtered noise
    windNoise = PinkNoise.ar(0.4) + BrownNoise.ar(0.25);
    windNoise = BPF.ar(windNoise, freq * LFNoise2.kr(0.2).range(0.7, 1.5), 0.5) * 2;
    windNoise = windNoise * LFNoise2.kr(0.3 + (windAmt * 0.5)).range(0.4, 1.0);
    windNoise = windNoise * (0.4 + (windAmt * 0.6));

    // Reed rustle - high frequency
    reedRustle = HPF.ar(WhiteNoise.ar(0.3), 2500 + (chill * 2000));
    reedRustle = reedRustle * LFNoise2.kr(4 + (reeds * 8)).range(0.3, 1.0);
    reedRustle = reedRustle * (0.3 + (reeds * 0.7));

    // Standing water low resonance
    waterLow = LPF.ar(BrownNoise.ar(0.4), 150 + (freq * 0.3));
    waterLow = waterLow + BPF.ar(BrownNoise.ar(0.25), freq * 0.5, 0.3) * 2;
    waterLow = waterLow * (0.3 + (water * 0.7));

    sig = windNoise + reedRustle + waterLow;

    // Flat landscape openness - allpass reverb
    space = sig;
    space = AllpassC.ar(space, 0.3, flat.linlin(0, 1, 0.05, 0.2), flat * 2.5);
    space = AllpassC.ar(space, 0.3, flat.linlin(0, 1, 0.08, 0.25), flat * 2);

    sig = (sig * (1 - (flat * 0.4))) + (space * flat * 0.5);

    // Pitched wind tone
    sig = sig + BPF.ar(PinkNoise.ar(0.2), freq, 0.35) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.12), 300);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_marsh loaded".postln;
