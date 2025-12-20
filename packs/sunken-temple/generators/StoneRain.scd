/*
STONERAIN Generator
Rain falling on ancient stone surfaces

Features:
  - Filtered rain noise
  - Stone impact resonance
  - Pool splashes
  - Running water

Custom params:
  - P1 drops: Rain density
  - P2 stone: Surface resonance
  - P3 pool: Water pooling
  - P4 distance: Spatial depth
  - P5 flow: Running streams
*/

SynthDef(\stonerain, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var drops, stone, pool, distance, flow;
    var trig, rainSig, stoneSig, poolSig, flowSig;
    var dropTrig, stoneRes;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    drops = In.kr(customBus0);
    drops = Lag.kr(drops, 0.1);
    stone = In.kr(customBus1);
    stone = Lag.kr(stone, 0.1);
    pool = In.kr(customBus2);
    pool = Lag.kr(pool, 0.1);
    distance = In.kr(customBus3);
    distance = Lag.kr(distance, 0.2);
    flow = In.kr(customBus4);
    flow = Lag.kr(flow, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === RAIN (filtered noise) ===
    rainSig = WhiteNoise.ar;
    rainSig = BPF.ar(rainSig, 3000 + (LFNoise1.kr(2).range(-500, 500)), 0.5);
    rainSig = rainSig * (1 + (LFNoise1.kr(0.5).range(-0.3, 0.3)));  // Intensity variation
    // Distance filtering
    rainSig = LPF.ar(rainSig, LinExp.kr(distance, 0, 1, 8000, 2000));
    rainSig = rainSig * drops * 0.4;
    
    // === STONE (impact resonance) ===
    dropTrig = Dust.ar(20 + (drops * 60));
    stoneRes = SinOsc.ar(freq * TRand.ar(1, 4, dropTrig));
    stoneRes = stoneRes * EnvGen.ar(Env.perc(0.001, 0.05), dropTrig);
    stoneRes = BPF.ar(stoneRes + (dropTrig * 0.5), freq * 2, 0.2);
    stoneSig = stoneRes * stone * 0.3;
    
    // === POOL (water splashes) ===
    poolSig = SinOsc.ar(
        freq * 3 * TRand.ar(0.8, 1.5, Dust.ar(pool * 15)),
        0,
        EnvGen.ar(Env.perc(0.001, 0.08), Dust.ar(pool * 15))
    );
    // Ripple effect
    poolSig = CombL.ar(poolSig, 0.1, 0.03, 0.3);
    poolSig = LPF.ar(poolSig, 4000);
    poolSig = poolSig * pool * 0.4;
    
    // === FLOW (running water) ===
    flowSig = PinkNoise.ar;
    flowSig = BPF.ar(flowSig, 600 * LFNoise2.kr(0.5).range(0.7, 1.4), 0.4);
    flowSig = flowSig + (BPF.ar(PinkNoise.ar, 1500, 0.3) * 0.5);
    flowSig = flowSig * LFNoise1.kr(1 + flow).range(0.5, 1);
    flowSig = flowSig * flow * 0.3;
    
    // === SPATIAL (distance reverb) ===
    sig = rainSig + stoneSig + poolSig + flowSig;
    sig = sig + (CombL.ar(sig, 0.3, 0.11, distance * 2) * distance * 0.3);
    sig = sig + (CombL.ar(sig, 0.3, 0.17, distance * 1.5) * distance * 0.2);
    
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.5, 0.25);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ stonerain loaded".postln;
