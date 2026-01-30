// ex_machina/glass — Lightweight end-stage generator
// glass: Facility glass walls - cold, clinical
SynthDef(\forge_ex_machina_glass, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var pane, cold, touch, hum, sterile;

    pane = p[0].linlin(0, 1, 0.2, 0.8);  // P1: Glass pane resonance
    cold = p[1].linlin(0, 1, 3000, 10000);  // P2: Cold brightness
    touch = p[2].linlin(0, 1, 1, 8);  // P3: Touch/tap rate
    hum = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Facility hum
    sterile = p[4].linlin(0, 1, 0.1, 0.4);  // P5: Sterile air

    freq = In.kr(freqBus);

    // DSP: Glass resonance - high pitched ring
    sig = Ringz.ar(Dust.ar(touch) * 0.2, freq * [6, 8, 12], 0.3) * pane;
    sig = Splay.ar(sig, 0.6);

    // Cold brightness - continuous shimmer
    sig = sig + (BPF.ar(WhiteNoise.ar(pane * 0.25), cold, 0.1));

    // Facility hum - electrical
    sig = sig + (SinOsc.ar(60 * [1, 2, 3]) * hum * [0.3, 0.15, 0.08]).sum;

    // Sterile air - filtered noise
    sig = sig + (HPF.ar(PinkNoise.ar(sterile * 0.3), 2000));

    // Glass body tone
    sig = sig + (SinOsc.ar(freq * [1, 2.01]) * pane * 0.15);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_glass loaded".postln;
