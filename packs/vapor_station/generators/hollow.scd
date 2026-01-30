// vapor_station/hollow — Lightweight end-stage generator
// hollow: Empty station void and silence
SynthDef(\forge_vapor_station_hollow, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var space, distant, lonely, concrete, wind;

    space = p[0].linlin(0, 1, 0.3, 0.9);  // P1: Reverb space size
    distant = p[1].linlin(0, 1, 0.1, 0.6);  // P2: Distant sounds
    lonely = p[2].linlin(0, 1, 0.2, 0.7);  // P3: Lonely tone
    concrete = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Concrete resonance
    wind = p[4].linlin(0, 1, 0.2, 0.6);  // P5: Night wind

    freq = In.kr(freqBus);

    // DSP: Base - continuous filtered noise
    sig = LPF.ar(PinkNoise.ar(0.3), 800);

    // Large space reverb simulation via comb filters
    sig = sig + CombL.ar(sig * 0.3, 0.3, space * 0.15 + 0.05, space * 3);

    // Distant sounds - sparse impacts
    sig = sig + (Ringz.ar(Dust.ar(distant * 4) * 0.2, freq * [1, 1.5], space) * distant);

    // Lonely tone - single wavering sine (always present)
    sig = sig + (SinOsc.ar(freq * [1, 1.003] * LFNoise1.kr(0.1).range(0.99, 1.01)) * lonely * 0.25);

    // Concrete resonance - boosted
    sig = sig + (Resonz.ar(Dust.ar(concrete * 5) * 0.3, freq * [0.5, 1, 2], 0.15) * concrete * 5);

    // Night wind - continuous
    sig = sig + (BPF.ar(BrownNoise.ar(wind), 300 * LFNoise1.kr(0.05).range(0.5, 2), 0.6) * 0.6);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_hollow loaded".postln;
