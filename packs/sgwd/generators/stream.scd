// sgwd/stream — Lightweight end-stage generator
// stream: Foreground water over rocks
SynthDef(\forge_sgwd_stream, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var flow, bubble, rocks, shallow, eddy;

    flow = p[0].linlin(0, 1, 0.3, 0.8);  // P1: Flow rate
    bubble = p[1].linlin(0, 1, 5, 30);  // P2: Bubble rate
    rocks = p[2].linlin(0, 1, 0.2, 0.6);  // P3: Over rocks
    shallow = p[3].linexp(0, 1, 500, 2000);  // P4: Shallow brightness
    eddy = p[4].linlin(0, 1, 0.5, 3);  // P5: Eddy rate

    freq = In.kr(freqBus);

    // DSP: Bubbling stream
    // Main flow
    sig = BPF.ar(PinkNoise.ar(flow), shallow, 0.5);
    sig = sig * LFNoise1.kr(eddy).range(0.7, 1);

    // Bubbling
    sig = sig + (Ringz.ar(Dust.ar(bubble) * 0.2, freq * [2, 3, 4, 5], 0.08).sum);

    // Over rocks - irregular splashes
    sig = sig + (BPF.ar(Crackle.ar(1.8, rocks * 0.3), 1500, 0.4));

    // Eddy swirls
    sig = sig + (BPF.ar(PinkNoise.ar(0.2), 800 * SinOsc.kr(eddy).range(0.7, 1.3), 0.3) * LFNoise1.kr(eddy).range(0.3, 1));

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_stream loaded".postln;
