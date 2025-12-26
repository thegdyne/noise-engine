/*
STONEPATH Generator
Dry footsteps on ancient flagstones

Features:
  - Hard stone impacts
  - Grit and gravel texture
  - Chamber reverb
  - Variable weight/pace

Custom params:
  - P1 steps: Step rate
  - P2 stone: Surface hardness
  - P3 grit: Loose material
  - P4 hall: Echo space
  - P5 weight: Impact heaviness
*/

SynthDef(\stonepath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var steps, stone, grit, hall, weight;
    var trig, stepTrig, stepSig, gritSig, stoneSig;
    var stepEnv, stepRate;
    
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
    steps = In.kr(customBus0);
    steps = Lag.kr(steps, 0.1);
    stone = In.kr(customBus1);
    stone = Lag.kr(stone, 0.1);
    grit = In.kr(customBus2);
    grit = Lag.kr(grit, 0.05);
    hall = In.kr(customBus3);
    hall = Lag.kr(hall, 0.1);
    weight = In.kr(customBus4);
    weight = Lag.kr(weight, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Step rhythm
    stepRate = 1 + (steps * 2);
    stepTrig = trig + Impulse.ar(stepRate * LFNoise1.kr(0.5).range(0.85, 1.15));
    
    // === STONE (hard impact) ===
    stepEnv = EnvGen.ar(Env.perc(0.001, 0.08 + (weight * 0.05)), stepTrig);
    stoneSig = WhiteNoise.ar * stepEnv;
    stoneSig = BPF.ar(stoneSig, 800 + (stone * 600), 0.3);
    // Hard click
    stoneSig = stoneSig + (
        HPF.ar(WhiteNoise.ar, 2000) * 
        EnvGen.ar(Env.perc(0.001, 0.01), stepTrig) * stone
    );
    stoneSig = stoneSig * stone * 0.5;
    
    // === WEIGHT (low thud) ===
    stepSig = SinOsc.ar(freq * 0.5 * TRand.ar(0.9, 1.1, stepTrig));
    stepSig = stepSig * EnvGen.ar(Env.perc(0.01, 0.1 + (weight * 0.1)), stepTrig);
    stepSig = LPF.ar(stepSig, 200);
    stepSig = stepSig * weight * 0.4;
    
    // === GRIT (loose material) ===
    gritSig = Dust.ar(grit * 100 * EnvGen.ar(Env.perc(0.01, 0.15), stepTrig));
    gritSig = BPF.ar(gritSig + (PinkNoise.ar * 0.3), 2500, 0.4);
    gritSig = gritSig * grit * 0.3;
    
    // === MIX ===
    sig = stoneSig + stepSig + gritSig;
    
    // === HALL (chamber echo) ===
    sig = sig + (CombL.ar(sig, 0.3, 0.12, hall * 2) * hall * 0.4);
    sig = sig + (CombL.ar(sig, 0.3, 0.19, hall * 1.5) * hall * 0.3);
    sig = sig + (CombL.ar(sig, 0.3, 0.07, hall * 1) * hall * 0.2);
    
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.25, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    sig = Limiter.ar(sig, 0.95);
    Out.ar(out, sig);
}).add;

"  [x] stonepath loaded".postln;
