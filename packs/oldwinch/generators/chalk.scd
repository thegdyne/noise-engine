// oldwinch/chalk — Lightweight end-stage generator
SynthDef(\forge_oldwinch_chalk, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var grass, down, white, soil, openAmt;
    var grassRustle, downWind, chalkTone, soilLow, space;

    grass = p[0];
    down = p[1];
    white = p[2];
    soil = p[3];
    openAmt = p[4];

    freq = In.kr(freqBus);

    // Grass rustle - high frequency filtered noise
    grassRustle = HPF.ar(WhiteNoise.ar(0.35), 2000 + (white * 3000));
    grassRustle = grassRustle * LFNoise2.kr(3 + (grass * 8)).range(0.4, 1.0);
    grassRustle = grassRustle * (0.3 + (grass * 0.7));

    // Downland wind
    downWind = BPF.ar(PinkNoise.ar(0.5), freq * down.linlin(0, 1, 1, 3), 0.4) * 2;
    downWind = downWind * LFNoise2.kr(0.3 + (down * 0.5)).range(0.5, 1.0);
    downWind = downWind * (0.4 + (down * 0.6));

    // Chalk tone - bright filtered
    chalkTone = BPF.ar(PinkNoise.ar(0.4) + WhiteNoise.ar(0.2 * white), freq * 2, 0.3) * 3;
    chalkTone = chalkTone * white;

    // Soil low frequency
    soilLow = LPF.ar(BrownNoise.ar(0.4), 200 + (freq * 0.3));
    soilLow = soilLow * (0.3 + (soil * 0.7));

    sig = grassRustle + downWind + chalkTone + soilLow;

    // Open landscape reverb
    space = sig;
    space = AllpassC.ar(space, 0.3, openAmt.linlin(0, 1, 0.05, 0.2), openAmt * 2.5);
    space = AllpassC.ar(space, 0.3, openAmt.linlin(0, 1, 0.08, 0.25), openAmt * 2);

    sig = (sig * (1 - (openAmt * 0.4))) + (space * openAmt * 0.5);

    // Pitched wind tone
    sig = sig + BPF.ar(PinkNoise.ar(0.15), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.1), 350);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_oldwinch_chalk loaded".postln;
