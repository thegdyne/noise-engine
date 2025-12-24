/*
Giant B0N0 Generator
Chaotic oscillator inspired by Rob Hordijk's Benjolin

Signal flow: Dual oscillators → Rungler → XOR → Filter → ENV VCA → Output

Custom params:
  - P1 osc2_ratio: 0.1-10 (second oscillator ratio)
  - P2 rungler_amount: 0-1 (chaos injection)
  - P3 xor_mix: 0-1 (clean <-> XOR output)
  - P4 filter_fm: 0-1 (filter frequency modulation)
  - P5 feedback: 0-1 (oscillator cross-modulation)
*/

SynthDef(\giantBono, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var osc2Ratio, runglerAmt, xorMix, filterFM, feedback;
    var osc1, osc2, rungler, xorSig, fbSig, runglerBits;
    
    // Standard params
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    osc2Ratio = In.kr(customBus0);
    runglerAmt = In.kr(customBus1);
    xorMix = In.kr(customBus2);
    filterFM = In.kr(customBus3);
    feedback = In.kr(customBus4);
    
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
    
    // === PROCESSING CHAIN ===
    filterFreq = filterFreq * (1 + (rungler * filterFM * 2));
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    sig = ~multiFilter.(sig, filterType, filterFreq.clip(20, 18000), rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ giantBono loaded (chaos edition)".postln;
