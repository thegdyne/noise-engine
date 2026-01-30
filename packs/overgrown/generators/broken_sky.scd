// overgrown/broken_sky — Lightweight end-stage generator
SynthDef(\forge_overgrown_broken_sky, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var shatter, light, prism, dustAmt, hope;
    var beams, glass, sparkle, dustMotes, warmth;

    shatter = p[0];
    light = p[1];
    prism = p[2];
    dustAmt = p[3];
    hope = p[4];

    freq = In.kr(freqBus);

    // Light beams - pure sines
    beams = SinOsc.ar(freq) * light * 0.3;
    beams = beams + (SinOsc.ar(freq * 2) * light * 0.15);
    beams = beams + (SinOsc.ar(freq * 3) * light * 0.08);

    // Prism spread - detuned harmonics
    glass = SinOsc.ar(freq * (1 + (prism * 0.02))) * 0.2;
    glass = glass + (SinOsc.ar(freq * (2 - (prism * 0.03))) * 0.1);
    glass = glass + (SinOsc.ar(freq * (4 + (prism * 0.05))) * 0.06);
    glass = glass + (SinOsc.ar(freq * (5 - (prism * 0.04))) * 0.04);

    // Shatter - randomized high partials
    sparkle = SinOsc.ar(freq * 6 * LFNoise1.kr(shatter.linexp(0, 1, 0.2, 2)).range(0.95, 1.05)) * shatter * 0.08;
    sparkle = sparkle + (SinOsc.ar(freq * 8 * LFNoise1.kr(shatter.linexp(0, 1, 0.3, 3)).range(0.94, 1.06)) * shatter * 0.05);
    sparkle = sparkle + (SinOsc.ar(freq * 10 * LFNoise1.kr(shatter.linexp(0, 1, 0.4, 4)).range(0.93, 1.07)) * shatter * 0.03);

    // Dust motes - tiny grains in the light
    dustMotes = Dust.ar(dustAmt.linexp(0, 1, 5, 60)) * 0.05 * dustAmt;
    dustMotes = Ringz.ar(dustMotes, freq * [4, 5], 0.02);

    // Warmth/hope - soft low sine
    warmth = SinOsc.ar(freq * 0.5) * hope * 0.2;
    warmth = warmth + (SinOsc.ar(freq * LFNoise1.kr(0.1).range(0.99, 1.01)) * hope * 0.15);

    // Combine with stereo
    sig = beams + glass + sparkle + warmth;
    sig = [sig + dustMotes[0], sig + dustMotes[1]];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_broken_sky loaded".postln;
