/*
CRUMBLEECHO Generator
Falling debris and structural decay

Features:
  - Stone/debris impacts
  - Variable debris size
  - Scattering patterns
  - Reverberant echoes

Custom params:
  - P1 fall: Fall rate
  - P2 size: Debris size
  - P3 scatter: Bounce pattern
  - P4 hall: Echo space
  - P5 decay: Structural crumbling
*/

SynthDef(\crumbleecho, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                          midiTrigBus=0, slotIndex=0,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, ampDecay, amp, envSource, clockRate, portamento;
    var fall, size, scatter, hall, structDecay;
    var trig, fallTrig, impactSig, scatterSig, decaySig;
    var impactFreq, impactEnv;
    
    // Standard params
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    ampDecay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    fall = In.kr(customBus0);
    fall = Lag.kr(fall, 0.1);
    size = In.kr(customBus1);
    size = Lag.kr(size, 0.1);
    scatter = In.kr(customBus2);
    scatter = Lag.kr(scatter, 0.05);
    hall = In.kr(customBus3);
    hall = Lag.kr(hall, 0.1);
    structDecay = In.kr(customBus4);
    structDecay = Lag.kr(structDecay, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Fall trigger
    fallTrig = trig + Dust.ar(fall * 8 + 1);
    
    // === IMPACT (main debris hit) ===
    impactFreq = freq * LinExp.kr(size, 0, 1, 2, 0.3);  // Bigger = lower
    impactEnv = EnvGen.ar(Env.perc(0.001, 0.05 + (size * 0.15)), fallTrig);
    
    impactSig = SinOsc.ar(impactFreq * TRand.ar(0.9, 1.1, fallTrig)) * impactEnv;
    impactSig = impactSig + (BPF.ar(WhiteNoise.ar, 1000 - (size * 600), 0.3) * impactEnv);
    impactSig = impactSig * 0.5;
    
    // === SCATTER (bouncing debris) ===
    scatterSig = Mix.fill(5, { |i|
        var scatterTrig = TDelay.ar(fallTrig, TRand.ar(0.02, 0.15, fallTrig) * (i + 1));
        var scatterEnv = EnvGen.ar(Env.perc(0.001, 0.02 + (0.01 * i)), scatterTrig);
        var scatterFreq = impactFreq * TRand.ar(1.5, 3, scatterTrig);
        SinOsc.ar(scatterFreq) * scatterEnv * (0.3 / (i + 1))
    });
    scatterSig = scatterSig * scatter;
    
    // === STRUCTURAL DECAY (crumbling) ===
    decaySig = Dust.ar(structDecay * 50) * BrownNoise.ar;
    decaySig = LPF.ar(decaySig, 500);
    decaySig = decaySig + (Crackle.ar(1.8) * structDecay * 0.05);
    decaySig = decaySig * structDecay * 0.3;
    
    // === MIX ===
    sig = impactSig + scatterSig + decaySig;
    
    // === HALL (reverb) ===
    sig = sig + (CombL.ar(sig, 0.5, 0.17, hall * 3) * hall * 0.4);
    sig = sig + (CombL.ar(sig, 0.5, 0.23, hall * 2.5) * hall * 0.3);
    sig = sig + (CombL.ar(sig, 0.5, 0.31, hall * 2) * hall * 0.2);
    
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.4, 0.25);
    sig = ~envVCA.(sig, envSource, clockRate, attack, ampDecay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ crumbleecho loaded".postln;
