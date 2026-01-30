// ex_machina/chrome — Lightweight end-stage generator
// chrome: Metallic skull mask - reflective, cold beauty
SynthDef(\forge_ex_machina_chrome, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var shine, cold, reflect, skull, amber;

    shine = p[0].linlin(0, 1, 0.3, 1);  // P1: Chrome shine
    cold = p[1].linlin(0, 1, 2000, 8000);  // P2: Cold brightness
    reflect = p[2].linlin(0, 1, 3, 15);  // P3: Reflection rate
    skull = p[3].linlin(0, 1, 0.2, 0.7);  // P4: Skull resonance
    amber = p[4].linlin(0, 1, 0, 0.4);  // P5: Amber glow warmth

    freq = In.kr(freqBus);

    // DSP: Chrome shimmer - high metallic harmonics
    sig = Ringz.ar(Dust.ar(reflect) * 0.2, freq * [8, 10, 12, 15], 0.08) * shine;
    sig = Splay.ar(sig, 0.7);

    // Skull resonance - hollow metallic body
    sig = sig + (BPF.ar(PinkNoise.ar(skull * 0.4), freq * 2, 0.2));
    sig = sig + (Ringz.ar(Dust.ar(reflect * 0.5) * 0.15, freq * [1.5, 2.5], 0.15) * skull);

    // Cold brightness filter
    sig = HPF.ar(sig, 200) + (sig * 0.3);

    // Amber glow - warm undertone
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * amber * 0.25);

    // Continuous metallic bed
    sig = sig + (BPF.ar(WhiteNoise.ar(shine * 0.2), cold, 0.15));

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_chrome loaded".postln;
