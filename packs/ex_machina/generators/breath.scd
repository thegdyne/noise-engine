// ex_machina/breath — Lightweight end-stage generator
// breath: Human warmth - organic, living
SynthDef(\forge_ex_machina_breath, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var inhale, warmth, life, pulse, soft;
    var breathCycle;

    inhale = p[0].linlin(0, 1, 0.1, 0.3);  // P1: Breath rate
    warmth = p[1].linlin(0, 1, 0.3, 1);  // P2: Body warmth
    life = p[2].linlin(0, 1, 0.1, 0.5);  // P3: Life signs
    pulse = p[3].linlin(0, 1, 0.8, 1.5);  // P4: Heart pulse rate
    soft = p[4].linlin(0, 1, 400, 2000);  // P5: Softness filter

    freq = In.kr(freqBus);

    // DSP: Breath cycle - slow modulated noise
    breathCycle = SinOsc.kr(inhale).range(0.3, 1);
    sig = BPF.ar(PinkNoise.ar(warmth * 0.5), freq * 2, 0.4) * breathCycle;

    // Body warmth - low filtered tone
    sig = sig + (LPF.ar(Saw.ar(freq * [0.5, 0.501]) * warmth, soft) * 0.25);

    // Life signs - subtle variations
    sig = sig + (SinOsc.ar(freq * LFNoise1.kr(0.1).range(0.99, 1.01)) * life * 0.2);

    // Heart pulse - sub rhythm
    sig = sig + (SinOsc.ar(freq * 0.25) * LFPulse.kr(pulse, 0, 0.1).lag(0.05, 0.2) * 0.2);

    // Continuous warmth
    sig = sig + (SinOsc.ar(freq * 0.5) * warmth * 0.15);

    sig = LPF.ar(sig, soft) * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_breath loaded".postln;
