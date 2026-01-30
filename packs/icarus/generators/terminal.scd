// icarus/terminal — Lightweight end-stage generator
// Terminal -- maximum velocity, blur of speed
// Role: motion

SynthDef(\forge_icarus_terminal, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var velocity, blur, mach, wake, doppler;
    var tone, chorusL, chorusR, noise, dopplerMod;

    freq = In.kr(freqBus);

    velocity = p[0].linlin(0, 1, 0.3, 1.0);  // Overall intensity
    blur = p[1].linlin(0, 1, 0.001, 0.02);  // Chorus depth (time)
    mach = p[2].linexp(0, 1, 1000, 12000);  // Edge filter freq
    wake = p[3].linlin(0, 1, 0.0, 0.5);  // Noise wake level
    doppler = p[4].linlin(0, 1, 0.0, 0.1);  // Pitch mod depth

    // Doppler frequency modulation
    dopplerMod = LFNoise2.kr(2, doppler, 1);

    // Core tone - sawtooth for harmonic richness
    tone = Saw.ar(freq * dopplerMod);

    // Motion blur - stereo chorus effect
    chorusL = DelayC.ar(tone, 0.05, SinOsc.kr(0.8, 0, blur, blur + 0.001));
    chorusR = DelayC.ar(tone, 0.05, SinOsc.kr(0.9, pi, blur, blur + 0.001));

    // Mach edge - resonant filter at the sound barrier
    chorusL = RLPF.ar(chorusL, mach, 0.3);
    chorusR = RLPF.ar(chorusR, mach, 0.3);

    // Turbulent wake - filtered noise trail
    noise = PinkNoise.ar(wake);
    noise = BPF.ar(noise, freq, 0.5);

    // Combine with velocity weight
    sig = [chorusL + (noise * 0.5), chorusR + (noise * 0.5)] * velocity;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_terminal loaded".postln;
