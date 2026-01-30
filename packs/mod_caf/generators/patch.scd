// mod_caf/patch — Lightweight end-stage generator
// patch: Patch cable connections and contact noise
SynthDef(\forge_mod_caf_patch, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crackle, hum, insert, oxidation, ground;

    crackle = p[0].linlin(0, 1, 10, 50);  // P1: Contact crackle rate (boosted)
    hum = p[1].linlin(0, 1, 0.2, 0.6);  // P2: Ground hum (boosted)
    insert = p[2].linlin(0, 1, 1, 6);  // P3: Jack insert rate
    oxidation = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Dirty contact
    ground = p[4].linlin(0, 1, 50, 62);  // P5: Ground frequency

    freq = In.kr(freqBus);

    // DSP: Continuous cable capacitance hiss (always present)
    sig = LPF.ar(PinkNoise.ar(0.35), 2500);

    // Ground hum - continuous 50/60Hz
    sig = sig + (SinOsc.ar(ground * [1, 2, 3]) * hum * [0.4, 0.2, 0.1]).sum;

    // Contact crackle - high frequency pops (boosted rate)
    sig = sig + (HPF.ar(Dust2.ar(crackle) * 0.35, 800));

    // Jack insert clicks - low thunks
    sig = sig + (Ringz.ar(Dust.ar(insert) * 0.3, 150, 0.03));

    // Oxidation noise - dirty contact texture (continuous Crackle)
    sig = sig + (Crackle.ar(1.5 + (oxidation * 0.4)) * oxidation * 0.25);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_patch loaded".postln;
