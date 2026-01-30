// glacialis/cavebrth — Lightweight end-stage generator
// CAVEBRTH - Wind through ice tubes
// Breath-like noise with tube resonance and formants

SynthDef(\forge_glacialis_cavebrth, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var blow, tube, turbulence, voice, cave;
    var noise, breath, tubeRes, formants, caveRes, lfo;

    blow = p[0];  // Breath intensity
    tube = p[1];  // Tube resonance
    turbulence = p[2];  // Turbulence
    voice = p[3];  // Formant
    cave = p[4];  // Cave depth

    freq = In.kr(freqBus);

    // Slow modulation for natural breath
    lfo = SinOsc.kr(0.15 + (turbulence * 0.3)).range(0.7, 1);

    // Base breath noise
    noise = WhiteNoise.ar(1) + (PinkNoise.ar(1) * 0.5);
    noise = noise * blow * lfo;

    // Turbulence modulation
    noise = noise * (1 + (LFNoise2.ar(turbulence.linexp(0, 1, 1, 20)) * turbulence * 0.5));

    // Tube resonance (comb filter at pitch frequency)
    tubeRes = CombL.ar(noise, 0.1, freq.reciprocal, tube.linexp(0, 1, 0.05, 0.5));
    tubeRes = tubeRes + CombL.ar(noise, 0.1, (freq * 2).reciprocal, tube.linexp(0, 1, 0.03, 0.3)) * 0.5;
    breath = (noise * (1 - tube)) + (tubeRes * tube);

    // Vocal formants (oo/ah blend)
    formants = BPF.ar(noise, voice.linexp(0, 1, 300, 700), 0.1) * 3;
    formants = formants + (BPF.ar(noise, voice.linexp(0, 1, 800, 1200), 0.15) * 2);
    formants = formants + (BPF.ar(noise, voice.linexp(0, 1, 2300, 2800), 0.2));
    breath = breath + (formants * voice * 0.5);

    // Cave resonance - long reverberant delays
    caveRes = CombL.ar(breath, 0.3, 0.17, cave.linexp(0, 1, 0.3, 2));
    caveRes = caveRes + CombL.ar(breath, 0.3, 0.23, cave.linexp(0, 1, 0.25, 1.5)) * 0.7;
    sig = breath + (caveRes * cave * 0.4);

    // Stereo width
    sig = [
        sig + (DelayC.ar(sig, 0.05, 0.013) * cave * 0.3),
        sig + (DelayC.ar(sig, 0.05, 0.019) * cave * 0.3)
    ];

    // Remove DC offset from noise/comb content

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_cavebrth loaded".postln;
