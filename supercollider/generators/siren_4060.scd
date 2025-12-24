/*
4060 Siren Generator
CD4060 counter/divider siren circuit

Signal flow: Counter outputs → Mix → Filter → ENV VCA → Output

Custom params:
  - P1 clock_rate: 0-1 (master clock speed)
  - P2 division_mix: 0-1 (which counter outputs)
  - P3 sweep_rate: 0-1 (pitch sweep speed)
  - P4 sweep_depth: 0-1 (pitch sweep amount)
  - P5 reset_chaos: 0-1 (counter reset randomness)
*/

SynthDef(\siren4060, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var clockR, divMix, sweepRate, sweepDepth, resetChaos;
    var masterClock, divisions, sweep;
    
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
    clockR = In.kr(customBus0);
    divMix = In.kr(customBus1);
    sweepRate = In.kr(customBus2);
    sweepDepth = In.kr(customBus3);
    resetChaos = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    sweep = SinOsc.kr(sweepRate.linexp(0, 1, 0.1, 10)) * sweepDepth;
    masterClock = freq * clockR.linexp(0, 1, 0.5, 4) * (1 + sweep);
    
    divisions = Mix([
        Pulse.ar(masterClock / 2, 0.5) * (1 - divMix),
        Pulse.ar(masterClock / 4, 0.5) * divMix.sqrt,
        Pulse.ar(masterClock / 8, 0.5) * divMix,
        Pulse.ar(masterClock / 16, 0.5) * (divMix ** 2)
    ]) * 0.25;
    
    sig = divisions;
    sig = sig + (Dust.ar(resetChaos.linexp(0, 1, 1, 100)) * resetChaos * 0.2);
    
    // === PROCESSING CHAIN ===
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ siren4060 loaded".postln;
