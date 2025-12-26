/*
TORCHFLICKER Generator
Fire crackling, warm flame sounds

Features:
  - Flickering flame noise
  - Wood crackling
  - Fire roar/rush
  - Warm tonal undertone

Custom params:
  - P1 flame: Flame intensity
  - P2 crackle: Wood pops
  - P3 roar: Fire rush
  - P4 warmth: Warm tone
  - P5 gust: Wind variation
*/

SynthDef(\torchflicker, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                           filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                           midiTrigBus=0, slotIndex=0,
                           customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flame, crackle, roar, warmth, gust;
    var trig, flameSig, crackleSig, roarSig, warmSig;
    var flickerMod, gustMod;
    
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
    flame = In.kr(customBus0);
    flame = Lag.kr(flame, 0.1);
    crackle = In.kr(customBus1);
    crackle = Lag.kr(crackle, 0.05);
    roar = In.kr(customBus2);
    roar = Lag.kr(roar, 0.1);
    warmth = In.kr(customBus3);
    warmth = Lag.kr(warmth, 0.1);
    gust = In.kr(customBus4);
    gust = Lag.kr(gust, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Flicker modulation
    flickerMod = LFNoise2.kr(8 + (flame * 10)).range(0.5, 1.2);
    // Gust modulation
    gustMod = LFNoise1.kr(0.5 + gust).range(1 - (gust * 0.3), 1 + (gust * 0.5));
    
    // === FLAME (flickering noise) ===
    flameSig = BPF.ar(PinkNoise.ar, 800 * flickerMod, 0.4);
    flameSig = flameSig + (BPF.ar(WhiteNoise.ar, 2000 * flickerMod, 0.3) * 0.5);
    flameSig = flameSig * flickerMod * gustMod;
    flameSig = flameSig * flame * 0.4;
    
    // === CRACKLE (wood pops) ===
    crackleSig = Dust.ar(crackle * 30) * WhiteNoise.ar;
    crackleSig = BPF.ar(crackleSig, 1500 + TRand.ar(0, 1000, Dust.ar(crackle * 30)), 0.2);
    // Sharp pops
    crackleSig = crackleSig + (
        Dust.ar(crackle * 15) *
        EnvGen.ar(Env.perc(0.001, 0.02), Dust.ar(crackle * 15)) * 2
    );
    crackleSig = crackleSig * crackle * 0.5;
    
    // === ROAR (fire rush) ===
    roarSig = BrownNoise.ar;
    roarSig = BPF.ar(roarSig, 300 * gustMod, 0.5);
    roarSig = roarSig + (LPF.ar(PinkNoise.ar, 400) * 0.3);
    roarSig = roarSig * LFNoise1.kr(2 + roar).range(0.6, 1);
    roarSig = roarSig * roar * 0.3;
    
    // === WARMTH (tonal) ===
    warmSig = SinOsc.ar(freq * LFNoise2.kr(0.5).range(0.98, 1.02));
    warmSig = warmSig + (SinOsc.ar(freq * 2) * 0.3);
    warmSig = LPF.ar(warmSig, 600);
    warmSig = warmSig * flickerMod * warmth * 0.3;
    
    // === MIX ===
    sig = flameSig + crackleSig + roarSig + warmSig;
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.3, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] torchflicker loaded".postln;
