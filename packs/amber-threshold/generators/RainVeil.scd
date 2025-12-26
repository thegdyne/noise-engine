/*
RAINVEIL Generator
Gentle rain curtain, soft atmospheric

Features:
  - Soft filtered rain noise
  - Distant diffusion
  - Trickling water
  - Misty atmosphere

Custom params:
  - P1 density: Rain amount
  - P2 soft: Gentleness
  - P3 distant: Spatial depth
  - P4 trickle: Water trickle
  - P5 mist: Atmospheric haze
*/

SynthDef(\rainveil, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, soft, distant, trickle, mist;
    var trig, rainSig, trickleSig, mistSig;
    
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
    density = In.kr(customBus0);
    density = Lag.kr(density, 0.1);
    soft = In.kr(customBus1);
    soft = Lag.kr(soft, 0.1);
    distant = In.kr(customBus2);
    distant = Lag.kr(distant, 0.2);
    trickle = In.kr(customBus3);
    trickle = Lag.kr(trickle, 0.1);
    mist = In.kr(customBus4);
    mist = Lag.kr(mist, 0.2);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === RAIN (soft noise) ===
    rainSig = PinkNoise.ar;
    rainSig = BPF.ar(rainSig, 2000 + (LFNoise1.kr(1).range(-300, 300)), 0.5);
    // Soft filtering
    rainSig = LPF.ar(rainSig, 4000 - (soft * 2000));
    // Intensity variation
    rainSig = rainSig * (1 + (LFNoise1.kr(0.3).range(-0.2, 0.2)));
    rainSig = rainSig * density * 0.4;
    
    // Distance filtering
    rainSig = LPF.ar(rainSig, LinExp.kr(distant, 0, 1, 6000, 1500));
    
    // === TRICKLE (water running) ===
    trickleSig = BPF.ar(PinkNoise.ar, 1200 * LFNoise2.kr(2 + trickle).range(0.7, 1.4), 0.2);
    trickleSig = trickleSig * LFNoise1.kr(3 + (trickle * 5)).range(0, 1);
    // Drip accents
    trickleSig = trickleSig + (
        SinOsc.ar(freq * 3 * TRand.ar(0.9, 1.2, Dust.ar(trickle * 10))) *
        EnvGen.ar(Env.perc(0.001, 0.05), Dust.ar(trickle * 10)) * 0.3
    );
    trickleSig = trickleSig * trickle * 0.3;
    
    // === MIST (atmospheric) ===
    mistSig = LPF.ar(PinkNoise.ar, 400);
    mistSig = mistSig + (BPF.ar(BrownNoise.ar, 200, 0.3) * 0.5);
    mistSig = mistSig * LFTri.kr(0.05).range(0.6, 1);
    mistSig = mistSig * mist * 0.2;
    
    // === MIX ===
    sig = rainSig + trickleSig + mistSig;
    
    // Distant reverb
    sig = sig + (CombL.ar(sig, 0.3, 0.15, distant * 2) * distant * 0.3);
    
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.5, 0.25);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] rainveil loaded".postln;
