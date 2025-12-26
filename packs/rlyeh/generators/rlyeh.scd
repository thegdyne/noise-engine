/*
RLYEH Generator
The sunken city rising from the deep

Features:
  - Ancient stone grinding and shifting
  - Water displacement and cascading
  - Massive structure groaning
  - Rising pitch sweeps
  - Ancient metallic resonance

Custom params:
  - P1 stone: Grinding stone textures
  - P2 water: Water displacement sounds
  - P3 groan: Structure stress sounds
  - P4 rise: Upward pitch sweep intensity
  - P5 age: Ancient metallic decay character

Hybrid triggered/continuous - the city is always shifting.
*/

SynthDef(\rlyeh, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                    midiTrigBus=0, slotIndex=0,
                    customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var stone, water, groan, rise, age;
    var trig, riseEnv;
    var stoneSig, waterSig, groanSig, riseSig, ageSig;
    var stoneNoise, stoneLFO;
    var waterNoise, waterMod;
    var groanOsc, groanLFO;
    var riseOsc, riseSweep;
    var agePartials, ageMod;
    
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
    stone = In.kr(customBus0);
    stone = Lag.kr(stone, 0.05);
    water = In.kr(customBus1);
    water = Lag.kr(water, 0.05);
    groan = In.kr(customBus2);
    groan = Lag.kr(groan, 0.05);
    rise = In.kr(customBus3);
    age = In.kr(customBus4);
    age = Lag.kr(age, 0.05);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Rising envelope on trigger
    riseEnv = EnvGen.ar(Env.perc(0.01, 3, 1, -2), trig);
    
    // === STONE (grinding textures) ===
    // Filtered noise with slow modulation for stone movement
    stoneNoise = BrownNoise.ar;
    stoneLFO = LFNoise1.kr(0.5).range(0.5, 2);
    stoneSig = BPF.ar(stoneNoise, freq * stoneLFO, 0.3) * 2;
    stoneSig = stoneSig + (BPF.ar(stoneNoise, freq * 2 * stoneLFO, 0.2) * 1.5);
    // Crumbling texture
    stoneSig = stoneSig + (Dust.ar(20 * stone) * BPF.ar(stoneNoise, 800, 0.5) * 0.5);
    stoneSig = stoneSig * stone * (0.7 + (riseEnv * 0.3));
    
    // === WATER (displacement cascades) ===
    // Filtered noise with faster modulation
    waterNoise = WhiteNoise.ar;
    waterMod = LFNoise2.kr(2).range(0.8, 1.2);
    waterSig = BPF.ar(waterNoise, 400 * waterMod, 0.6) * 0.5;
    waterSig = waterSig + (HPF.ar(waterNoise, 3000) * 0.2);  // Spray
    // Bubbling
    waterSig = waterSig + (SinOsc.ar(LFNoise0.kr(8).range(100, 400)) * 0.1 *
        EnvGen.ar(Env.perc(0.001, 0.05), Dust.ar(15)));
    waterSig = waterSig * water * (0.6 + (riseEnv * 0.4));
    
    // === GROAN (structure stress) ===
    // Low resonant drones with pitch bending
    groanLFO = LFNoise2.kr(0.3).range(0.95, 1.05);
    groanOsc = SinOsc.ar(freq * 0.5 * groanLFO);
    groanOsc = groanOsc + (Saw.ar(freq * 0.25 * groanLFO) * 0.3);
    // Stress creaking
    groanOsc = groanOsc + (LFPulse.ar(freq * 0.125, 0, LFNoise2.kr(0.2).range(0.1, 0.5)) * 0.2);
    groanSig = LPF.ar(groanOsc, 300 + (groan * 400)) * groan;
    
    // === RISE (upward sweeps) ===
    // Pitch sweep triggered by clock/MIDI
    riseSweep = EnvGen.ar(Env.perc(0.1, 2, 1, -4), trig);
    riseOsc = SinOsc.ar(freq * (1 + (riseSweep * rise * 2)));  // Up to 3x freq
    riseOsc = riseOsc + (Saw.ar(freq * 0.5 * (1 + (riseSweep * rise))) * 0.3);
    riseSig = riseOsc * riseSweep * rise;
    
    // === AGE (ancient metallic resonance) ===
    // Inharmonic partials with long decay
    ageMod = LFNoise2.kr(0.2).range(0.99, 1.01);
    agePartials = SinOsc.ar(freq * 3.17 * ageMod) * 0.3;
    agePartials = agePartials + (SinOsc.ar(freq * 5.43 * ageMod) * 0.2);
    agePartials = agePartials + (SinOsc.ar(freq * 7.89 * ageMod) * 0.15);
    // Gong-like decay
    agePartials = agePartials * EnvGen.ar(Env.perc(0.001, 4 + (age * 4), 1, -2), trig);
    ageSig = HPF.ar(agePartials, 400) * age * 0.6;
    
    // === MIX ===
    sig = stoneSig + waterSig + groanSig + riseSig + ageSig;
    
    // Soft limiting
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.2, 0.25);  // Wide shifting
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    sig = LeakDC.ar(sig);
    Out.ar(out, sig);
}).add;

"  [x] rlyeh loaded".postln;
