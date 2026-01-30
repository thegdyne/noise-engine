// mod_caf/test — Lightweight end-stage generator
// test: Acoustic test tones - calibration signals
SynthDef(\forge_mod_caf_test, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var sine, pink, sweep, click, reference;
    var sweepFreq;

    sine = p[0].linlin(0, 1, 0.2, 0.8);  // P1: Sine level
    pink = p[1].linlin(0, 1, 0, 0.5);  // P2: Pink noise
    sweep = p[2].linlin(0, 1, 0, 0.5);  // P3: Sweep amount
    click = p[3].linlin(0, 1, 0.5, 4);  // P4: Click rate
    reference = p[4].linlin(0, 1, 0, 0.4);  // P5: Reference tone (1kHz)

    freq = In.kr(freqBus);

    // DSP: Pure sine test tone
    sig = SinOsc.ar(freq) * sine * 0.4;

    // Pink noise - broadband test
    sig = sig + (PinkNoise.ar(pink) * 0.4);

    // Sweep - slow frequency sweep around base
    sweepFreq = freq * LFTri.kr(0.1).range(0.5, 2);
    sig = sig + (SinOsc.ar(sweepFreq) * sweep * 0.3);

    // Click track - timing reference
    sig = sig + (Ringz.ar(Impulse.ar(click), 1000, 0.01) * 0.2);

    // 1kHz reference tone
    sig = sig + (SinOsc.ar(1000) * reference * 0.3);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_test loaded".postln;
