/*
CTHULHU Generator
The Great Old One - massive eldritch presence

Features:
  - Subsonic mass (felt more than heard)
  - Non-Euclidean harmonics (impossible intervals)
  - Psychic dread throb
  - Ancient vocalization
  - Dream transmission shimmer

Custom params:
  - P1 mass: Sub-bass presence and weight
  - P2 geometry: Impossible harmonic relationships
  - P3 dread: Low frequency anxiety throb
  - P4 voice: Eldritch vocalization
  - P5 dream: Ethereal transmission shimmer

Primarily continuous/drone with optional triggering for emphasis.
*/

SynthDef(\cthulhu, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var mass, geometry, dread, voice, dream;
    var trig, trigEnv;
    var massSig, geoSig, dreadSig, voiceSig, dreamSig;
    var subOsc, subLFO;
    var geoPartials, geoMod;
    var dreadLFO, dreadOsc;
    var voiceFormant, voiceMod;
    var dreamShimmer, dreamMod;
    
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
    mass = In.kr(customBus0);
    mass = Lag.kr(mass, 0.1);
    geometry = In.kr(customBus1);
    geometry = Lag.kr(geometry, 0.1);
    dread = In.kr(customBus2);
    dread = Lag.kr(dread, 0.1);
    voice = In.kr(customBus3);
    voice = Lag.kr(voice, 0.1);
    dream = In.kr(customBus4);
    dream = Lag.kr(dream, 0.1);
    
    // === TRIGGER (for emphasis swells) ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    trigEnv = EnvGen.ar(Env.perc(0.5, 4, 1, -4), trig) * 0.5 + 0.5;
    
    // === MASS (subsonic presence) ===
    // Deep sub oscillator with slow movement
    subLFO = LFNoise2.kr(0.1).range(0.97, 1.03);
    subOsc = SinOsc.ar(freq * 0.25 * subLFO);  // Two octaves below
    subOsc = subOsc + (SinOsc.ar(freq * 0.5 * subLFO) * 0.5);  // One octave below
    // Add subsonic rumble
    subOsc = subOsc + (SinOsc.ar(freq * 0.125) * 0.3);  // Three octaves below
    massSig = subOsc * mass * trigEnv;
    
    // === GEOMETRY (non-Euclidean harmonics) ===
    // Impossible intervals - irrational ratios that shift
    geoMod = LFNoise2.kr(0.15).range(0.98, 1.02);
    geoPartials = SinOsc.ar(freq * 1.618 * geoMod) * 0.4;  // Golden ratio
    geoPartials = geoPartials + (SinOsc.ar(freq * pi * geoMod) * 0.3);  // Pi ratio
    geoPartials = geoPartials + (SinOsc.ar(freq * sqrt(2) * geoMod) * 0.25);  // Root 2
    geoPartials = geoPartials + (SinOsc.ar(freq * 2.718 * geoMod) * 0.2);  // e ratio
    // Ring mod for alien texture
    geoPartials = geoPartials * SinOsc.ar(freq * 0.127);
    geoSig = geoPartials * geometry * trigEnv;
    
    // === DREAD (psychic anxiety throb) ===
    // Infrasound-range pulsing
    dreadLFO = LFTri.kr(0.3 + (dread * 0.4)).range(0.3, 1);  // Slow throb
    dreadOsc = SinOsc.ar(freq * 0.5) * dreadLFO;
    // Add beating frequencies for unease
    dreadOsc = dreadOsc + (SinOsc.ar(freq * 0.501) * 0.5 * dreadLFO);  // Slow beat
    dreadOsc = dreadOsc + (SinOsc.ar(freq * 0.498) * 0.5 * dreadLFO);  // Counter beat
    dreadSig = dreadOsc * dread;
    
    // === VOICE (eldritch vocalization) ===
    // Formant-like drone suggesting impossible speech
    voiceMod = LFNoise2.kr(0.2).range(0.9, 1.1);
    voiceFormant = Formant.ar(freq * 0.5, freq * 2.3 * voiceMod, freq * 0.8);
    voiceFormant = voiceFormant + (Formant.ar(freq * 0.5, freq * 3.7 * voiceMod, freq) * 0.5);
    // Add growling undertone
    voiceFormant = voiceFormant + (LFPulse.ar(freq * 0.25, 0, 0.3) * 0.3);
    voiceSig = LPF.ar(voiceFormant, 2000) * voice * 0.5 * trigEnv;
    
    // === DREAM (transmission shimmer) ===
    // High ethereal tones suggesting psychic contact
    dreamMod = LFNoise2.kr(0.4);
    dreamShimmer = SinOsc.ar(freq * 4 * (1 + (dreamMod * 0.02))) * 0.3;
    dreamShimmer = dreamShimmer + (SinOsc.ar(freq * 5.03) * 0.2);  // Slight detune
    dreamShimmer = dreamShimmer + (SinOsc.ar(freq * 6.28) * 0.15);  // 2*pi
    // Tremolo for otherworldly quality
    dreamShimmer = dreamShimmer * LFTri.kr(3 + (dream * 4)).range(0.5, 1);
    dreamSig = HPF.ar(dreamShimmer, 1000) * dream * 0.4;
    
    // === MIX ===
    sig = massSig + geoSig + dreadSig + voiceSig + dreamSig;
    
    // Soft saturation for density
    sig = (sig * 1.5).tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.08, 0.3);  // Wide but slow movement
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ cthulhu loaded".postln;
