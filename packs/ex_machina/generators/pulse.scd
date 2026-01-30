// ex_machina/pulse — Lightweight end-stage generator
// pulse: Power source - rhythmic energy core
SynthDef(\forge_ex_machina_pulse, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rate, power, surge, glow, stable;
    var pulseMod;

    rate = p[0].linexp(0, 1, 0.5, 4);  // P1: Pulse rate
    power = p[1].linlin(0, 1, 0.3, 1);  // P2: Power level
    surge = p[2].linlin(0, 1, 0, 0.5);  // P3: Power surge
    glow = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Amber glow
    stable = p[4].linlin(0, 1, 0.95, 1);  // P5: Stability

    freq = In.kr(freqBus);

    // DSP: Pulse modulation
    pulseMod = LFPulse.kr(rate, 0, 0.3).lag(0.02, 0.1);

    // Power core - pulsing sub
    sig = SinOsc.ar(freq * 0.5 * LFNoise1.kr(0.1).range(stable, 1.01)) * power * 0.5;
    sig = sig * (0.5 + (pulseMod * 0.5));

    // Electrical hum
    sig = sig + (Saw.ar(freq * [1, 1.002]) * power * 0.2);

    // Surge events
    sig = sig + (Ringz.ar(Dust.ar(surge * 5) * 0.25, freq * [2, 4], 0.1) * surge);

    // Amber glow - warm continuous
    sig = sig + (SinOsc.ar(freq * [1, 2]) * glow * 0.2);

    // Stability noise
    sig = sig + (LPF.ar(PinkNoise.ar((1 - stable) * 0.3), 500));

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_pulse loaded".postln;
