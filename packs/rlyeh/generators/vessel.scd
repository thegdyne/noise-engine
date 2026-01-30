// rlyeh/vessel — Lightweight end-stage generator
// vessel: The doomed ship - creaking hull facing the impossible
SynthDef(\forge_rlyeh_vessel, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var hull, creak, rock, sail, dread;

    hull = p[0].linlin(0, 1, 0.4, 1);  // P1: Hull resonance
    creak = p[1].linlin(0, 1, 2, 10);  // P2: Creak rate
    rock = p[2].linlin(0, 1, 0.1, 0.5);  // P3: Rocking motion
    sail = p[3].linlin(0, 1, 0.2, 0.7);  // P4: Sail flutter
    dread = p[4].linlin(0, 1, 0.2, 0.8);  // P5: Impending dread

    freq = In.kr(freqBus);

    // DSP: Hull resonance - wooden body (boosted gain)
    sig = Resonz.ar(PinkNoise.ar(hull), freq * [1, 1.5, 2.2], 0.2) * 12;
    sig = Splay.ar(sig, 0.4);

    // Creaking - continuous triggered hits
    sig = sig + (Ringz.ar(Dust.ar(creak) * 0.4, freq * [0.7, 1.5], 0.25) * 0.6);

    // Rocking motion - gentler
    sig = sig * SinOsc.kr(rock).range(0.7, 1);

    // Sail flutter - boosted
    sig = sig + (BPF.ar(PinkNoise.ar(sail), freq * 3, 0.4) * 0.5);

    // Dread undertone - always present, boosted
    sig = sig + (SinOsc.ar(freq * [0.25, 0.251]) * dread * 0.5);

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_vessel loaded".postln;
