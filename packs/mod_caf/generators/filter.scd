// mod_caf/filter — Lightweight end-stage generator
// filter: Resonant filter sweep - self-oscillation territory
SynthDef(\forge_mod_caf_filter, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var resonance, sweep, input, feedback, ping;
    var sweepMod, filterCut;

    resonance = p[0].linlin(0, 1, 0.5, 0.05);  // P1: Resonance (lower rq = more res)
    sweep = p[1].linlin(0, 1, 0.05, 2);  // P2: Sweep rate
    input = p[2].linlin(0, 1, 0.2, 0.8);  // P3: Input level
    feedback = p[3].linlin(0, 1, 0, 0.7);  // P4: Feedback
    ping = p[4].linlin(0, 1, 1, 10);  // P5: Ping rate

    freq = In.kr(freqBus);

    // DSP: Sweep modulation
    sweepMod = LFTri.kr(sweep).range(0.5, 2);
    filterCut = freq * 4 * sweepMod;

    // Input noise
    sig = PinkNoise.ar(input) + (Saw.ar(freq * [1, 1.003]) * input * 0.3);

    // Resonant filter
    sig = RLPF.ar(sig, filterCut.clip(20, 18000), resonance);

    // Filter ping - excite the resonance
    sig = sig + (Ringz.ar(Dust.ar(ping) * 0.2, filterCut.clip(100, 8000), resonance * 2) * 0.3);

    // Feedback saturation
    sig = (sig * (1 + feedback)).tanh;

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_filter loaded".postln;
