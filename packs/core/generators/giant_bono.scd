// core/giant_bono — Lightweight end-stage generator
/*
Giant B0N0 Generator
Chaotic oscillator inspired by Rob Hordijk's Benjolin

Signal flow: Dual oscillators -> Rungler -> XOR -> Filter -> ENV VCA -> Output

Custom params:
  - P1 osc2_ratio: 0.1-10 (second oscillator ratio)
  - P2 rungler_amount: 0-1 (chaos injection)
  - P3 xor_mix: 0-1 (clean <-> XOR output)
  - P4 filter_fm: 0-1 (filter frequency modulation)
  - P5 feedback: 0-1 (oscillator cross-modulation)
*/

SynthDef(\giantBono, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var osc2Ratio, runglerAmt, xorMix, filterFM, feedback;
    var osc1, osc2, rungler, xorSig, fbSig, runglerBits;

    freq = In.kr(freqBus);

    osc2Ratio = p[0];
    runglerAmt = p[1];
    xorMix = p[2];
    filterFM = p[3];
    feedback = p[4];

    // === SOUND SOURCE ===
    fbSig = LocalIn.ar(1);

    osc1 = LFTri.ar(freq * (1 + (fbSig * feedback * 0.5)));
    osc2 = LFPulse.ar(freq * osc2Ratio * (1 + (fbSig * feedback * 0.3)));

    // Simplified rungler - shift register chaos
    runglerBits = Mix.fill(8, { |i|
        var bit = ((osc1 > 0) * (osc2 > (i / 8 - 0.5))).lag(0.001);
        bit * (2 ** i) / 255
    });
    rungler = runglerBits * 2 - 1;

    xorSig = ((osc1 > 0) - (osc2 > 0)).abs * 2 - 1;

    sig = SelectX.ar(xorMix, [
        osc1 + (osc2 * 0.5),
        xorSig
    ]);

    sig = sig + (rungler * runglerAmt);
    sig = sig.tanh * 0.7;

    LocalOut.ar(sig);

    filterFreq = filterFreq * (1 + (rungler * filterFM * 2));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] giantBono loaded (chaos edition)".postln;
