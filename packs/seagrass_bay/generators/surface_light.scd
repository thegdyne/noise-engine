// seagrass_bay/surface_light — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_surface_light, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var ripple, sun, dance, sparkle, wave;
    var carrier, modulator, rippleMod, dancePattern, sparkleGlints, amDepth;

    // Standard bus reads
    freq = In.kr(freqBus);

    ripple = p[0];  // Surface wave rate
    sun = p[1];  // Brightness
    dance = p[2];  // Light pattern
    sparkle = p[3];  // Glints
    wave = p[4];  // Mod depth

    // Ripple modulation rate
    rippleMod = ripple.linexp(0, 1, 2, 15);

    // AM modulator - multiple ripple frequencies for complex pattern
    modulator = SinOsc.ar(rippleMod) * 0.4;
    modulator = modulator + (SinOsc.ar(rippleMod * 1.618) * 0.3);  // Golden ratio
    modulator = modulator + (SinOsc.ar(rippleMod * 0.618) * 0.3);  // Inverse golden

    // Dance pattern - irregular brightness shifts
    dancePattern = LFNoise1.kr(dance.linexp(0, 1, 0.5, 3)).range(0.7, 1);

    // Carrier - bright harmonics for sun quality
    carrier = Pulse.ar(freq, 0.3) * 0.4;
    carrier = carrier + (Pulse.ar(freq * 2.01, 0.4) * 0.25 * sun);
    carrier = carrier + (SinOsc.ar(freq * 3) * 0.15 * sun);

    // AM depth controlled by wave
    amDepth = wave.linlin(0, 1, 0.1, 0.6);
    sig = carrier * (1 + (modulator * amDepth));

    // Apply dance pattern
    sig = sig * dancePattern;

    // Sparkle - high frequency glints
    sparkleGlints = Ringz.ar(
        Dust.ar(sparkle.linexp(0, 1, 5, 40)),
        freq * [3, 4, 5, 6],
        0.05
    ).sum * sparkle * 0.2;
    sig = sig + sparkleGlints;

    // Sun = overall brightness
    sig = sig * sun.linlin(0, 1, 0.5, 1.2);

    // Wide stereo for shimmering effect
    sig = ~stereoSpread.(sig, rippleMod * 0.1, 0.6);

    // Standard output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_surface_light loaded".postln;
