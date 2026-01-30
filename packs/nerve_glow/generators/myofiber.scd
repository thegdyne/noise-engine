// nerve_glow/myofiber — Lightweight end-stage generator
// MYOFIBER -- Muscle fiber bowed string
// Physical modeling of muscle tissue -- warm, organic, pulsing

SynthDef(\forge_nerve_glow_myofiber, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var fiber, actin, contract, warmth, twitch;
    var bowPos, bowForce, vibRate, vibDepth;
    var fundamental, harmonics, body;

    // Standard bus reads
    freq = In.kr(freqBus);

    fiber = p[0].linlin(0, 1, 0.1, 0.9);  // Bow position
    actin = p[1].linexp(0, 1, 0.3, 3.0);  // Pressure variation rate
    contract = p[2].linlin(0, 1, 0.2, 0.9);  // Bow force
    warmth = p[3].linlin(0, 1, 1, 8);  // Harmonics count
    twitch = p[4].linexp(0, 1, 0.5, 12);  // Vibrato rate

    // Bow position modulation (actin sliding)
    bowPos = fiber + (SinOsc.kr(actin, 0, 0.15));

    // Muscle twitch vibrato
    vibRate = twitch;
    vibDepth = twitch.linlin(0.5, 12, 0.002, 0.015);

    // Bowed string simulation using saw + feedback
    fundamental = VarSaw.ar(
        freq * (1 + SinOsc.kr(vibRate, 0, vibDepth)),
        0,
        bowPos
    );

    // Add harmonics for warmth (like muscle fiber bundles)
    harmonics = Mix.fill(8, { |i|
        var hAmp = (warmth - i).clip(0, 1) * (0.7 ** i);
        var hFreq = freq * (i + 1) * (1 + SinOsc.kr(vibRate * (1 + (i * 0.1)), i * 0.5, vibDepth * 0.5));
        SinOsc.ar(hFreq) * hAmp * 0.12
    });

    // Bow friction noise
    body = BrownNoise.ar(0.03) * contract;
    body = BPF.ar(body, freq * 2, 0.3);

    sig = (fundamental * contract * 0.4) + harmonics + body;

    // Soft clip for organic warmth
    sig = (sig * 1.5).tanh * 0.7;

    // Stereo spread

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_nerve_glow_myofiber loaded".postln;
