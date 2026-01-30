// bed_stuy/stoop — Lightweight end-stage generator
// stoop: Brownstone steps, concrete resonance
SynthDef(\forge_bed_stuy_stoop, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var stone, weight, iron, settle, urban;

    stone = p[0].linlin(0, 1, 0.3, 1);  // P1: Stone resonance
    weight = p[1].linlin(0, 1, 0.2, 0.8);  // P2: Heavy presence
    iron = p[2].linlin(0, 1, 0, 0.5);  // P3: Iron railing
    settle = p[3].linlin(0, 1, 1, 6);  // P4: Settling creaks
    urban = p[4].linlin(0, 1, 0.1, 0.5);  // P5: City rumble

    freq = In.kr(freqBus);

    // DSP: Stone body - low filtered tone
    sig = LPF.ar(Pulse.ar(freq * [0.5, 0.501], 0.4) * stone, 600) * 0.4;

    // Heavy sub presence
    sig = sig + (SinOsc.ar(freq * 0.25) * weight * 0.4);

    // Iron railing - metallic ring
    sig = sig + (Ringz.ar(Dust.ar(settle) * 0.15, freq * [3, 4.5, 6], 0.1) * iron);

    // Urban rumble - distant traffic
    sig = sig + (LPF.ar(BrownNoise.ar(urban), 150) * 0.5);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_stoop loaded".postln;
