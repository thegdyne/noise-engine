/*
AMBERGLOW Generator
Warm golden light resonance, soft harmonic shimmer

Features:
  - Rich warm harmonics
  - Gentle shimmering movement
  - Light diffusion texture
  - Dust particles in beams

Custom params:
  - P1 warmth: Golden tone intensity
  - P2 shimmer: Light movement
  - P3 spread: Diffusion width
  - P4 dust: Particle texture
  - P5 ancient: Aged patina
*/

SynthDef(\amberglow, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var warmth, shimmer, spread, dust, ancient;
    var trig, warmSig, shimmerSig, dustSig;
    var warmOsc, shimmerMod;
    
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
    warmth = In.kr(customBus0);
    warmth = Lag.kr(warmth, 0.1);
    shimmer = In.kr(customBus1);
    shimmer = Lag.kr(shimmer, 0.1);
    spread = In.kr(customBus2);
    spread = Lag.kr(spread, 0.1);
    dust = In.kr(customBus3);
    dust = Lag.kr(dust, 0.05);
    ancient = In.kr(customBus4);
    ancient = Lag.kr(ancient, 0.2);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === WARMTH (golden harmonics) ===
    warmOsc = SinOsc.ar(freq);
    warmOsc = warmOsc + (SinOsc.ar(freq * 2) * 0.5);  // Octave
    warmOsc = warmOsc + (SinOsc.ar(freq * 3) * 0.25);  // 5th
    warmOsc = warmOsc + (SinOsc.ar(freq * 4) * 0.15);  // 2nd octave
    // Warm filtering - emphasize low-mids
    warmOsc = LPF.ar(warmOsc, 1500 + (warmth * 1000));
    warmOsc = warmOsc + (BPF.ar(warmOsc, 400, 0.3) * warmth * 0.5);
    warmSig = warmOsc * warmth * 0.4;
    
    // === SHIMMER (light dancing) ===
    shimmerMod = LFNoise2.kr(3 + (shimmer * 8)).range(0.95, 1.05);
    shimmerSig = SinOsc.ar(freq * 2 * shimmerMod);
    shimmerSig = shimmerSig + (SinOsc.ar(freq * 3.01 * shimmerMod) * 0.5);
    shimmerSig = shimmerSig * LFNoise1.kr(5 + (shimmer * 10)).range(0.3, 1);
    shimmerSig = HPF.ar(shimmerSig, 800);
    shimmerSig = shimmerSig * shimmer * 0.3;
    
    // === DUST (particles in light) ===
    dustSig = Dust.ar(dust * 80) * 0.5;
    dustSig = BPF.ar(dustSig, 3000 + (LFNoise1.kr(2).range(0, 2000)), 0.3);
    dustSig = dustSig + (Dust.ar(dust * 40) * BPF.ar(PinkNoise.ar, 1500, 0.2) * 0.3);
    dustSig = dustSig * dust;
    
    // === SPREAD (diffusion) ===
    sig = warmSig + shimmerSig + dustSig;
    sig = sig + (CombL.ar(sig, 0.1, 0.03 + (spread * 0.02), spread * 0.5) * spread * 0.3);
    sig = sig + (CombL.ar(sig, 0.1, 0.05, spread * 0.4) * spread * 0.2);
    
    // === ANCIENT (aged quality) ===
    sig = sig + (BPF.ar(PinkNoise.ar, 200, 0.2) * ancient * 0.1);
    sig = LPF.ar(sig, 6000 - (ancient * 2000));
    
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.3, 0.15);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ amberglow loaded".postln;
