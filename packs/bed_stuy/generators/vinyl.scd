// bed_stuy/vinyl — Lightweight end-stage generator
// vinyl: Record crackle and lo-fi warmth
SynthDef(\forge_bed_stuy_vinyl, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crackle, warmth, dust, hiss, worn;

    crackle = p[0].linlin(0, 1, 5, 50);  // P1: Crackle density
    warmth = p[1].linlin(0, 1, 0.3, 1);  // P2: Warm saturation
    dust = p[2].linlin(0, 1, 0, 0.4);  // P3: Dust pops
    hiss = p[3].linlin(0, 1, 0, 0.3);  // P4: Surface hiss
    worn = p[4].linlin(0, 1, 500, 3000);  // P5: Worn frequency

    freq = In.kr(freqBus);

    // DSP: Warm base tone - saturated
    sig = SinOsc.ar(freq * [1, 1.002]) * warmth;
    sig = (sig * 2).tanh * 0.5;  // Soft saturation

    // Crackle texture
    sig = sig + (HPF.ar(Dust2.ar(crackle) * 0.15, 800));

    // Dust pops - occasional loud clicks
    sig = sig + (Ringz.ar(Dust.ar(dust * 3) * 0.2, 1500, 0.01));

    // Surface hiss
    sig = sig + (BPF.ar(WhiteNoise.ar(hiss), worn, 0.5) * 0.5);

    // Lo-fi filter
    sig = LPF.ar(sig, worn);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_vinyl loaded".postln;
