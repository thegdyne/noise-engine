// nexus/nexus — Lightweight end-stage generator
SynthDef(\forge_nexus_nexus, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var op1, op2, op3, fbk, drf;
    var carrier, mod1, mod2, mod3, feedback;

    // Read custom params - 3-op cascade topology
    op1 = p[0];  // P1: First operator intensity (feeds OP2)
    op2 = p[1];  // P2: Second operator (modulates OP3, scaled by OP1)
    op3 = p[2];  // P3: Third operator output (feeds back to OP1)
    fbk = p[3];  // P4: Feedback amount OP3→OP1
    drf = p[4];  // P5: Drift in all operator ratios

    freq = In.kr(freqBus);

    // DSP: 3-operator cascade with feedback
    // OP1 → OP2 → OP3 with internal feedback

    // Ratio drift for each operator
    mod1 = 1 + (LFNoise1.kr(drf * 2 + 0.1) * drf * 0.1);
    mod2 = 2 + (LFNoise1.kr(drf * 1.7 + 0.1) * drf * 0.2);
    mod3 = 3 + (LFNoise1.kr(drf * 1.3 + 0.1) * drf * 0.3);

    // OP1: First modulator with self-feedback
    carrier = SinOscFB.ar(
        freq * mod1,
        fbk.linlin(0, 1, 0.1, 1.2) * op1
    ) * op1.linexp(0, 1, 0.3, 1);

    // OP2: Modulated by OP1, intensity scaled by op1*op2
    feedback = SinOsc.ar(
        freq * mod2,
        carrier * op1 * op2 * 4 * pi,
        op2.linexp(0, 1, 0.3, 1)
    );

    // OP3: Final carrier with feedback FM, modulated by OP2
    sig = SinOscFB.ar(
        freq * mod3 * [1, 1.003],
        fbk.linlin(0, 1, 0.05, 0.6) * op3
    ) * op3.linlin(0, 1, 0.3, 0.6);
    sig = sig * (1 + (feedback * op2 * 0.5));

    // Add fundamental for stability
    sig = sig + (SinOsc.ar(freq, carrier * op1 * pi * 0.5, 0.25));

    // Identity fracture: slight chorus
    sig = sig + (DelayC.ar(sig, 0.03, LFNoise1.kr(drf + 0.2).range(0.01, 0.025)) * drf * 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_nexus_nexus loaded".postln;
