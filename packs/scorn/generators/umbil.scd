// scorn/umbil — Lightweight end-stage generator
// umbil: Umbilical cables - pulsing tubes
SynthDef(\forge_scorn_umbil, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var pulse, tube, flow, taut, connect;
    var pulseMod;

    pulse = p[0].linexp(0, 1, 0.5, 3);  // P1: Pulse rate
    tube = p[1].linlin(0, 1, 0.3, 0.9);  // P2: Tube resonance
    flow = p[2].linlin(0, 1, 0.2, 0.7);  // P3: Fluid flow
    taut = p[3].linlin(0, 1, 500, 3000);  // P4: Tautness
    connect = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Connection strength

    freq = In.kr(freqBus);

    // DSP: Pulsing rhythm
    pulseMod = LFPulse.kr(pulse, 0, 0.4).lag(0.05, 0.15);

    // Tube resonance - filtered with pulse
    sig = BPF.ar(PinkNoise.ar(tube * 0.5), taut * pulseMod.range(0.5, 1), 0.2);

    // Fluid flow through tube
    sig = sig + (LPF.ar(BrownNoise.ar(flow * 0.4), 600) * pulseMod.range(0.3, 1));

    // Connection tone - continuous
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * connect * 0.3);

    // Tube body hum
    sig = sig + (Saw.ar(freq * [1, 1.002]) * tube * 0.15);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_umbil loaded".postln;
