// mod_caf/voltage — Lightweight end-stage generator
// voltage: CV modulation textures - stepped random, chaos
SynthDef(\forge_mod_caf_voltage, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var stepRate, chaos, slew, depth, bipolar;
    var stepped, chaotic;

    stepRate = p[0].linlin(0, 1, 0.5, 15);  // P1: Step rate
    chaos = p[1].linlin(0, 1, 1.5, 1.99);  // P2: Chaos amount
    slew = p[2].linlin(0, 1, 0.001, 0.2);  // P3: Slew limiting
    depth = p[3].linlin(0, 1, 0.3, 1);  // P4: Modulation depth
    bipolar = p[4].linlin(0, 1, 0, 0.5);  // P5: Bipolar offset

    freq = In.kr(freqBus);

    // DSP: Stepped random - S&H style
    stepped = LFNoise0.kr(stepRate).lag(slew);

    // Chaotic - Lorenz-style via Crackle
    chaotic = Crackle.ar(chaos);

    // Modulated oscillator
    sig = SinOsc.ar(freq * (1 + (stepped * depth * 0.5))) * 0.3;
    sig = sig + (Pulse.ar(freq * (1 + (stepped * depth * 0.3)), 0.3 + (chaotic * 0.2)) * 0.2);

    // Chaos texture layer
    sig = sig + (BPF.ar(chaotic, freq * 2, 0.3) * depth * 0.3);

    // Bipolar offset adds asymmetry
    sig = sig + (SinOsc.ar(freq * 0.5) * bipolar * 0.2);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_voltage loaded".postln;
