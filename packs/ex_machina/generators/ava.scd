// ex_machina/ava — Lightweight end-stage generator
// ava: AI consciousness - questioning, aware
SynthDef(\forge_ex_machina_ava, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var aware, question, soft, human, machine;

    aware = p[0].linlin(0, 1, 0.3, 1);  // P1: Awareness level
    question = p[1].linlin(0, 1, 0.05, 0.2);  // P2: Questioning inflection
    soft = p[2].linlin(0, 1, 500, 3000);  // P3: Softness filter
    human = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Human breath
    machine = p[4].linlin(0, 1, 0, 0.3);  // P5: Machine undertone

    freq = In.kr(freqBus);

    // DSP: Formant voice - soft, questioning
    sig = Formant.ar(
        freq * LFNoise1.kr(question).range(0.98, 1.02),
        freq * 3 * LFNoise1.kr(question * 0.5).range(0.9, 1.1),
        freq * 5
    ) * aware * 0.35;

    // Human breath texture
    sig = sig + (BPF.ar(PinkNoise.ar(human), freq * 3, 0.3) * LFNoise1.kr(0.2).range(0.5, 1) * 0.4);

    // Machine undertone - subtle digital
    sig = sig + (Pulse.ar(freq * [1, 1.001], 0.3) * machine * 0.15);

    // Softness filter
    sig = LPF.ar(sig, soft);

    // Continuous awareness hum
    sig = sig + (SinOsc.ar(freq * 0.5) * aware * 0.15);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_ava loaded".postln;
