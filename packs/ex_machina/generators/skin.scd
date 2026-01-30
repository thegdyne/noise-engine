// ex_machina/skin — Lightweight end-stage generator
// skin: Synthetic flesh - soft, uncanny
SynthDef(\forge_ex_machina_skin, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var texture, warmth, uncanny, membrane, touch;

    texture = p[0].linlin(0, 1, 0.3, 0.9);  // P1: Skin texture
    warmth = p[1].linlin(0, 1, 500, 2500);  // P2: Body warmth filter
    uncanny = p[2].linlin(0, 1, 0.1, 0.5);  // P3: Uncanny quality
    membrane = p[3].linlin(0, 1, 0.3, 0.8);  // P4: Membrane flex
    touch = p[4].linlin(0, 1, 2, 12);  // P5: Touch sensitivity

    freq = In.kr(freqBus);

    // DSP: Continuous body warmth tone (always present)
    sig = SinOsc.ar(freq * [0.5, 1]) * texture * 0.35;

    // Soft skin texture - filtered noise
    sig = sig + (LPF.ar(PinkNoise.ar(texture * 0.5), warmth));

    // Membrane flex - low resonance (boosted)
    sig = sig + (Ringz.ar(Dust.ar(touch) * 0.2, freq * [0.5, 1, 1.5], 0.25) * membrane * 0.5);

    // Uncanny quality - slight wrongness
    sig = sig + (SinOsc.ar(freq * LFNoise1.kr(0.05).range(0.98, 1.02) * [1, 1.003]) * uncanny * 0.25);

    // Touch response
    sig = sig + (LPF.ar(Dust2.ar(touch * 2) * 0.15, warmth));

    sig = LPF.ar(sig, warmth * 1.5) * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_skin loaded".postln;
