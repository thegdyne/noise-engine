/*
LONGING Generator
The emotional core - quiet desperation and yearning

Features:
  - Yearning melodic tone
  - Dull ache undertone
  - Sense of distance
  - Faint hope glimmers
  - Quiet resignation

Custom params:
  - P1 yearn: Melodic yearning
  - P2 ache: Low painful undertone
  - P3 distance: Filtered separation
  - P4 hope: Brief bright moments
  - P5 resignation: Accepting drone

What remains of the human inside the husk.
*/

SynthDef(\longing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var yearn, ache, distance, hope, resignation;
    var trig, breathMod;
    var yearnSig, acheSig, distanceSig, hopeSig, resignationSig;
    var yearnOsc, yearnVib;
    var acheOsc, acheMod;
    var distanceOsc, distanceMod;
    var hopeTrig, hopeOsc;
    var resignOsc, resignLFO;
    
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
    
    // Custom params with smoothing
    yearn = In.kr(customBus0);
    yearn = Lag.kr(yearn, 0.1);
    ache = In.kr(customBus1);
    ache = Lag.kr(ache, 0.1);
    distance = In.kr(customBus2);
    distance = Lag.kr(distance, 0.1);
    hope = In.kr(customBus3);
    resignation = In.kr(customBus4);
    resignation = Lag.kr(resignation, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Breathing modulation - everything pulses slightly
    breathMod = SinOsc.kr(0.15).range(0.85, 1);
    
    // === YEARN (melodic longing) ===
    // Main melodic tone with expressive vibrato
    yearnVib = SinOsc.kr(5 + (yearn * 2)).range(-0.02, 0.02);
    yearnOsc = SinOsc.ar(freq * (1 + yearnVib));
    yearnOsc = yearnOsc + (SinOsc.ar(freq * 2 * (1 + yearnVib)) * 0.3);  // Octave
    // Add fifth for openness
    yearnOsc = yearnOsc + (SinOsc.ar(freq * 1.5 * (1 + yearnVib)) * 0.25);
    // Swell
    yearnOsc = yearnOsc * LFTri.kr(0.08).range(0.6, 1);
    yearnSig = yearnOsc * yearn * 0.4 * breathMod;
    
    // === ACHE (dull undertone) ===
    // Low, sustained pain
    acheMod = LFNoise2.kr(0.2).range(0.98, 1.02);
    acheOsc = SinOsc.ar(freq * 0.5 * acheMod);
    acheOsc = acheOsc + (SinOsc.ar(freq * 0.501) * 0.4);  // Slow beating
    // Minor second for dissonance/pain
    acheOsc = acheOsc + (SinOsc.ar(freq * 0.53 * acheMod) * 0.3);
    acheSig = LPF.ar(acheOsc, 400) * ache * 0.4 * breathMod;
    
    // === DISTANCE (separation) ===
    // Filtered, far away version of the sound
    distanceMod = LFNoise2.kr(0.3).range(0.95, 1.05);
    distanceOsc = SinOsc.ar(freq * distanceMod);
    distanceOsc = distanceOsc + (SinOsc.ar(freq * 2 * distanceMod) * 0.2);
    // Heavy filtering for distance
    distanceOsc = LPF.ar(distanceOsc, 300 + (distance * 200));
    distanceOsc = HPF.ar(distanceOsc, 100);
    // Add reverb-like quality with comb filter
    distanceOsc = distanceOsc + (CombL.ar(distanceOsc, 0.2, 0.1, 1) * 0.3);
    distanceSig = distanceOsc * distance * 0.35 * breathMod;
    
    // === HOPE (faint glimmers) ===
    // Brief bright moments
    hopeTrig = trig + Dust.ar(hope * 2);
    hopeOsc = SinOsc.ar(freq * 3);  // Higher, brighter
    hopeOsc = hopeOsc + (SinOsc.ar(freq * 4) * 0.5);
    hopeOsc = hopeOsc + (SinOsc.ar(freq * 5) * 0.3);  // Major chord voicing
    hopeOsc = hopeOsc * EnvGen.ar(Env.perc(0.1, 0.8, 1, -4), hopeTrig);
    hopeSig = hopeOsc * hope * 0.35;
    
    // === RESIGNATION (acceptance) ===
    // Steady, unchanging drone
    resignLFO = LFNoise2.kr(0.1).range(0.99, 1.01);
    resignOsc = SinOsc.ar(freq * 0.25 * resignLFO);
    resignOsc = resignOsc + (SinOsc.ar(freq * 0.5 * resignLFO) * 0.4);
    resignOsc = resignOsc + (SinOsc.ar(freq * 0.75 * resignLFO) * 0.3);  // Fifth below
    // Very stable, almost static
    resignOsc = resignOsc * 0.8;
    resignationSig = resignOsc * resignation * 0.35;
    
    // === MIX ===
    sig = yearnSig + acheSig + distanceSig + hopeSig + resignationSig;
    
    // Very soft limiting - keep the gentleness
    sig = (sig * 0.9).tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.06, 0.2);  // Gentle, slow movement
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ longing loaded".postln;
