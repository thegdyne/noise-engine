// overgrown/giraffe_hum — Lightweight end-stage generator
SynthDef(\forge_overgrown_giraffe_hum, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var breath, throat, call, gentle, wonder;
    var source, formant1, formant2, formant3, breathNoise, vibrato, shimmer;

    breath = p[0];
    throat = p[1];
    call = p[2];
    gentle = p[3];
    wonder = p[4];

    freq = In.kr(freqBus);

    // Gentle vibrato for organic feel
    vibrato = SinOsc.kr(call.linexp(0, 1, 3, 7)).range(0.995, 1.005);

    // Source oscillator - soft saw with gentle character
    source = LFSaw.ar(freq * vibrato) * (1 - (gentle * 0.5));
    source = source + (SinOsc.ar(freq * vibrato) * gentle * 0.8);
    source = source * 0.5;

    // Formant filters - vocal throat character
    formant1 = BPF.ar(source, throat.linexp(0, 1, 300, 800), 0.15) * 4;
    formant2 = BPF.ar(source, throat.linexp(0, 1, 800, 2000), 0.12) * 3;
    formant3 = BPF.ar(source, throat.linexp(0, 1, 2000, 3500), 0.1) * 2;

    // Breath noise layer
    breathNoise = BPF.ar(PinkNoise.ar, throat.linexp(0, 1, 400, 1200), 0.4) * breath * 0.3;
    breathNoise = breathNoise * LFNoise1.kr(2).range(0.5, 1);

    // Wonder shimmer - high harmonics
    shimmer = SinOsc.ar(freq * [5.01, 4.99] * vibrato) * wonder * 0.08;
    shimmer = shimmer + (SinOsc.ar(freq * [7.02, 6.98] * vibrato) * wonder * 0.04);

    // Combine with stereo spread
    sig = [formant1 + formant2 + (formant3 * 0.5), formant1 + formant2 + (formant3 * 0.5)];
    sig = sig + breathNoise + shimmer;

    // Soft movement
    sig = Balance2.ar(sig[0], sig[1], SinOsc.kr(0.15).range(-0.3, 0.3));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_giraffe_hum loaded".postln;
