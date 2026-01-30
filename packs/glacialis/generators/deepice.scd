// glacialis/deepice — Lightweight end-stage generator
// DEEPICE - Sub-harmonic frozen mass
// Glacial drone with ice stress crackles

SynthDef(\forge_glacialis_deepice, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, flow, crack, depth, vast;
    var sub, fund, noise, lfo, crackle;

    mass = p[0];  // Sub vs fundamental
    flow = p[1];  // Movement rate
    crack = p[2];  // Ice stress noise
    depth = p[3];  // Resonant depth
    vast = p[4];  // Stereo width

    freq = In.kr(freqBus);

    // Glacial LFO for movement
    lfo = SinOsc.kr(flow.linexp(0, 1, 0.01, 0.2));

    // Sub-harmonic (one octave down)
    sub = SinOsc.ar(freq * 0.5) + (SinOsc.ar(freq * 0.25) * 0.5);
    sub = sub * mass;

    // Fundamental with slow PWM
    fund = Pulse.ar(freq, lfo.range(0.3, 0.7)) * 0.7;
    fund = fund + (Saw.ar(freq * 1.002) * 0.3);
    fund = fund * (1 - (mass * 0.5));

    // Ice stress crackles
    crackle = Dust.ar(crack.linexp(0, 1, 0.5, 30));
    crackle = Ringz.ar(crackle, freq * [2, 3.17, 5.43], 0.1).sum * 0.3;
    crackle = crackle * crack;

    // Combine
    sig = sub + fund + crackle;

    // Resonant filtering for depth
    sig = sig + (BPF.ar(sig, freq * 2, 0.1) * depth * 2);

    // Stereo spread
    sig = sig + (DelayC.ar(sig, 0.05, vast.linlin(0, 1, 0.001, 0.03)) * vast * 0.5);
    sig = [sig, DelayC.ar(sig, 0.05, vast.linlin(0, 1, 0.002, 0.04))];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_deepice loaded".postln;
