// gotham_stairs/smile — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_smile, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var grin, teeth, strain, fake, crack;
    var exciter, formants, f1, f2, f3, strainMod, crackBurst;

    grin = p[0];
    teeth = p[1];
    strain = p[2];
    fake = p[3];
    crack = p[4];

    freq = In.kr(freqBus);

    // Strain modulation - tension tremolo
    strainMod = 1 + (strain * SinOsc.kr(strain.linlin(0, 1, 2, 12)).range(0, 0.2));

    // Vocal exciter - pulse wave with strain
    exciter = Pulse.ar(freq * strainMod, 0.3 + (strain * 0.2)) * 0.3;
    exciter = exciter + (PinkNoise.ar(0.1) * teeth);

    // Formant frequencies - grin widens the mouth shape
    // Base vowel "EE" (smile) shifting based on grin
    f1 = grin.linlin(0, 1, 300, 450) * (1 + (fake * LFNoise1.kr(3).range(0, 0.1)));
    f2 = grin.linlin(0, 1, 2200, 2800) * (1 + (fake * LFNoise1.kr(2.5).range(0, 0.1)));
    f3 = grin.linlin(0, 1, 2800, 3500) * (1 + (teeth * 0.3));

    // Formant filters with gain boost
    formants = Resonz.ar(exciter, f1, 0.1) * 5;
    formants = formants + (Resonz.ar(exciter, f2, 0.15) * 4 * grin);
    formants = formants + (Resonz.ar(exciter, f3, 0.2) * 3 * teeth);

    // Crack moments - sudden breaks in the facade
    crackBurst = Dust.ar(crack.linlin(0, 1, 0.5, 4));
    crackBurst = Ringz.ar(crackBurst, freq * [3, 5], 0.1).sum * crack * 0.4;

    sig = formants + crackBurst;

    // Fake happiness warble
    sig = sig * (1 + (fake * SinOsc.kr(fake.linlin(0, 1, 4, 10)).range(0, 0.15)));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_smile loaded".postln;
