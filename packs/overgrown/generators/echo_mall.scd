// overgrown/echo_mall — Lightweight end-stage generator
SynthDef(\forge_overgrown_echo_mall, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var vast, decayTime, hollow, ghost, memory;
    var source, comb1, comb2, comb3, ghostTone, memoryEcho;

    vast = p[0];
    decayTime = p[1];
    hollow = p[2];
    ghost = p[3];
    memory = p[4];

    freq = In.kr(freqBus);

    // Source - soft pulse with some noise
    source = LFPulse.ar(freq, 0, 0.3 + (hollow * 0.2)) * 0.2;
    source = source + (PinkNoise.ar(0.05) * hollow);
    source = LPF.ar(source, freq * 4);

    // Comb filter delays for cavernous space
    comb1 = CombL.ar(source, 0.5, vast.linexp(0, 1, 0.05, 0.3), decayTime.linexp(0, 1, 0.5, 4));
    comb2 = CombL.ar(source, 0.5, vast.linexp(0, 1, 0.07, 0.35), decayTime.linexp(0, 1, 0.6, 4.5));
    comb3 = CombL.ar(source, 0.5, vast.linexp(0, 1, 0.11, 0.4), decayTime.linexp(0, 1, 0.4, 3.5));

    // Ghost tones - high pitched whispers
    ghostTone = SinOsc.ar(freq * 4 * LFNoise1.kr(0.2).range(0.98, 1.02)) * ghost * 0.08;
    ghostTone = ghostTone + (SinOsc.ar(freq * 6 * LFNoise1.kr(0.15).range(0.97, 1.03)) * ghost * 0.04);
    ghostTone = ghostTone * LFNoise1.kr(0.5).range(0.3, 1);

    // Memory echoes - delayed harmonics
    memoryEcho = SinOsc.ar(freq * 2) * memory * 0.1;
    memoryEcho = DelayL.ar(memoryEcho, 1.0, memory.linexp(0, 1, 0.2, 0.8));
    memoryEcho = memoryEcho + DelayL.ar(memoryEcho * 0.5, 1.0, memory.linexp(0, 1, 0.3, 0.6));

    // Combine with stereo spread
    sig = [comb1 + (comb3 * 0.5), comb2 + (comb3 * 0.5)];
    sig = sig + ghostTone + memoryEcho;

    // Hollow filtering
    sig = HPF.ar(sig, hollow.linexp(0, 1, 80, 300));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_echo_mall loaded".postln;
