// vapor_station/hose — Lightweight end-stage generator
// hose: Resonant rubber fuel hose
SynthDef(\forge_vapor_station_hose, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tension, length, excite, rubber, flow;
    var delTime, exciter;

    tension = p[0].linlin(0, 1, 0.9, 0.99);  // P1: Tube tension (feedback)
    length = p[1].linlin(0, 1, 0.5, 2);  // P2: Tube length multiplier
    excite = p[2].linlin(0, 1, 3, 20);  // P3: Excitation rate (boosted)
    rubber = p[3].linlin(0, 1, 800, 4000);  // P4: Rubber damping freq
    flow = p[4].linlin(0, 1, 0.2, 0.7);  // P5: Flow through tube

    freq = In.kr(freqBus);

    // DSP: Karplus-Strong style waveguide
    delTime = (1 / freq) * length;
    exciter = Dust.ar(excite) * 0.8;

    // Comb resonator for tube - boosted feedback time
    sig = CombL.ar(exciter, 0.1, delTime.clip(0.001, 0.1), tension * 3);
    sig = LPF.ar(sig, rubber);

    // Flow noise through tube - boosted
    sig = sig + (BPF.ar(PinkNoise.ar(flow), freq * [1.5, 2.5], 0.4) * 0.8);

    // Continuous tonal anchor
    sig = sig + (SinOsc.ar(freq * [0.5, 0.501]) * 0.15);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_hose loaded".postln;
