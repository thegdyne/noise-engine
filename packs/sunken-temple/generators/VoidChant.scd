/*
VOIDCHANT Generator
Ghostly spectral vocals echoing through ruins

Features:
  - Formant-based vocal tones
  - Hollow resonant harmonics
  - Drifting pitch
  - Ethereal chorus

Custom params:
  - P1 choir: Voice count/blend
  - P2 hollow: Formant depth
  - P3 drift: Pitch wandering
  - P4 ghost: Spectral doubling
  - P5 prayer: Ritual pulse
*/

SynthDef(\voidchant, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var choir, hollow, drift, ghost, prayer;
    var trig, voiceSig, formants, driftMod, ghostSig, prayerMod;
    
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
    choir = In.kr(customBus0);
    choir = Lag.kr(choir, 0.1);
    hollow = In.kr(customBus1);
    hollow = Lag.kr(hollow, 0.1);
    drift = In.kr(customBus2);
    drift = Lag.kr(drift, 0.2);
    ghost = In.kr(customBus3);
    ghost = Lag.kr(ghost, 0.1);
    prayer = In.kr(customBus4);
    prayer = Lag.kr(prayer, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Pitch drift
    driftMod = LFNoise2.kr(0.3 + (drift * 0.5)).range(1 - (drift * 0.03), 1 + (drift * 0.03));
    
    // Prayer rhythm modulation
    prayerMod = LFTri.kr(0.5 + (prayer * 0.5)).range(0.6, 1) * (1 - prayer) + prayer;
    
    // === VOICE SOURCE ===
    // Pulse wave for vocal-like harmonics
    voiceSig = Pulse.ar(freq * driftMod, 0.3 + (LFNoise1.kr(2).range(0, 0.2)));
    voiceSig = voiceSig + (Pulse.ar(freq * 1.002 * driftMod, 0.35) * choir * 0.5);
    voiceSig = voiceSig + (Pulse.ar(freq * 0.998 * driftMod, 0.25) * choir * 0.5);
    
    // === FORMANTS (vowel-like) ===
    // "Ah" / "Oh" formants
    formants = BPF.ar(voiceSig, 600 * (1 + (hollow * 0.5)), 0.15) * 2;
    formants = formants + (BPF.ar(voiceSig, 1000, 0.2) * (1 - hollow));
    formants = formants + (BPF.ar(voiceSig, 2500, 0.3) * 0.5);
    
    // Hollow depth - shifts formants down
    formants = formants + (BPF.ar(voiceSig, 300, 0.1) * hollow * 2);
    
    voiceSig = formants * 0.5;
    
    // === GHOST (ethereal doubling) ===
    ghostSig = DelayL.ar(voiceSig, 0.1, LFNoise2.kr(0.5).range(0.02, 0.05));
    ghostSig = ghostSig + DelayL.ar(voiceSig, 0.1, LFNoise2.kr(0.4).range(0.03, 0.07));
    ghostSig = HPF.ar(ghostSig, 400);
    voiceSig = voiceSig + (ghostSig * ghost * 0.5);
    
    // === REVERB (spectral space) ===
    voiceSig = voiceSig + (CombL.ar(voiceSig, 0.5, 0.13, 3) * 0.3);
    voiceSig = voiceSig + (CombL.ar(voiceSig, 0.5, 0.19, 2.5) * 0.25);
    
    // Prayer modulation
    voiceSig = voiceSig * prayerMod;
    
    sig = voiceSig * 0.4;
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.35, 0.15);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ voidchant loaded".postln;
