/*
TB-303 Generator
Roland TB-303 Bassline inspired acid synth

Features:
  - Saw or square oscillator
  - Classic 303 diode ladder filter character
  - Accent (boosts resonance + volume + env depth)
  - Snappy filter envelope with adjustable decay
  - Slide/glide between notes
  - That squelchy acid sound!

Custom params:
  - P1 waveform: 0=saw, 1=square
  - P2 accent: Accent intensity
  - P3 env_mod: Filter envelope depth
  - P4 env_decay: Filter envelope decay time
  - P5 slide: Portamento/glide amount
*/

SynthDef(\tb303, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                    midiTrigBus=0, slotIndex=0,
                    customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var waveform, accent, envMod, envDecay, slide;
    var slidingFreq, saw, square;
    var envTrig, filtEnv, filtFreqMod, envOctaves, accentedRes, accentedAmp;
    
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
    waveform = In.kr(customBus0);
    accent = In.kr(customBus1);
    accent = Lag.kr(accent, 0.02);  // Smooth accent changes to prevent zipper noise
    envMod = In.kr(customBus2);
    envDecay = In.kr(customBus3);
    slide = In.kr(customBus4);
    
    // === SLIDE (Portamento) ===
    // Squared mapping gives more resolution in short glides (the musical sweet spot)
    slidingFreq = Lag.kr(freq, slide.squared * 0.3);
    
    // === VCO ===
    saw = Saw.ar(slidingFreq);
    square = Pulse.ar(slidingFreq, 0.5);
    sig = SelectX.ar(waveform, [saw, square]);
    
    // === FILTER ENVELOPE ===
    // Clock triggers are audio rate - clamp indices for safety
    envTrig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),                                                      // OFF: no trigger
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),  // CLK
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))            // MIDI
    ]);
    
    // 303-style snappy envelope - very fast attack, variable decay
    filtEnv = EnvGen.ar(
        Env.perc(0.001, envDecay, 1, -8),  // Sharp attack, exponential decay
        envTrig
    );
    
    // === ACCENT ===
    // Accent boosts: filter env depth, resonance, and volume
    accentedRes = rq * (1 - (accent * 0.3));  // Lower RQ = more resonance
    accentedAmp = amp * (1 + (accent * 0.5)); // Louder on accent
    
    // === FILTER MODULATION (octave-based) ===
    // Exponential scaling gives musical response across full knob range
    // Max 4 octaves of sweep, accent doubles the depth
    envOctaves = filtEnv * envMod * (1 + (accent * 2)) * 4;
    filtFreqMod = filterFreq * (2 ** envOctaves);
    filtFreqMod = filtFreqMod.clip(20, 18000);
    
    // === 303 FILTER ===
    // Use resonant lowpass - the 303 magic is in the filter!
    // The diode ladder has a distinctive squeaky resonance
    sig = RLPF.ar(sig, filtFreqMod, accentedRes.max(0.05));
    
    // Add some soft saturation for that gritty 303 character
    sig = (sig * 2).tanh * 0.7;
    
    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.05, 0.05);  // Minimal stereo - 303 is mono
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, accentedAmp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ tb303 loaded".postln;
