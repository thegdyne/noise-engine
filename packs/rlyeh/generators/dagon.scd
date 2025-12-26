/*
DAGON Generator
Ancient sea god - ritual worship from the deep

Features:
  - Deep ritual drums
  - Inhuman chanting
  - Tidal pulse rhythm
  - Ancient resonance
  - Summoning crescendo

Custom params:
  - P1 ritual: Drum pulse intensity
  - P2 chant: Deep One voices
  - P3 tide: Tidal rhythm modulation
  - P4 ancient: Old resonance tones
  - P5 summon: Summoning intensity buildup

The sound of forbidden worship.
*/

SynthDef(\dagon, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                    midiTrigBus=0, slotIndex=0,
                    customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ritual, chant, tide, ancient, summon;
    var trig, tideLFO, summonMod;
    var ritualSig, chantSig, tideSig, ancientSig, summonSig;
    var drumOsc, drumEnv;
    var chantOsc, chantMod;
    var tideNoise, tideMod;
    var ancientOsc, ancientLFO;
    var summonOsc, summonEnv;
    
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
    ritual = In.kr(customBus0);
    chant = In.kr(customBus1);
    chant = Lag.kr(chant, 0.05);
    tide = In.kr(customBus2);
    tide = Lag.kr(tide, 0.1);
    ancient = In.kr(customBus3);
    ancient = Lag.kr(ancient, 0.1);
    summon = In.kr(customBus4);
    summon = Lag.kr(summon, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Tidal rhythm affects everything
    tideLFO = LFTri.kr(0.08).range(0.7, 1);  // Very slow tide
    
    // Summoning intensity modulates multiple elements
    summonMod = summon * 0.5 + 0.5;
    
    // === RITUAL (deep drums) ===
    // Triggered low drum hits
    drumEnv = EnvGen.ar(Env.perc(0.01, 0.3 * summonMod, 1, -6), trig);
    drumOsc = SinOsc.ar(freq * 0.5 * tideLFO);
    // Pitch drop like a massive drum
    drumOsc = drumOsc + (
        SinOsc.ar(freq * 0.5 * (1 + (drumEnv * 0.5))) * drumEnv
    );
    // Body resonance
    drumOsc = drumOsc + (LPF.ar(BrownNoise.ar, 100) * drumEnv * 0.5);
    ritualSig = drumOsc * drumEnv * ritual;
    
    // === CHANT (inhuman voices) ===
    // Formant synthesis for alien vocalization
    chantMod = LFNoise2.kr(0.5 + (chant * 1.5)).range(0.9, 1.1);
    chantOsc = Formant.ar(freq * 0.25 * chantMod, freq * 1.5, freq * 0.5);
    chantOsc = chantOsc + (Formant.ar(freq * 0.25, freq * 2.2 * chantMod, freq * 0.8) * 0.5);
    // Multiple "voices"
    chantOsc = chantOsc + (Formant.ar(freq * 0.26, freq * 1.8, freq * 0.6) * 0.4);
    // Rhythmic chanting pattern
    chantOsc = chantOsc * LFPulse.kr(0.5 * summonMod, 0, 0.6).lag(0.1);
    chantSig = LPF.ar(chantOsc, 1500) * chant * 0.4 * tideLFO;
    
    // === TIDE (rhythmic pulse) ===
    // Filtered noise with tidal modulation
    tideNoise = BrownNoise.ar;
    tideMod = tideLFO.squared;  // More pronounced tide shape
    tideSig = LPF.ar(tideNoise, 150 + (tideMod * 200));
    tideSig = tideSig + (BPF.ar(tideNoise, 80, 0.5) * tideMod);
    tideSig = tideSig * tide * tideMod * 0.5;
    
    // === ANCIENT (old resonance) ===
    // Slowly shifting inharmonic partials
    ancientLFO = LFNoise2.kr(0.15).range(0.98, 1.02);
    ancientOsc = SinOsc.ar(freq * 1.17 * ancientLFO) * 0.4;  // Non-integer ratio
    ancientOsc = ancientOsc + (SinOsc.ar(freq * 2.43 * ancientLFO) * 0.3);
    ancientOsc = ancientOsc + (SinOsc.ar(freq * 3.89 * ancientLFO) * 0.2);
    // Ancient "bell" quality
    ancientOsc = ancientOsc + (
        SinOsc.ar(freq * 5.11, SinOsc.ar(freq * 0.5) * 0.5) * 0.15
    );
    ancientSig = ancientOsc * ancient * 0.4 * tideLFO;
    
    // === SUMMON (crescendo) ===
    // Building intensity on trigger
    summonEnv = EnvGen.ar(Env.perc(0.5, 3, 1, -2), trig);
    summonOsc = SinOsc.ar(freq * (1 + (summonEnv * 0.5 * summon)));
    summonOsc = summonOsc + (Saw.ar(freq * 0.5 * (1 + (summonEnv * 0.3))) * 0.3);
    // Rising harmonics
    summonOsc = summonOsc + (
        SinOsc.ar(freq * 2 * (1 + (summonEnv * summon))) * summonEnv * 0.4
    );
    summonOsc = summonOsc + (
        SinOsc.ar(freq * 3 * (1 + (summonEnv * summon * 0.5))) * summonEnv.squared * 0.3
    );
    summonSig = summonOsc * summonEnv * summon;
    
    // === MIX ===
    sig = ritualSig + chantSig + tideSig + ancientSig + summonSig;
    
    // Saturation for intensity
    sig = (sig * (1 + (summon * 0.5))).tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.12, 0.2);  // Cavernous space
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] dagon loaded".postln;
