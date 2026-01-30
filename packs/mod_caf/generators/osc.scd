// mod_caf/osc — Lightweight end-stage generator
// osc: Classic analog oscillator with drift
SynthDef(\forge_mod_caf_osc, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var drift, shape, thick, warmth, sub;
    var driftMod;

    drift = p[0].linlin(0, 1, 0.001, 0.02);  // P1: Pitch drift
    shape = p[1].linlin(0, 1, 0.1, 0.9);  // P2: Pulse width
    thick = p[2].linlin(0, 1, 0, 0.015);  // P3: Detuning
    warmth = p[3].linlin(0, 1, 1, 3);  // P4: Saturation
    sub = p[4].linlin(0, 1, 0, 0.5);  // P5: Sub oscillator

    freq = In.kr(freqBus);

    // DSP: Analog drift
    driftMod = LFNoise1.kr(0.3).range(1 - drift, 1 + drift);

    // Main oscillators with drift and thickness
    sig = Saw.ar(freq * driftMod * [1, 1 + thick]) * 0.3;
    sig = sig + (Pulse.ar(freq * driftMod * [1.001, 1 - thick], shape) * 0.25);

    // Warmth saturation
    sig = (sig * warmth).tanh;

    // Sub oscillator
    sig = sig + (SinOsc.ar(freq * 0.5 * driftMod) * sub * 0.4);

    sig = Splay.ar(sig, 0.6) * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_osc loaded".postln;
