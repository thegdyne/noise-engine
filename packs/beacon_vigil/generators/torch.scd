// TORCH - Warm flame foundation
// Source: Flame acoustics - turbulent combustion as tonal generator
// Role: Bed - sustaining warmth with organic flicker

SynthDef(\forge_beacon_vigil_torch, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                 clockRateBus, clockTrigBus,
                                 midiTrigBus=0, slotIndex=0,
                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                 portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flkr, heat, glow, wind, lift;
    var flicker, breath, core, sub, harmonics;

    // Custom params
    flkr = In.kr(customBus0);  // Flame flicker rate
    heat = In.kr(customBus1);  // Wavefold saturation
    glow = In.kr(customBus2);  // Sustain body
    wind = In.kr(customBus3);  // Breath modulation
    lift = In.kr(customBus4);  // Upper harmonic lift

    // Standard reads
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

    // === DSP: Flame Character ===

    // Flicker: multiple slow random LFOs for organic flame movement
    flicker = LFNoise1.kr(flkr.linexp(0, 1, 0.1, 8)).range(0.85, 1.0);
    flicker = flicker * LFNoise2.kr(flkr.linexp(0, 1, 0.5, 12)).range(0.9, 1.0);

    // Breath: slow undulation like wind on flame
    breath = SinOsc.kr(wind.linexp(0, 1, 0.05, 0.8)).range(1 - (wind * 0.3), 1.0);

    // Core: warm sawtooth with sub-octave
    core = VarSaw.ar(freq * flicker, width: glow.linlin(0, 1, 0.3, 0.7));
    sub = SinOsc.ar(freq * 0.5) * glow.linlin(0, 1, 0.2, 0.5);

    // Wavefold for harmonic heat
    sig = core + (sub * 0.6);
    sig = sig * (1 + (heat * 2));
    sig = sig.fold2(1) * (1 / (1 + heat));

    // Upper harmonics lift - add brightness via pulse
    harmonics = Pulse.ar(freq * 2, 0.3) * lift * 0.2;
    harmonics = LPF.ar(harmonics, freq * 8);
    sig = sig + harmonics;

    // Apply breath modulation
    sig = sig * breath;

    // Gentle chorus for warmth
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.3).range(0.007, 0.012)) * 0.3);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_torch loaded".postln;
