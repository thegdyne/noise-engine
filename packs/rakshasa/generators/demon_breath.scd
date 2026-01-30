// rakshasa/demon_breath — Lightweight end-stage generator
// Demon Breath -- Low exhale with formant resonances and growl
// Role: bed | Family: texture

SynthDef(\forge_rakshasa_demon_breath, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var heat, foul, hiss, depth, growl;
    var breath, lowRumble, hissLayer, formants, growlMod;
    var formantFreqs, formantAmps;

    // Standard bus reads
    freq = In.kr(freqBus);

    // Custom parameters
    heat = p[0].linexp(0, 1, 200, 4000);  // Spectral center
    foul = p[1].linlin(0, 1, 1, 20);  // Distortion amount
    hiss = p[2].linlin(0, 1, 0, 0.4);  // HF noise mix
    depth = p[3].linlin(0, 1, 0, 0.6);  // Sub rumble mix
    growl = p[4].linexp(0, 1, 0.1, 15);  // Growl modulation rate

    // Growl modulation
    growlMod = LFNoise1.kr(growl).range(0.7, 1.3);

    // Low rumble from the depths
    lowRumble = LPF.ar(BrownNoise.ar, freq * 0.5 * growlMod) * depth;
    lowRumble = lowRumble + (SinOsc.ar(freq * 0.5 * growlMod) * depth * 0.3);

    // Main breath noise
    breath = PinkNoise.ar;

    // Formant resonances -- demon vocal tract
    formantFreqs = [heat * 0.8, heat * 1.2, heat * 2.5] * growlMod;
    formants = Mix.ar(
        formantFreqs.collect({ |f, i|
            BPF.ar(breath, f.clip(80, 12000), 0.15) * (1 / (i + 1))
        })
    );

    // Add distortion for foulness
    formants = (formants * foul).tanh / foul.sqrt;

    // High frequency hiss
    hissLayer = HPF.ar(WhiteNoise.ar, 3000) * hiss;
    hissLayer = hissLayer * LFNoise2.kr(growl * 0.5).range(0.5, 1);

    // Combine all elements
    sig = (formants * 0.5) + lowRumble + hissLayer;

    // Stereo with slight movement
    sig = Pan2.ar(sig, LFNoise2.kr(0.3).range(-0.3, 0.3));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_rakshasa_demon_breath loaded".postln;
