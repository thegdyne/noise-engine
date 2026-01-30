// overgrown/rust_wind — Lightweight end-stage generator
SynthDef(\forge_overgrown_rust_wind, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var gust, corrosion, howl, rattle, lonely;
    var wind, resonance, rattleSound, howlTone, lonelyTone, gustMod;

    gust = p[0];
    corrosion = p[1];
    howl = p[2];
    rattle = p[3];
    lonely = p[4];

    freq = In.kr(freqBus);

    // Gust modulation - slow wind movement
    gustMod = LFNoise1.kr(gust.linexp(0, 1, 0.1, 1)).range(0.3, 1);

    // Base wind noise
    wind = PinkNoise.ar(0.3) * gustMod;
    wind = BPF.ar(wind, freq * 2 * LFNoise1.kr(0.3).range(0.8, 1.2), 0.5) * 2;
    wind = wind + (BrownNoise.ar(0.15) * gustMod);

    // Corrosion texture - grainy high frequencies
    resonance = BPF.ar(WhiteNoise.ar(0.2), freq * 4 * LFNoise1.kr(0.2).range(0.9, 1.1), 0.2) * corrosion * 3;
    resonance = resonance + (BPF.ar(WhiteNoise.ar(0.1), freq * 6, 0.15) * corrosion * 2);

    // Howling - resonant pitched wind
    howlTone = Resonz.ar(wind, freq * LFNoise1.kr(0.15).range(0.95, 1.05), howl.linexp(0, 1, 0.5, 0.1)) * howl * 4;
    howlTone = howlTone + (Resonz.ar(wind, freq * 2 * LFNoise1.kr(0.1).range(0.96, 1.04), howl.linexp(0, 1, 0.4, 0.08)) * howl * 2);

    // Rattle - triggered metallic hits
    rattleSound = Ringz.ar(Dust.ar(rattle.linexp(0, 1, 1, 15)) * 0.1, freq * [3, 5], 0.05) * rattle * 2;

    // Lonely desolate tone
    lonelyTone = SinOsc.ar(freq * 0.5 * LFNoise1.kr(0.05).range(0.98, 1.02)) * lonely * 0.15;
    lonelyTone = lonelyTone + (SinOsc.ar(freq * LFNoise1.kr(0.08).range(0.99, 1.01)) * lonely * 0.1);
    lonelyTone = lonelyTone * LFNoise1.kr(0.2).range(0.5, 1);

    // Combine with stereo
    sig = wind + resonance + howlTone + lonelyTone;
    sig = [sig + rattleSound[0], sig + rattleSound[1]];

    // Stereo wind movement
    sig = Balance2.ar(sig[0], sig[1], LFNoise1.kr(gust.linexp(0, 1, 0.1, 0.5)).range(-0.5, 0.5));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_rust_wind loaded".postln;
