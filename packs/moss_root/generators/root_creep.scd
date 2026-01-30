// moss_root/root_creep — Lightweight end-stage generator
SynthDef(\forge_moss_root_root_creep, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var twist, reach, tangle, earth, sky;
    var voices, earthSub, skyHarm, panMod;

    freq = In.kr(freqBus);

    twist = p[0];
    reach = p[1];
    tangle = p[2];
    earth = p[3];
    sky = p[4];

    // Multiple tangled voices with independent slow modulation
    voices = Mix(Array.fill(4, { |i|
        var rate = twist.linexp(0, 1, 0.02, 0.3) * (1 + (i * 0.15));
        var pitchMod = LFNoise1.kr(rate) * reach.linlin(0, 1, 0.01, 0.08);
        var ampMod = LFNoise1.kr(rate * 0.7).range(0.3, 1);
        var voiceFreq = freq * (1 + pitchMod) * [1, 1.002, 0.998, 1.005][i];

        // Mix of saw and triangle for organic character
        var voice = (Saw.ar(voiceFreq) * 0.6) + (LFTri.ar(voiceFreq) * 0.4);
        voice * ampMod * (tangle.linlin(0, 1, 0.3, 1) / 4)
    }));

    // Earth: sub oscillator rooted deep
    earthSub = SinOsc.ar(freq * 0.5) * earth * 0.4;
    earthSub = earthSub + (LFTri.ar(freq * 0.25) * earth * 0.2);

    // Sky: upper harmonics reaching up
    skyHarm = Mix([
        SinOsc.ar(freq * 2, LFNoise1.kr(twist.linexp(0, 1, 0.1, 0.5)) * sky),
        SinOsc.ar(freq * 3) * 0.5,
        SinOsc.ar(freq * 4) * 0.3
    ]) * sky * 0.15;
    // Sky has its own slow tremolo
    skyHarm = skyHarm * LFTri.kr(twist.linexp(0, 1, 0.5, 2)).range(0.6, 1);

    sig = voices + earthSub + skyHarm;

    // Slow stereo movement - roots spreading
    panMod = LFNoise1.kr(twist.linexp(0, 1, 0.05, 0.2));
    sig = Pan2.ar(sig, panMod * tangle * 0.7);

    // MANDATORY output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_root_creep loaded".postln;
