// duga/sweep — Lightweight end-stage generator
SynthDef(\forge_duga_sweep, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var span, speed, depth, ring, echo;
    var sweepOsc, modulator, carrier, echoSig, sweepFreq;

    freq = In.kr(freqBus);

    span = p[0];
    speed = p[1];
    depth = p[2];
    ring = p[3];
    echo = p[4];

    // Sweep oscillator - slow rotation
    sweepOsc = SinOsc.kr(speed.linexp(0, 1, 0.05, 1));
    sweepFreq = freq * sweepOsc.range(1 - (span * 0.5), 1 + (span * 0.5));

    // Phase modulation FM
    modulator = SinOsc.ar(sweepFreq * 2, 0, depth.linlin(0, 1, 0.5, 4));
    carrier = SinOsc.ar(sweepFreq, modulator);

    // Add resonant ringing
    sig = carrier + (Ringz.ar(carrier * 0.1, sweepFreq * 3, ring.linlin(0, 1, 0.05, 0.3)) * ring);

    sig = sig * 0.4;

    // Radar echo returns - delayed copies
    echoSig = CombL.ar(sig, 0.5, echo.linlin(0, 1, 0.05, 0.3), echo.linlin(0, 1, 0.1, 1));
    sig = sig + (echoSig * echo * 0.4);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_sweep loaded".postln;
