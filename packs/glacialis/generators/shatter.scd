// glacialis/shatter — Lightweight end-stage generator
// SHATTER - Ice crack and splinter
// Dust-triggered resonant fractures

SynthDef(\forge_glacialis_shatter, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var fracture, splinter, echo, weight, spray;
    var cracks, splinters, thuds, particles, trig;

    fracture = p[0];  // Crack density
    splinter = p[1];  // Splinter pitch
    echo = p[2];  // Resonance decay
    weight = p[3];  // Low thud
    spray = p[4];  // Spread

    freq = In.kr(freqBus);

    // Main crack triggers
    trig = Dust.ar(fracture.linexp(0, 1, 2, 40));

    // Sharp cracks - high resonant pings
    cracks = Ringz.ar(trig,
        freq * splinter.linexp(0, 1, 2, 8) * [1, 1.73, 2.41],
        echo.linexp(0, 1, 0.05, 0.4)
    ).sum * 0.4;

    // Ice splinters - higher density, varied pitch
    splinters = Dust.ar(fracture.linexp(0, 1, 10, 100) * spray);
    splinters = Ringz.ar(splinters,
        TRand.ar(freq * 3, freq * 12, splinters),
        echo.linexp(0, 1, 0.02, 0.15)
    ) * 0.2 * spray;

    // Low thuds for heavy cracks
    thuds = Ringz.ar(trig * weight,
        freq * [0.5, 0.75, 1],
        echo.linexp(0, 1, 0.1, 0.5)
    ).sum * 0.5 * weight;

    // Combine
    sig = cracks + splinters + thuds;

    // Add some white noise burst for texture
    particles = WhiteNoise.ar(1) * Decay.ar(trig, 0.02) * 0.2;
    particles = HPF.ar(particles, 2000);
    sig = sig + (particles * spray);

    // Stereo spray
    sig = [
        sig + (DelayC.ar(sig, 0.05, spray.linlin(0, 1, 0.001, 0.02)) * 0.3),
        sig + (DelayC.ar(sig, 0.05, spray.linlin(0, 1, 0.002, 0.03)) * 0.3)
    ];

    // Remove DC from impulsive content

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_shatter loaded".postln;
