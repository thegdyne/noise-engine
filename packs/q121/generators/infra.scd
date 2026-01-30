// q121/infra — Lightweight end-stage generator
SynthDef(\forge_q121_infra, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var pressure, cycle, sub, pulse, weight;
    var infraOsc, subOsc, pulseMod, amMod, chorusVoices;

    pressure = p[0];
    cycle = p[1];
    sub = p[2];
    pulse = p[3];
    weight = p[4];

    freq = In.kr(freqBus);

    // Infrasonic pressure cycle - AM tremolo
    pulseMod = SinOsc.kr(cycle.linexp(0, 1, 0.1, 2)).range(1 - (pulse * 0.6), 1);

    // AM depth modulation
    amMod = SinOsc.kr(cycle.linexp(0, 1, 0.05, 1) * 1.3).range(1 - (pressure * 0.4), 1);

    // Sub bass foundation
    subOsc = SinOsc.ar(freq * 0.5) * sub * 0.5;
    subOsc = subOsc + (SinOsc.ar(freq * 0.25) * sub * weight * 0.3);

    // Infrasonic oscillator bank with slight chorus detune
    chorusVoices = Mix.fill(5, { |i|
        var detune = LFNoise1.kr(0.2 + (i * 0.1)).range(0.995, 1.005);
        var voiceFreq = freq * detune;
        var voiceAmp = 0.2 - (i * 0.03);
        SinOsc.ar(voiceFreq) * voiceAmp
    });

    infraOsc = chorusVoices * amMod;

    // Low frequency rumble layer
    sig = infraOsc + subOsc;
    sig = sig + (LFNoise1.ar(freq * 0.1) * weight * 0.15);

    // Pressure modulation
    sig = sig * pulseMod;

    // Subtle harmonic content for presence
    sig = sig + (SinOsc.ar(freq * 2) * (1 - weight) * 0.1);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_infra loaded".postln;
