// seagrass_bay/gentle_giant — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_gentle_giant, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, grace, skin, breath, swim;
    var mainOsc, subOsc, breathMod, swimMod, skinNoise;

    // Standard bus reads
    freq = In.kr(freqBus);

    mass = p[0];  // Size/weight
    grace = p[1];  // Smoothness
    skin = p[2];  // Texture
    breath = p[3];  // Breathing mod
    swim = p[4];  // Motion quality

    // Breathing modulation - slow amplitude swell
    breathMod = SinOsc.kr(breath.linexp(0, 1, 0.08, 0.3)).range(1 - (breath * 0.15), 1);

    // Swim modulation - gentle pitch drift
    swimMod = LFTri.kr(swim.linexp(0, 1, 0.05, 0.25)) * swim * 0.008;
    freq = freq * (1 + swimMod);

    // Main oscillator - triangle for smoothness, saw for body
    mainOsc = (VarSaw.ar(freq, 0, grace.linlin(0, 1, 0.5, 0.1)) * 0.6) +
              (LFTri.ar(freq) * grace * 0.4);

    // Sub oscillator for mass
    subOsc = SinOsc.ar(freq * 0.5) * mass * 0.5;

    // Octave up for presence
    sig = mainOsc + subOsc + (LFTri.ar(freq * 2) * (1 - mass) * 0.15);

    // Skin texture - subtle noise
    skinNoise = LPF.ar(PinkNoise.ar, freq * 3) * skin * 0.08;
    sig = sig + skinNoise;

    // Apply breathing
    sig = sig * breathMod;

    // Grace = smoothing/filtering
    sig = LPF.ar(sig, grace.linexp(0, 1, 3000, 12000));

    // Warm stereo spread

    // Standard output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_gentle_giant loaded".postln;
