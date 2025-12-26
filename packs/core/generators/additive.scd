/*
Additive Generator
Harmonic partial synthesis with spectral shaping

Signal flow: Partials -> Mix -> Filter -> ENV VCA -> Output

Custom params:
  - P1 partial_ratio: 0.5-4.0 (harmonic spacing multiplier)
  - P2 partial_curve: -2 to +2 (spectral shape/rolloff)
  - P3 num_partials: 2-16 discrete (number of harmonics)
  - P4 amp_env_depth: 0-1 (per-partial envelope modulation)
  - P5 spectral_tilt: -1 to +1 (dark <-> bright)
*/

SynthDef(\additive, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var partialRatio, partialCurve, numPartials, envDepth, tilt;
    
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
    partialRatio = In.kr(customBus0);
    partialCurve = In.kr(customBus1);
    numPartials = In.kr(customBus2);
    envDepth = In.kr(customBus3);
    tilt = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    sig = Mix.fill(16, { |i|
        var harmonic = i + 1;
        var partialFreq, partialAmp, partialPhase;
        
        partialFreq = (freq * harmonic * partialRatio.linlin(0.5, 4.0, 0.98, 1.02)).clip(20, 20000);
        partialAmp = 1 / (harmonic ** (1.5 + partialCurve));
        partialAmp = partialAmp * (1 + (tilt * (harmonic - 1) * 0.1));
        partialPhase = LFNoise1.kr(0.1 + (i * 0.02)).range(-0.003, 0.003);
        partialAmp = partialAmp * (1 - (envDepth * LFNoise1.kr(0.5 + (i * 0.1)).range(0, 0.3)));
        
        SinOsc.ar(partialFreq * (1 + partialPhase)) * partialAmp * (harmonic <= numPartials)
    });
    sig = sig / numPartials.sqrt * 0.5;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    Out.ar(out, sig);
}).add;

"  [x] additive loaded".postln;
