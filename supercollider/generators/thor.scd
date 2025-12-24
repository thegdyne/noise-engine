/*
THOR Generator
Blacksmith's anvil - hammer striking metal with forge atmosphere

Features:
  - Weighted hammer impact with pitch drop
  - Metallic anvil ring (FM inharmonics)
  - Roaring forge fire (continuous, ducks on impact)
  - Bellows breathing (rhythmic whoosh)
  - Spark spray on impact

Custom params:
  - P1 hammer: Hammer weight (affects pitch, decay, impact depth)
  - P2 anvil: Metallic ring amount
  - P3 fire: Continuous forge fire level
  - P4 bellows: Rhythmic bellows breathing level
  - P5 spark: Bright transient sparks on impact

Note: Fire and Bellows are continuous/drone elements that duck on impact.
      Hammer, Anvil, Spark are triggered by CLK/MIDI.
*/

SynthDef(\thor, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                   filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                   midiTrigBus=0, slotIndex=0,
                   customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var hammer, anvil, fire, bellows, spark;
    var trig, impactEnv, bedDuck;
    var hammerSig, anvilSig, fireSig, bellowsSig, sparkSig;
    var pitchEnv, hammerBody, hammerDecay, hammerPitch, hammerSweep;
    var anvilPartials, anvilEnv;
    var fireNoise, fireLFO;
    var bellowsNoise, bellowsLFO;
    var sparkEnv, sparkNoise;
    
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
    hammer = In.kr(customBus0);
    anvil = In.kr(customBus1);
    fire = In.kr(customBus2);
    fire = Lag.kr(fire, 0.05);  // Smooth continuous param
    bellows = In.kr(customBus3);
    bellows = Lag.kr(bellows, 0.05);
    spark = In.kr(customBus4);
    
    // === TRIGGER ===
    // Clamp indices for safety
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Impact envelope for bed ducking
    impactEnv = EnvGen.ar(Env.perc(0.001, 0.15, 1, -4), trig);
    bedDuck = 1 - (impactEnv * 0.3);  // Duck bed by 30% on impact
    
    // === HAMMER (weighted impact) ===
    // Exponential mapping per aspect - feels like "mass" across full range
    // Heavier = lower pitch, deeper sweep, longer decay
    hammerPitch = freq * hammer.linexp(0, 1, 1, 0.6);         // 0-40% pitch drop
    hammerSweep = hammer.pow(1.4) * 2.5;                       // Power curve for sweep depth
    hammerDecay = hammer.linexp(0, 1, 0.12, 0.7);              // 120ms to 700ms
    
    pitchEnv = EnvGen.ar(
        Env.perc(0.001, 0.012 + (hammer * 0.05), 1, -8),  // 12-62ms sweep time
        trig
    );
    hammerBody = SinOsc.ar(hammerPitch + (pitchEnv * freq * hammerSweep));
    hammerSig = hammerBody * EnvGen.ar(Env.perc(0.001, hammerDecay, 1, -6), trig);
    hammerSig = hammerSig * hammer;  // True zero at 0 for "anvil only" patches
    
    // === ANVIL (metallic ring) ===
    // FM synthesis with inharmonic ratios for metallic character
    anvilEnv = EnvGen.ar(Env.perc(0.001, 0.3 + (anvil * 0.5), 1, -4), trig);
    // Main body with FM for metallic timbre
    anvilPartials = SinOsc.ar(freq * 2.76, SinOsc.ar(freq * 1.41) * 2) * 0.4;
    // Higher partials with faster decay (metal resonance character)
    anvilPartials = anvilPartials + (SinOsc.ar(freq * 4.13) * 0.25 *
        EnvGen.ar(Env.perc(0.001, 0.15), trig));
    anvilPartials = anvilPartials + (SinOsc.ar(freq * 5.87) * 0.15 *
        EnvGen.ar(Env.perc(0.001, 0.08), trig));
    // Bright "chink" transient
    anvilPartials = anvilPartials + (SinOsc.ar(freq * 7.2) * 0.3 *
        EnvGen.ar(Env.perc(0.0005, 0.02), trig));
    // Extra high partial for more metallic harshness
    anvilPartials = anvilPartials + (SinOsc.ar(freq * 11.9) * 0.12 *
        EnvGen.ar(Env.perc(0.0005, 0.01), trig));
    anvilSig = anvilPartials * anvilEnv * anvil;
    
    // === FIRE (continuous forge roar) ===
    // Single noise source, multiple bandpass filters with slow movement
    fireNoise = WhiteNoise.ar;
    fireLFO = LFNoise2.kr(0.3).range(0.7, 1.3);  // Slow flickering
    fireSig = BPF.ar(fireNoise, 300 * fireLFO, 0.7) * 0.5;           // Low rumble
    fireSig = fireSig + (BPF.ar(fireNoise, 700 * fireLFO, 0.5) * 0.35);   // Mid crackle
    fireSig = fireSig + (BPF.ar(fireNoise, 1400 * fireLFO, 0.4) * 0.2);   // Upper hiss
    fireSig = fireSig * fire * 0.5 * bedDuck;  // Apply ducking
    
    // === BELLOWS (rhythmic breathing) ===
    // Pink noise through lowpass with slow amplitude modulation
    bellowsNoise = PinkNoise.ar;
    bellowsLFO = LFTri.kr(0.25).range(0, 1);  // ~4 second breath cycle
    bellowsSig = LPF.ar(bellowsNoise, 250 + (bellowsLFO * 250));  // Filter opens with breath
    bellowsSig = bellowsSig * bellowsLFO.squared * bellows * 0.6 * bedDuck;  // Squared + ducking
    
    // === SPARK (bright transient spray) ===
    // Single noise source, HPF'd and scattered
    sparkNoise = WhiteNoise.ar;
    sparkEnv = EnvGen.ar(
        Env.perc(0.001, 0.015 + (0.02 * TRand.ar(0, 1, trig))),  // Randomized decay
        trig
    );
    sparkSig = HPF.ar(sparkNoise, 3000) * sparkEnv;
    // Secondary sparks with delays for scatter effect
    sparkSig = sparkSig + (HPF.ar(sparkNoise, 4500) *
        EnvGen.ar(Env.perc(0.001, 0.012), TDelay.ar(trig, 0.008)) * 0.5);
    sparkSig = sparkSig + (HPF.ar(sparkNoise, 6000) *
        EnvGen.ar(Env.perc(0.001, 0.008), TDelay.ar(trig, 0.018)) * 0.35);
    // Extended third delay for more obvious spray
    sparkSig = sparkSig + (HPF.ar(sparkNoise, 6500) *
        EnvGen.ar(Env.perc(0.001, 0.006), TDelay.ar(trig, 0.045)) * 0.25);
    // Long tail spark at low level
    sparkSig = sparkSig + (HPF.ar(sparkNoise, 7500) *
        EnvGen.ar(Env.perc(0.001, 0.008), TDelay.ar(trig, 0.065)) * 0.15);
    sparkSig = sparkSig * spark;
    
    // === MIX ===
    sig = hammerSig + anvilSig + fireSig + bellowsSig + sparkSig;
    
    // Soft limiting to tame combined levels
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.15, 0.2);  // Stereo width for forge ambience
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ thor loaded".postln;
