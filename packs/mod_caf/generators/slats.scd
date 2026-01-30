// mod_caf/slats — Lightweight end-stage generator
// slats: Wood slat architecture resonance
SynthDef(\forge_mod_caf_slats, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var body, spacing, tap, warmth, room;

    body = p[0].linlin(0, 1, 0.4, 1);  // P1: Wood body resonance
    spacing = p[1].linlin(0, 1, 0.008, 0.04);  // P2: Slat spacing (comb)
    tap = p[2].linlin(0, 1, 2, 12);  // P3: Tap excitation rate
    warmth = p[3].linlin(0, 1, 600, 4000);  // P4: Warmth filter
    room = p[4].linlin(0, 1, 0.2, 0.6);  // P5: Room reflection

    freq = In.kr(freqBus);

    // DSP: Wood body - continuous filtered tone
    sig = LPF.ar(Saw.ar(freq * [0.5, 1, 1.002]) * body, warmth) * 0.4;
    sig = Splay.ar(sig, 0.5);

    // Continuous room noise bed
    sig = sig + (LPF.ar(PinkNoise.ar(room * 0.5), 800));

    // Comb resonance - slat spacing
    sig = sig + CombL.ar(sig * 0.4, 0.1, spacing, 0.8);

    // Tap excitation - wood knocks (boosted)
    sig = sig + (Ringz.ar(Dust.ar(tap) * 0.25, freq * [1, 2, 3.5], 0.1) * 0.5);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_slats loaded".postln;
