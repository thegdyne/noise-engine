// scorn/throb — Lightweight end-stage generator
// throb: Biological pulse - deep rhythm
SynthDef(\forge_scorn_throb, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rate, deep, organ, pressure, alive;
    var throbMod;

    rate = p[0].linexp(0, 1, 0.5, 2.5);  // P1: Throb rate
    deep = p[1].linlin(0, 1, 0.3, 1);  // P2: Deep sub
    organ = p[2].linlin(0, 1, 0.2, 0.7);  // P3: Organ resonance
    pressure = p[3].linlin(0, 1, 0.1, 0.6);  // P4: Blood pressure
    alive = p[4].linlin(0, 1, 0.2, 0.7);  // P5: Alive feeling

    freq = In.kr(freqBus);

    // DSP: Throb modulation
    throbMod = LFPulse.kr(rate, 0, 0.35).lag(0.03, 0.2);

    // Deep sub pulse
    sig = SinOsc.ar(freq * 0.5) * deep * throbMod * 0.5;

    // Organ resonance - body cavity
    sig = sig + (BPF.ar(PinkNoise.ar(organ * 0.4), freq * [1, 2], 0.3) * throbMod.range(0.4, 1));

    // Blood pressure - rushing sound
    sig = sig + (LPF.ar(BrownNoise.ar(pressure * 0.4), 400 * throbMod.range(0.5, 1.5)));

    // Alive continuous presence
    sig = sig + (Saw.ar(freq * [1, 1.003]) * alive * 0.2);

    // Body warmth
    sig = sig + (SinOsc.ar(freq) * alive * 0.15);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_throb loaded".postln;
