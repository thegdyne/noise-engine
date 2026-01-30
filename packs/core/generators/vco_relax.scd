// core/vco_relax — Lightweight end-stage generator
/*
VCO Relax Generator
Relaxation oscillator inspired by Elektor circuits

Signal flow: Relaxation Osc -> Waveshaping -> Filter -> ENV VCA -> Output

Custom params:
  - P1 charge_rate: 0-1 (capacitor charge speed)
  - P2 threshold: 0-1 (trigger threshold)
  - P3 hysteresis: 0-1 (schmitt trigger width)
  - P4 waveshape: 0-1 (triangle <-> pulse)
  - P5 sync_amount: 0-1 (hard sync depth)
*/

SynthDef(\vcoRelax, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var chargeRate, threshold, hysteresis, waveshape, syncAmount;
    var tri, pulse, syncOsc;

    freq = In.kr(freqBus);

    chargeRate = p[0];
    threshold = p[1];
    hysteresis = p[2];
    waveshape = p[3];
    syncAmount = p[4];

    // === SOUND SOURCE ===
    tri = LFTri.ar(freq * chargeRate.linexp(0, 1, 0.5, 2));
    pulse = LFPulse.ar(freq, 0, threshold.linlin(0, 1, 0.1, 0.9));

    sig = SelectX.ar(waveshape, [tri, pulse]);

    syncOsc = SyncSaw.ar(freq, freq * syncAmount.linexp(0, 1, 1, 4)) * syncAmount;
    sig = sig + (syncOsc * 0.3);

    sig = (sig * (1 + (hysteresis * 2))).tanh * 0.7;

    sig = ~stereoSpread.(sig, 0.3, 0.3);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] vcoRelax loaded".postln;
