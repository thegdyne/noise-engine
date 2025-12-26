// ============================================================================
// LEVIATHAN: Tidal Breath
// Role: Motion - the rhythmic breathing of ocean and creature
// 
// LNG (Lung)     - Breath depth, how full the inhalation
// RHY (Rhythm)   - Breathing rate modulation
// WET (Wet)      - Water in the breath, filtered noise
// CAV (Cavity)   - Body cavity resonance size
// EXH (Exhale)   - Exhale intensity, the release
// ============================================================================

SynthDef(\forge_leviathan_tidal_breath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var lung, rhythm, wet, cavity, exhale;
    var breathCycle, inhale, exhalePhase;
    var bodyResonance, wetNoise, cavityFilter;
    var breathMod, pitchMod;

    // Read standard params
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

    // === THEMED PARAMS ===
    lung = In.kr(customBus0).linlin(0, 1, 0.3, 1.0);
    rhythm = In.kr(customBus1).linexp(0, 1, 0.05, 0.5);
    wet = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    cavity = In.kr(customBus3).linexp(0, 1, 0.5, 2.0);
    exhale = In.kr(customBus4).linlin(0, 1, 0.3, 1.0);

    // === BREATH CYCLE ===
    // Asymmetric breathing - slow inhale, quicker exhale
    breathCycle = LFTri.kr(rhythm).range(0, 1);
    inhale = (breathCycle * 2).clip(0, 1);  // First half
    exhalePhase = ((breathCycle - 0.5) * 2 * exhale).clip(0, 1);  // Second half

    // Breath modulates amplitude
    breathMod = (inhale * lung) + (exhalePhase * 0.3);
    
    // Subtle pitch movement with breath
    pitchMod = 1 + (breathCycle * 0.02 * lung);

    // === BODY RESONANCE (filtered oscillators) ===
    bodyResonance = SinOsc.ar(freq * pitchMod / cavity);
    bodyResonance = bodyResonance + (SinOsc.ar(freq * 2 * pitchMod / cavity) * 0.3);
    bodyResonance = bodyResonance + (SinOsc.ar(freq * 0.5 * pitchMod) * lung * 0.4);
    
    // Add formant-like resonances for "body"
    bodyResonance = bodyResonance + (Formant.ar(freq / cavity, freq * 2, freq * 4) * 0.2);

    // === WET NOISE (water in breath) ===
    wetNoise = PinkNoise.ar * wet;
    wetNoise = BPF.ar(wetNoise, freq * 2 * pitchMod, 0.3);
    wetNoise = wetNoise + (BrownNoise.ar * wet * 0.3);
    wetNoise = LPF.ar(wetNoise, 1000 + (breathCycle * 2000));
    wetNoise = wetNoise * breathMod;

    // === CAVITY RESONANCE ===
    cavityFilter = Resonz.ar(bodyResonance + wetNoise, freq * cavity, 0.1) * 2;
    cavityFilter = cavityFilter + Resonz.ar(bodyResonance, freq * 1.5 * cavity, 0.15);

    // === MIX ===
    sig = bodyResonance * 0.5 + wetNoise * 0.4 + cavityFilter * 0.3;
    sig = sig * breathMod;

    // Soft saturation
    sig = (sig * 1.5).tanh * 0.6;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, rhythm, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_leviathan_tidal_breath loaded".postln;
