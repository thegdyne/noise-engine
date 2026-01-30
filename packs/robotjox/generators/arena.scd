// robotjox/arena — Lightweight end-stage generator
SynthDef(\forge_robotjox_arena, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var windAmt, crowd, dust, vast, tension;
    var windNoise, crowdRoar, dustStorm, space, tensionMod;

    windAmt = p[0];
    crowd = p[1];
    dust = p[2];
    vast = p[3];
    tension = p[4];

    freq = In.kr(freqBus);

    // Tension modulation - slow undulation
    tensionMod = LFNoise2.kr(0.2 + (tension * 0.5)).range(0.7, 1.0);

    // Wasteland wind
    windNoise = PinkNoise.ar(0.4) + BrownNoise.ar(0.3);
    windNoise = BPF.ar(windNoise, freq * LFNoise2.kr(0.3).range(0.5, 2), 0.5) * 2;
    windNoise = windNoise * LFNoise2.kr(0.4 + (windAmt * 0.5)).range(0.4, 1.0);
    windNoise = windNoise * (0.4 + (windAmt * 0.6));

    // Distant crowd roar
    crowdRoar = LPF.ar(BrownNoise.ar(0.5), 200 + (crowd * 300));
    crowdRoar = crowdRoar * LFNoise2.kr(0.3).range(0.5, 1.0);
    crowdRoar = crowdRoar * (0.3 + (crowd * 0.7));

    // Dust storm high frequencies
    dustStorm = HPF.ar(WhiteNoise.ar(0.25), 2000 + (dust * 3000));
    dustStorm = dustStorm * LFNoise2.kr(2 + (dust * 5)).range(0.3, 1.0);
    dustStorm = dustStorm * dust;

    sig = windNoise + crowdRoar + dustStorm;

    // Apply tension
    sig = sig * tensionMod;

    // Arena vastness - allpass reverb
    space = sig;
    space = AllpassC.ar(space, 0.3, vast.linlin(0, 1, 0.05, 0.2), vast * 3);
    space = AllpassC.ar(space, 0.3, vast.linlin(0, 1, 0.08, 0.25), vast * 2.5);
    space = AllpassC.ar(space, 0.3, vast.linlin(0, 1, 0.03, 0.15), vast * 2);

    sig = (sig * (1 - (vast * 0.4))) + (space * vast * 0.6);

    // Pitched wind resonance
    sig = sig + BPF.ar(PinkNoise.ar(0.2), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.12), 250);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_arena loaded".postln;
