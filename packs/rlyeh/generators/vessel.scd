/*
VESSEL Generator
The doomed boat - tiny humanity against cosmic indifference

Features:
  - Creaking wood under stress
  - Sail flapping in wind
  - Rope tension and snapping
  - Hull resonance
  - Sense of doom

Custom params:
  - P1 creak: Wood stress sounds
  - P2 sail: Canvas flapping
  - P3 rope: Rope under tension
  - P4 hull: Hull body resonance
  - P5 doom: Underlying dread tone

The fragile human element in cosmic horror.
*/

SynthDef(\vessel, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                     filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                     midiTrigBus=0, slotIndex=0,
                     customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var creak, sail, rope, hull, doom;
    var trig, rockLFO;
    var creakSig, sailSig, ropeSig, hullSig, doomSig;
    var creakNoise, creakMod;
    var sailNoise, sailMod;
    var ropeTrig, ropeHit;
    var hullOsc, hullEnv;
    var doomOsc, doomLFO;
    
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
    creak = In.kr(customBus0);
    creak = Lag.kr(creak, 0.05);
    sail = In.kr(customBus1);
    sail = Lag.kr(sail, 0.05);
    rope = In.kr(customBus2);
    hull = In.kr(customBus3);
    hull = Lag.kr(hull, 0.05);
    doom = In.kr(customBus4);
    doom = Lag.kr(doom, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Boat rocking motion - affects everything
    rockLFO = LFTri.kr(0.3).range(0.7, 1.3);
    
    // === CREAK (wood stress) ===
    // Pitched noise bursts with resonance
    creakNoise = PinkNoise.ar;
    creakMod = LFNoise2.kr(2 + (creak * 5)).range(0.8, 1.2);
    // Multiple resonant "wood" frequencies
    creakSig = BPF.ar(creakNoise, 300 * creakMod * rockLFO, 0.05) * 3;
    creakSig = creakSig + (BPF.ar(creakNoise, 500 * creakMod, 0.08) * 2);
    creakSig = creakSig + (BPF.ar(creakNoise, 800 * creakMod, 0.1));
    // Triggered stress sounds
    creakSig = creakSig * (
        LFNoise1.kr(3).range(0.3, 1) +
        (EnvGen.ar(Env.perc(0.01, 0.3), Dust.ar(creak * 5)) * 0.5)
    );
    creakSig = creakSig * creak * 0.5;
    
    // === SAIL (flapping canvas) ===
    // Rhythmic filtered noise
    sailNoise = WhiteNoise.ar;
    sailMod = LFPulse.kr(3 + (sail * 5) + LFNoise1.kr(0.5).range(-1, 1), 0, 0.3);
    sailSig = BPF.ar(sailNoise, 600, 0.4) * sailMod;
    sailSig = sailSig + (HPF.ar(sailNoise, 2000) * sailMod * 0.3);  // High snap
    sailSig = sailSig * sail * 0.4;
    
    // === ROPE (tension and snap) ===
    // Short pitched impacts
    ropeTrig = trig + Dust.ar(rope * 4);
    ropeHit = SinOsc.ar(freq * 2 * TRand.ar(0.9, 1.1, ropeTrig));
    ropeHit = ropeHit + (SinOsc.ar(freq * 3.2) * 0.3);
    ropeHit = ropeHit * EnvGen.ar(Env.perc(0.001, 0.05 + (TRand.ar(0, 0.1, ropeTrig))), ropeTrig);
    // Tension creak
    ropeHit = ropeHit + (
        BPF.ar(PinkNoise.ar, 1200 * rockLFO, 0.1) *
        LFNoise1.kr(5).range(0, 1) * 0.3
    );
    ropeSig = ropeHit * rope;
    
    // === HULL (body resonance) ===
    // Low wooden thump when waves hit
    hullEnv = EnvGen.ar(Env.perc(0.01, 0.4), trig + Dust.ar(hull * 2));
    hullOsc = SinOsc.ar(freq * 0.5 * rockLFO);
    hullOsc = hullOsc + (SinOsc.ar(freq * 0.75) * 0.4);
    // Wooden body resonance
    hullOsc = hullOsc + (BPF.ar(BrownNoise.ar, 150, 0.3) * 0.5);
    hullSig = LPF.ar(hullOsc * hullEnv, 400) * hull;
    
    // === DOOM (underlying dread) ===
    // Low ominous drone
    doomLFO = LFNoise2.kr(0.2).range(0.95, 1.05);
    doomOsc = SinOsc.ar(freq * 0.25 * doomLFO);
    doomOsc = doomOsc + (SinOsc.ar(freq * 0.251) * 0.5);  // Slow beating
    // Subtle dissonance
    doomOsc = doomOsc + (SinOsc.ar(freq * 0.375) * 0.3);  // Tritone below
    doomOsc = LPF.ar(doomOsc, 200);
    doomSig = doomOsc * doom * 0.5 * LFTri.kr(0.15).range(0.5, 1);
    
    // === MIX ===
    sig = creakSig + sailSig + ropeSig + hullSig + doomSig;
    
    // Soft limiting
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.15, 0.2);  // Moderate rocking movement
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ vessel loaded".postln;
