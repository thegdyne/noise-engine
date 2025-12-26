/*
THRESHOLDHUM Generator
Liminal doorway resonance, standing waves

Features:
  - Standing wave harmonics
  - Portal-like resonance
  - Liminal between-space feel
  - Pulsing energy

Custom params:
  - P1 standing: Standing wave
  - P2 portal: Doorway resonance
  - P3 liminal: Between-space
  - P4 pulse: Energy pulsing
  - P5 ancient: Mystery/age
*/

SynthDef(\thresholdhum, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                           filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                           midiTrigBus=0, slotIndex=0,
                           customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var standing, portal, liminal, pulse, ancient;
    var trig, standingSig, portalSig, liminalSig, pulseMod;
    
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
    standing = In.kr(customBus0);
    standing = Lag.kr(standing, 0.1);
    portal = In.kr(customBus1);
    portal = Lag.kr(portal, 0.1);
    liminal = In.kr(customBus2);
    liminal = Lag.kr(liminal, 0.2);
    pulse = In.kr(customBus3);
    pulse = Lag.kr(pulse, 0.1);
    ancient = In.kr(customBus4);
    ancient = Lag.kr(ancient, 0.2);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Pulse modulation
    pulseMod = LFTri.kr(0.3 + (pulse * 0.5)).range(0.7, 1) * (1 - pulse) + (
        LFPulse.kr(0.5 + (pulse * 1), 0, 0.5).lag(0.1) * pulse
    );
    
    // === STANDING WAVE ===
    standingSig = SinOsc.ar(freq);
    standingSig = standingSig + (SinOsc.ar(freq * 2) * 0.5);
    standingSig = standingSig + (SinOsc.ar(freq * 3) * 0.33);
    standingSig = standingSig + (SinOsc.ar(freq * 4) * 0.25);
    // Slight detuning for standing wave effect
    standingSig = standingSig + (SinOsc.ar(freq * 1.003) * 0.3);
    standingSig = standingSig * standing * 0.3 * pulseMod;
    
    // === PORTAL (doorway resonance) ===
    portalSig = Resonz.ar(PinkNoise.ar, freq * 1.5, 0.02) * 5;
    portalSig = portalSig + Resonz.ar(PinkNoise.ar, freq * 2.5, 0.03) * 3;
    portalSig = portalSig + Resonz.ar(BrownNoise.ar, freq * 0.5, 0.02) * 4;
    portalSig = portalSig * portal * 0.4;
    
    // === LIMINAL (between-space) ===
    liminalSig = SinOsc.ar(freq * 0.5 * LFNoise2.kr(0.1).range(0.98, 1.02));
    liminalSig = liminalSig + (SinOsc.ar(freq * 0.749) * 0.5);  // Slightly off 5th
    liminalSig = liminalSig * LFNoise1.kr(0.3).range(0.5, 1);
    liminalSig = LPF.ar(liminalSig, 500);
    liminalSig = liminalSig * liminal * 0.3;
    
    // === ANCIENT (mystery) ===
    sig = standingSig + portalSig + liminalSig;
    sig = sig + (BPF.ar(BrownNoise.ar, 150, 0.2) * ancient * 0.15);
    sig = LPF.ar(sig, 5000 - (ancient * 2000));
    
    // Spatial resonance
    sig = sig + (CombL.ar(sig, 0.5, 0.23, portal * 2) * portal * 0.2);
    
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.3, 0.15);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] thresholdhum loaded".postln;
