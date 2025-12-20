/*
TENTACLE Generator
Writhing alien appendages

Features:
  - Continuous writhing movement
  - Wet slithering textures
  - Suction cup pops
  - Mass/body presence
  - Reaching grabbing motion

Custom params:
  - P1 writhe: Movement intensity
  - P2 slither: Wet sliding texture
  - P3 suction: Sucker sounds
  - P4 mass: Body thickness
  - P5 reach: Grabbing motion sweeps

Organic, wet, alien movement.
*/

SynthDef(\tentacle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var writhe, slither, suction, mass, reach;
    var trig, writheLFO;
    var writheSig, slitherSig, suctionSig, massSig, reachSig;
    var writheOsc, writheMod;
    var slitherNoise, slitherMod;
    var suctionTrig, suctionPop;
    var massOsc, massLFO;
    var reachSweep, reachOsc;
    
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
    writhe = In.kr(customBus0);
    writhe = Lag.kr(writhe, 0.05);
    slither = In.kr(customBus1);
    slither = Lag.kr(slither, 0.05);
    suction = In.kr(customBus2);
    mass = In.kr(customBus3);
    mass = Lag.kr(mass, 0.05);
    reach = In.kr(customBus4);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Global writhing motion
    writheLFO = LFNoise2.kr(0.5 + (writhe * 2)).range(0.8, 1.2);
    
    // === WRITHE (movement) ===
    // Slowly undulating pitched tones
    writheMod = LFNoise2.kr(0.8 + (writhe * 1.5));
    writheOsc = SinOsc.ar(freq * writheLFO * (1 + (writheMod * 0.2)));
    writheOsc = writheOsc + (SinOsc.ar(freq * 1.5 * writheLFO) * 0.3);
    // FM for organic quality
    writheOsc = writheOsc + (
        SinOsc.ar(freq, SinOsc.ar(freq * 0.5 * writheLFO) * (1 + writhe)) * 0.4
    );
    writheSig = writheOsc * writhe * 0.4;
    
    // === SLITHER (wet texture) ===
    // Filtered noise with squelchy modulation
    slitherNoise = PinkNoise.ar;
    slitherMod = LFNoise2.kr(3 + (slither * 8)).range(0.5, 2);
    slitherSig = BPF.ar(slitherNoise, 800 * slitherMod * writheLFO, 0.2) * 2;
    slitherSig = slitherSig + (BPF.ar(slitherNoise, 1500 * slitherMod, 0.3));
    // Wet "squelch" resonance
    slitherSig = slitherSig + (
        Resonz.ar(slitherNoise, 400 * writheLFO, 0.05) *
        LFNoise1.kr(5).range(0, 1) * 2
    );
    slitherSig = slitherSig * slither * 0.4;
    
    // === SUCTION (popping suckers) ===
    // Short resonant pops
    suctionTrig = trig + Dust.ar(suction * 12);
    suctionPop = SinOsc.ar(
        TRand.ar(200, 600, suctionTrig) * writheLFO,
        0,
        EnvGen.ar(Env.perc(0.001, 0.03 + (TRand.ar(0, 0.05, suctionTrig))), suctionTrig)
    );
    // "Pop" with pitch drop
    suctionPop = suctionPop + (
        SinOsc.ar(
            TRand.ar(300, 800, suctionTrig) *
            EnvGen.ar(Env.perc(0.001, 0.02), suctionTrig).linexp(0, 1, 0.5, 1)
        ) * EnvGen.ar(Env.perc(0.001, 0.04), suctionTrig) * 0.5
    );
    suctionSig = suctionPop * suction;
    
    // === MASS (body presence) ===
    // Low frequency body drone
    massLFO = LFNoise2.kr(0.3).range(0.95, 1.05);
    massOsc = SinOsc.ar(freq * 0.5 * massLFO * writheLFO);
    massOsc = massOsc + (SinOsc.ar(freq * 0.25 * massLFO) * 0.6);
    // Fleshy resonance
    massOsc = massOsc + (LPF.ar(Pulse.ar(freq * 0.25, 0.3), 200) * 0.3);
    massSig = LPF.ar(massOsc, 300 + (mass * 200)) * mass * 0.5;
    
    // === REACH (grabbing motion) ===
    // Pitch sweep suggesting extension
    reachSweep = EnvGen.ar(Env.perc(0.05, 0.8, 1, -2), trig);
    reachOsc = SinOsc.ar(freq * (1 + (reachSweep * reach)));
    reachOsc = reachOsc + (SinOsc.ar(freq * 2 * (1 + (reachSweep * reach * 0.5))) * 0.3);
    // Grabbing "close" - pitch down at end
    reachOsc = reachOsc + (
        SinOsc.ar(freq * 1.5 * (1 - (reachSweep * 0.3))) *
        EnvGen.ar(Env([0, 0, 1, 0], [0.3, 0.2, 0.5]), trig) * 0.4
    );
    reachSig = reachOsc * reachSweep * reach;
    
    // === MIX ===
    sig = writheSig + slitherSig + suctionSig + massSig + reachSig;
    
    // Soft saturation for organic density
    sig = (sig * 1.3).tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.2, 0.25);  // Organic movement
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ tentacle loaded".postln;
