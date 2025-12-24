/*
MADNESS Generator
Sanity fracturing - the human mind breaking

Features:
  - Reality fracturing dissonance
  - Maddening whispers
  - Descending spiral
  - Horrific glimpses
  - Mind unraveling chaos

Custom params:
  - P1 fracture: Dissonant intervals, reality breaking
  - P2 whisper: Filtered noise suggesting voices
  - P3 spiral: Descending Shepard-like tones
  - P4 glimpse: Sharp horrific transients
  - P5 unravel: Increasing chaos/randomness

The sound of losing your mind to cosmic truth.
*/

SynthDef(\madness, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var fracture, whisper, spiral, glimpse, unravel;
    var trig;
    var fractureSig, whisperSig, spiralSig, glimpseSig, unravelSig;
    var fractureOsc, fractureMod;
    var whisperNoise, whisperMod;
    var spiralOscs, spiralPhase;
    var glimpseTrig, glimpseHit;
    var unravelOsc, unravelMod;
    
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
    fracture = In.kr(customBus0);
    fracture = Lag.kr(fracture, 0.05);
    whisper = In.kr(customBus1);
    whisper = Lag.kr(whisper, 0.05);
    spiral = In.kr(customBus2);
    glimpse = In.kr(customBus3);
    unravel = In.kr(customBus4);
    unravel = Lag.kr(unravel, 0.05);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === FRACTURE (dissonant reality break) ===
    // Tritones, minor 2nds, and beating frequencies
    fractureMod = LFNoise2.kr(0.5).range(0.98, 1.02);
    fractureOsc = SinOsc.ar(freq * fractureMod);
    // Tritone (the devil's interval)
    fractureOsc = fractureOsc + (SinOsc.ar(freq * 1.414 * fractureMod) * 0.5);  // sqrt(2) ≈ tritone
    // Minor second cluster
    fractureOsc = fractureOsc + (SinOsc.ar(freq * 1.059 * fractureMod) * 0.4);  // Minor 2nd
    fractureOsc = fractureOsc + (SinOsc.ar(freq * 0.944 * fractureMod) * 0.4);  // Minor 2nd down
    // Beating
    fractureOsc = fractureOsc + (SinOsc.ar(freq * 1.01) * SinOsc.ar(freq * 0.99) * 0.3);
    fractureSig = fractureOsc * fracture * 0.4;
    
    // === WHISPER (maddening voices) ===
    // Filtered noise shaped like speech
    whisperNoise = PinkNoise.ar;
    whisperMod = LFNoise2.kr(3).range(0.5, 1.5);  // Fast modulation
    whisperSig = BPF.ar(whisperNoise, 800 * whisperMod, 0.3);
    whisperSig = whisperSig + (BPF.ar(whisperNoise, 1500 * whisperMod, 0.4) * 0.6);
    whisperSig = whisperSig + (BPF.ar(whisperNoise, 2500 * whisperMod, 0.5) * 0.3);
    // Amplitude shaping like speech rhythm
    whisperSig = whisperSig * LFNoise1.kr(8).range(0.2, 1);
    whisperSig = whisperSig * whisper * 0.4;
    
    // === SPIRAL (descending Shepard tone) ===
    // Multiple octaves of slowly descending pitch
    spiralPhase = LFSaw.kr(0.1).range(0, 1);  // Continuous descent
    spiralOscs = SinOsc.ar(freq * (2 ** (spiralPhase))) * (1 - spiralPhase);
    spiralOscs = spiralOscs + (SinOsc.ar(freq * 2 * (2 ** (spiralPhase))) * spiralPhase * (1 - spiralPhase) * 2);
    spiralOscs = spiralOscs + (SinOsc.ar(freq * 0.5 * (2 ** (spiralPhase))) * spiralPhase);
    // Triggered descent on clock/MIDI
    spiralOscs = spiralOscs + (
        SinOsc.ar(freq * (1 + EnvGen.ar(Env.perc(0.01, 2, 1, 4), trig))) *
        EnvGen.ar(Env.perc(0.1, 2), trig) * 0.5
    );
    spiralSig = spiralOscs * spiral * 0.5;
    
    // === GLIMPSE (horrific transients) ===
    // Sharp dissonant stabs
    glimpseTrig = trig + Dust.ar(glimpse * 3);  // Clock + random
    glimpseHit = SinOsc.ar(freq * 1.5, SinOsc.ar(freq * 2.33) * 4);  // FM stab
    glimpseHit = glimpseHit + (Pulse.ar(freq * 0.5, 0.1) * 0.5);  // Harsh pulse
    glimpseHit = glimpseHit * EnvGen.ar(Env.perc(0.001, 0.08), glimpseTrig);
    glimpseSig = HPF.ar(glimpseHit, 200) * glimpse;
    
    // === UNRAVEL (chaos) ===
    // Increasingly random/chaotic sounds
    unravelMod = LFNoise0.kr(5 + (unravel * 20));  // Faster randomness at higher unravel
    unravelOsc = SinOsc.ar(freq * unravelMod.range(0.5, 2));
    // Sample & hold pitch chaos
    unravelOsc = unravelOsc + (
        SinOsc.ar(Latch.kr(LFNoise0.kr(10), Impulse.kr(8)) * freq * 2) * 0.3
    );
    // Glitchy noise bursts
    unravelOsc = unravelOsc + (
        WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.02), Dust.ar(unravel * 30)) * 0.5
    );
    unravelSig = unravelOsc * unravel * 0.4;
    
    // === MIX ===
    sig = fractureSig + whisperSig + spiralSig + glimpseSig + unravelSig;
    
    // Harsh clipping for disturbing quality
    sig = (sig * 1.5).clip2(1);
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.3, 0.35);  // Unsettling movement
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ madness loaded".postln;
