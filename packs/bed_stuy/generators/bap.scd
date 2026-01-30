// bed_stuy/bap — Lightweight end-stage generator
// bap: Snare/clap texture - crisp hits
SynthDef(\forge_bed_stuy_bap, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var snap, body, wire, room, tight;

    snap = p[0].linlin(0, 1, 0.2, 0.8);  // P1: Snap transient
    body = p[1].linlin(0, 1, 0.2, 0.7);  // P2: Body tone
    wire = p[2].linlin(0, 1, 0.1, 0.6);  // P3: Snare wire
    room = p[3].linlin(0, 1, 0.2, 0.6);  // P4: Room ambience
    tight = p[4].linlin(0, 1, 0.02, 0.15);  // P5: Decay tightness

    freq = In.kr(freqBus);

    // DSP: Continuous room noise bed (always present)
    sig = LPF.ar(PinkNoise.ar(room * 0.5), 1000);

    // Snap transient - noise burst (boosted rate)
    sig = sig + (HPF.ar(Dust2.ar(8) * snap * 0.4, 800).lag(0.001, tight));

    // Body tone - tuned resonance
    sig = sig + (Ringz.ar(Dust.ar(8) * body, freq * [1, 1.5], tight * 2) * 0.5);

    // Snare wire - continuous filtered noise
    sig = sig + (BPF.ar(WhiteNoise.ar(wire * 0.4), 4000, 0.4));

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_bap loaded".postln;
