// ex_machina/servo — Lightweight end-stage generator
// servo: Mechanical eyes - precise servo movements
SynthDef(\forge_ex_machina_servo, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var motor, precision, focus, track, idle;

    motor = p[0].linlin(0, 1, 0.3, 0.9);  // P1: Motor whir
    precision = p[1].linlin(0, 1, 8, 35);  // P2: Movement precision
    focus = p[2].linlin(0, 1, 0.2, 0.6);  // P3: Focus clicks
    track = p[3].linlin(0, 1, 0.5, 3);  // P4: Tracking rate
    idle = p[4].linlin(0, 1, 0.2, 0.6);  // P5: Idle hum

    freq = In.kr(freqBus);

    // DSP: Continuous idle hum (always present)
    sig = SinOsc.ar(freq * [0.5, 1]) * idle * 0.35;

    // Motor whir - continuous high frequency
    sig = sig + (BPF.ar(WhiteNoise.ar(motor * 0.5), 3000 * LFNoise1.kr(track).range(0.8, 1.2), 0.2));

    // Precision clicks - stepped movements (boosted)
    sig = sig + (Ringz.ar(Dust.ar(precision) * 0.25, freq * [4, 6, 8], 0.03) * 0.6);

    // Focus mechanism
    sig = sig + (Ringz.ar(Dust.ar(focus * 5) * 0.2, freq * 2, 0.1) * focus);

    // Tracking servo - modulated noise
    sig = sig + (BPF.ar(PinkNoise.ar(motor * 0.4), 1500 * LFNoise0.kr(track).range(0.5, 2), 0.25));

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_servo loaded".postln;
