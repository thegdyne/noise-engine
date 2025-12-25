// ============================================================================
// WAX_PRINT: Bold Motif
// Role: Bed - geometric patterns as sound, repeating shapes
// 
// GEO (Geometry) - Pattern complexity, harmonic layers
// REP (Repeat)   - Motif repetition rate
// CON (Contrast) - Light/dark, loud/soft dynamics
// SYM (Symmetry) - Pattern balance, phase relationships
// INK (Ink)      - Color saturation, timbral richness
// ============================================================================

SynthDef(\forge_wax_print_bold_motif, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var geometry, repeat, contrast, symmetry, ink;
    var layer1, layer2, layer3, patternMod;

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

    geometry = In.kr(customBus0).linlin(0, 1, 1, 5).round;
    repeat = In.kr(customBus1).linexp(0, 1, 0.25, 4);
    contrast = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    symmetry = In.kr(customBus3).linlin(0, 1, 0.0, 1.0);
    ink = In.kr(customBus4).linlin(0, 1, 0.0, 1.0);

    // Pattern modulation (repeating motif)
    patternMod = LFTri.kr(repeat).range(0.8, 1.2);
    patternMod = patternMod * (1 + (LFPulse.kr(repeat * 2).range(0, contrast * 0.3)));

    // Layer 1: Foundation (simple geometry)
    layer1 = SinOsc.ar(freq * patternMod) * 0.4;
    layer1 = layer1 + (SinOsc.ar(freq * 2 * patternMod) * 0.2);

    // Layer 2: Complexity (more harmonics based on geometry)
    layer2 = Pulse.ar(freq * patternMod, 0.5 - (geometry * 0.08)) * geometry * 0.1;
    layer2 = layer2 + (Saw.ar(freq * 1.5 * patternMod) * (geometry / 5) * 0.15);
    layer2 = LPF.ar(layer2, freq * (2 + geometry));

    // Layer 3: Symmetry (phase-related doubling)
    layer3 = SinOsc.ar(freq * patternMod, symmetry * pi) * symmetry * 0.3;
    layer3 = layer3 + (SinOsc.ar(freq * 2 * patternMod, symmetry * pi * 0.5) * symmetry * 0.2);

    // Ink saturation
    sig = layer1 + layer2 + layer3;
    sig = sig + (sig.clip(-0.3, 0.3) * ink * 2);  // Soft saturation adds color
    sig = sig + (Saw.ar(freq * 3) * ink * 0.1);

    // Contrast dynamics
    sig = sig * (1 + (LFPulse.kr(repeat).range(-contrast * 0.3, contrast * 0.3)));

    sig = (sig * 1.5).tanh * 0.5;

    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_wax_print_bold_motif loaded".postln;
