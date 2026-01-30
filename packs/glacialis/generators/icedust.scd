// glacialis/icedust — Lightweight end-stage generator
// ICEDUST - Frozen particle cloud
// Granular texture from triggered resonant grains

SynthDef(\forge_glacialis_icedust, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var flake, size, fall, glint, swirl;
    var grains, dust, grainFreq, grainDur, shimmer, lfo;

    flake = p[0];  // Density
    size = p[1];  // Grain size
    fall = p[2];  // Pitch scatter
    glint = p[3];  // Brightness
    swirl = p[4];  // Movement

    freq = In.kr(freqBus);

    // Swirl modulation
    lfo = SinOsc.kr(swirl.linexp(0, 1, 0.1, 2));

    // Grain parameters
    grainDur = size.linexp(0, 1, 0.005, 0.1);

    // Multiple grain streams at different densities
    grains = Mix.fill(4, { |i|
        var trig, grainPitch, env, grain;
        trig = Dust.ar(flake.linexp(0, 1, 5, 80) * (1 + (i * 0.3)));

        // Pitch scatter around base frequency
        grainPitch = freq * TRand.ar(
            1 - (fall * 0.5),
            1 + (fall * (1 + (glint * 2))),
            trig
        );
        grainPitch = grainPitch * (1 + (i * fall * 0.3));

        // Grain envelope
        env = Decay2.ar(trig, 0.001, grainDur * (1 + (i * 0.2)));

        // Resonant grain - sine with slight noise
        grain = SinOsc.ar(grainPitch) + (WhiteNoise.ar(0.1) * glint);
        grain = grain * env * (4 - i).reciprocal;
        grain
    });

    sig = grains * 0.3;

    // High shimmer layer
    shimmer = Dust.ar(flake.linexp(0, 1, 20, 200) * glint);
    shimmer = Ringz.ar(shimmer, freq * TRand.ar(4, 12, shimmer), 0.02) * 0.15 * glint;
    sig = sig + shimmer;

    // Stereo spread via swirl
    sig = [
        sig + (DelayC.ar(sig, 0.05, lfo.range(0.005, 0.015) * swirl) * 0.4),
        sig + (DelayC.ar(sig, 0.05, lfo.range(0.008, 0.02).neg.abs * swirl) * 0.4)
    ];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_icedust loaded".postln;
