// icarus/wax_wings — Lightweight end-stage generator
// Wax Wings -- melting, failing, coming apart
// Role: foreground

SynthDef(\forge_icarus_wax_wings, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var melt, drip, feather, fail, shimmer;
    var tone, meltMod, drips, flutter, shine;

    freq = In.kr(freqBus);

    melt = p[0].linlin(0, 1, 0.0, 0.3);  // Pitch drop amount
    drip = p[1].linlin(0, 1, 1, 15);  // Drip rate
    feather = p[2].linlin(0, 1, 0.0, 0.5);  // Flutter level
    fail = p[3].linlin(0, 1, 0.0, 0.4);  // Instability
    shimmer = p[4].linlin(0, 1, 0.0, 3);  // FM index

    // Melting - slow pitch descent with wobble
    meltMod = LFNoise2.kr(0.3, melt, 1 - (melt * 0.5));

    // Core tone - sine with FM shimmer (light catching on wax)
    shine = SinOsc.ar(freq * meltMod * (1 + SinOsc.ar(freq * 2.01, 0, shimmer * 0.1)));

    // Feather flutter - fast tremolo texture
    flutter = SinOsc.ar(freq * 3 * meltMod, 0, feather);
    flutter = flutter * LFNoise2.ar(20 + (fail * 30));

    // Dripping wax - random impulses with pitch drop
    drips = Dust.ar(drip) * 0.5;
    drips = Ringz.ar(drips, freq * LFNoise0.kr(drip, 0.5, 1.5), 0.1);

    // Structural failure - random amplitude drops
    tone = shine + flutter + drips;
    tone = tone * (1 - (LFNoise2.kr(2 + (fail * 5)) * fail * 0.5));

    sig = tone;

    // Gentle stereo spread

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_wax_wings loaded".postln;
