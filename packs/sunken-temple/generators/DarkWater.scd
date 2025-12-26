/*
DARKWATER Generator
Murky flooded depths with tidal movement

Features:
  - Undulating bass tides
  - Murky filtered textures
  - Dripping from above
  - Underwater currents

Custom params:
  - P1 tide: Tidal bass movement
  - P2 murk: Sediment texture
  - P3 drip: Water drops
  - P4 current: Flow movement
  - P5 cold: Icy undertone
*/

SynthDef(\darkwater, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tide, murk, drip, current, cold;
    var trig, tideSig, murkSig, dripSig, currentSig, coldSig;
    var tideOsc;
    
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
    tide = In.kr(customBus0);
    tide = Lag.kr(tide, 0.2);
    murk = In.kr(customBus1);
    murk = Lag.kr(murk, 0.1);
    drip = In.kr(customBus2);
    drip = Lag.kr(drip, 0.05);
    current = In.kr(customBus3);
    current = Lag.kr(current, 0.1);
    cold = In.kr(customBus4);
    cold = Lag.kr(cold, 0.2);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === TIDE (undulating bass) ===
    tideOsc = LFTri.kr(0.15 + (tide * 0.1)).range(0.7, 1.3);
    tideSig = SinOsc.ar(freq * 0.5 * tideOsc);
    tideSig = tideSig + (SinOsc.ar(freq * 0.75 * tideOsc) * 0.5);
    tideSig = LPF.ar(tideSig, 300);
    tideSig = tideSig * LFTri.kr(0.08).range(0.5, 1);
    tideSig = tideSig * tide * 0.5;
    
    // === MURK (sediment) ===
    murkSig = BrownNoise.ar;
    murkSig = LPF.ar(murkSig, 200 + (murk * 300));
    murkSig = murkSig * LFNoise1.kr(0.5 + (murk * 2)).range(0.3, 1);
    murkSig = murkSig * murk * 0.4;
    
    // === DRIP (water drops) ===
    dripSig = SinOsc.ar(
        freq * 4 * TRand.kr(0.8, 1.5, Dust.kr(drip * 8)),
        0,
        EnvGen.ar(Env.perc(0.001, 0.1), Dust.ar(drip * 8))
    );
    // Splash ripple
    dripSig = dripSig + (
        BPF.ar(WhiteNoise.ar, 2000, 0.3) *
        EnvGen.ar(Env.perc(0.001, 0.05), Dust.ar(drip * 6)) * 0.3
    );
    dripSig = CombL.ar(dripSig, 0.2, 0.08, 0.5);  // Ripple echo
    dripSig = dripSig * drip * 0.5;
    
    // === CURRENT (flow) ===
    currentSig = PinkNoise.ar;
    currentSig = BPF.ar(currentSig, 400 * LFNoise2.kr(0.3).range(0.5, 2), 0.3);
    currentSig = currentSig * LFNoise1.kr(current * 3 + 0.5).range(0, 1);
    currentSig = currentSig * current * 0.3;
    
    // === COLD (icy tone) ===
    coldSig = SinOsc.ar(freq * 2 * LFNoise2.kr(0.2).range(0.99, 1.01));
    coldSig = coldSig + (SinOsc.ar(freq * 3.01) * 0.3);
    coldSig = HPF.ar(coldSig, 500);
    coldSig = coldSig * LFTri.kr(0.1).range(0.2, 0.8);
    coldSig = coldSig * cold * 0.2;
    
    // === MIX ===
    sig = tideSig + murkSig + dripSig + currentSig + coldSig;
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.25, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] darkwater loaded".postln;
