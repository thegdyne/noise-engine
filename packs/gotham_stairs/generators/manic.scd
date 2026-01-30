// gotham_stairs/manic — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_manic, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var hysteria, laugh, twitch, spiral, breakPoint;
    var fbOsc, modOsc, modFreq, fbAmount, chaosLFO;

    hysteria = p[0];
    laugh = p[1];
    twitch = p[2];
    spiral = p[3];
    breakPoint = p[4];

    freq = In.kr(freqBus);

    // Spiral pitch drift - slow descent
    freq = freq * (1 - (spiral * LFSaw.kr(0.1).range(0, 0.3)));

    // Manic laughter modulation - irregular tremolo
    chaosLFO = LFNoise2.kr(laugh.linlin(0, 1, 2, 15)).range(0.5, 1);
    chaosLFO = chaosLFO * (1 + (LFPulse.kr(laugh.linlin(0, 1, 4, 20), 0, 0.3) * 0.3));

    // Feedback amount with breaking point chaos
    fbAmount = hysteria.linlin(0, 1, 0.2, pi);
    fbAmount = fbAmount * (1 + (breakPoint * LFNoise0.kr(8).range(0, 0.5)));

    // FM modulator with twitchy index
    modFreq = freq * (2 + (twitch * LFNoise1.kr(5).range(0, 1)));
    modOsc = SinOsc.ar(modFreq) * freq * twitch.linlin(0, 1, 1, 8);

    // Main feedback FM oscillator
    fbOsc = SinOscFB.ar(freq + modOsc, fbAmount);

    // Layer with slightly detuned chaotic copy
    sig = fbOsc + (SinOscFB.ar(freq * 1.003 + (modOsc * 0.7), fbAmount * 0.8) * 0.5);

    // Apply manic modulation
    sig = sig * chaosLFO;

    // Add noise burst on breaking point
    sig = sig + (WhiteNoise.ar(0.1) * breakPoint * LFNoise0.kr(12).range(0, 1));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_manic loaded".postln;
