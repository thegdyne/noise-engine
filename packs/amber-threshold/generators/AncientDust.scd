/*
ANCIENTDUST Generator
Particles dancing in light beams

Features:
  - Granular particle texture
  - Sparkle when catching light
  - Swirling movement
  - Settling density

Custom params:
  - P1 swirl: Movement pattern
  - P2 sparkle: Light reflections
  - P3 thick: Particle density
  - P4 settle: Falling/settling
  - P5 age: Ancient texture
*/

SynthDef(\ancientdust, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                          midiTrigBus=0, slotIndex=0,
                          customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var swirl, sparkle, thick, settle, age;
    var trig, dustSig, sparkleSig, settleSig, ageSig;
    var swirlMod;
    
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
    swirl = In.kr(customBus0);
    swirl = Lag.kr(swirl, 0.1);
    sparkle = In.kr(customBus1);
    sparkle = Lag.kr(sparkle, 0.05);
    thick = In.kr(customBus2);
    thick = Lag.kr(thick, 0.1);
    settle = In.kr(customBus3);
    settle = Lag.kr(settle, 0.1);
    age = In.kr(customBus4);
    age = Lag.kr(age, 0.2);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Swirling modulation
    swirlMod = LFNoise2.kr(0.5 + (swirl * 2)).range(0.5, 1.5);
    
    // === DUST (granular base) ===
    dustSig = Dust.ar(thick * 200 + 50);
    dustSig = BPF.ar(dustSig, 2000 * swirlMod, 0.3);
    dustSig = dustSig + (Dust.ar(thick * 100) * BPF.ar(PinkNoise.ar, 3000, 0.2) * 0.5);
    dustSig = dustSig * thick * 0.4;
    
    // === SPARKLE (light catching) ===
    sparkleSig = Dust.ar(sparkle * 30);
    sparkleSig = sparkleSig * SinOsc.ar(freq * 4 * TRand.ar(0.9, 1.5, Dust.ar(sparkle * 30)));
    sparkleSig = HPF.ar(sparkleSig, 3000);
    sparkleSig = sparkleSig + (
        Resonz.ar(Dust.ar(sparkle * 50), 5000, 0.02) * 3
    );
    sparkleSig = sparkleSig * sparkle * 0.3;
    
    // === SETTLE (falling particles) ===
    settleSig = Dust.ar(settle * 40) * BrownNoise.ar;
    settleSig = LPF.ar(settleSig, 1000);
    settleSig = settleSig * LFNoise1.kr(settle + 0.5).range(0.3, 1);
    settleSig = settleSig * settle * 0.3;
    
    // === AGE (ancient texture) ===
    ageSig = Crackle.ar(1.5 + (age * 0.4)) * age * 0.05;
    ageSig = ageSig + (BPF.ar(PinkNoise.ar, 400, 0.2) * age * 0.1);
    
    // === MIX ===
    sig = dustSig + sparkleSig + settleSig + ageSig;
    
    // Swirl spatial movement
    sig = sig + (DelayL.ar(sig, 0.1, LFNoise2.kr(swirl + 0.5).range(0.01, 0.05)) * swirl * 0.3);
    
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.5, 0.3);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ ancientdust loaded".postln;
