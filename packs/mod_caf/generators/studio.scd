// mod_caf/studio — Lightweight end-stage generator
// studio: Room tone and quiet studio ambience
SynthDef(\forge_mod_caf_studio, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var room, hvac, gear, quiet, presence;

    room = p[0].linlin(0, 1, 0.2, 0.7);  // P1: Room tone
    hvac = p[1].linlin(0, 1, 0, 0.4);  // P2: HVAC hum
    gear = p[2].linlin(0, 1, 0, 0.3);  // P3: Gear noise
    quiet = p[3].linlin(0, 1, 200, 1500);  // P4: Quiet filter
    presence = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Human presence

    freq = In.kr(freqBus);

    // DSP: Room tone - continuous filtered noise
    sig = LPF.ar(PinkNoise.ar(room), quiet) * 0.5;

    // HVAC - low drone
    sig = sig + (LPF.ar(BrownNoise.ar(hvac), 150) * 0.5);

    // Gear noise - high frequency hiss
    sig = sig + (HPF.ar(WhiteNoise.ar(gear * 0.3), 4000));

    // Human presence - occasional subtle movement
    sig = sig + (BPF.ar(PinkNoise.ar(presence), 400 * LFNoise1.kr(0.1).range(0.8, 1.2), 0.3) * LFNoise1.kr(0.2).range(0.3, 1) * 0.3);

    // Sub presence - room resonance
    sig = sig + (SinOsc.ar(freq * 0.25) * room * 0.15);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_studio loaded".postln;
