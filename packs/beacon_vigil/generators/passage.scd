// PASSAGE - Sweeping crossing movement
// Source: Ocean crossing, ship passage, doppler sweeps
// Role: Motion - movement and transition texture

SynthDef(\forge_beacon_vigil_passage, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var span, rate, turb, wake, wide;
    var sweep, sweepFreq, core, turbulence, wakeTrail;
    var leftSweep, rightSweep;

    // Custom params
    span = In.kr(customBus0);  // Sweep range
    rate = In.kr(customBus1);  // Movement speed
    turb = In.kr(customBus2);  // Turbulence
    wake = In.kr(customBus3);  // Trailing echoes
    wide = In.kr(customBus4);  // Stereo width

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

    // === DSP: Passage Movement ===

    // Primary sweep LFO - slow crossing motion
    sweep = LFTri.kr(rate.linexp(0, 1, 0.02, 0.5));

    // Sweep frequency range (logarithmic sweep)
    sweepFreq = sweep.linexp(-1, 1,
        freq * (1 / (1 + (span * 3))),
        freq * (1 + (span * 3))
    );

    // Core: resonant filtered noise + pitched element
    core = PinkNoise.ar;
    core = BPF.ar(core, sweepFreq, 0.1 + (turb * 0.2)) * 3;
    // Add pitched undertone
    core = core + (SinOsc.ar(sweepFreq * 0.5) * 0.3);
    core = core + (Saw.ar(sweepFreq * 0.25) * 0.15);

    // Turbulence: add irregular modulation
    turbulence = LFNoise1.kr(turb.linexp(0, 1, 0.5, 8)).range(0.8, 1.2);
    core = core * turbulence;
    // Pitch turbulence
    core = core + (BPF.ar(PinkNoise.ar,
        sweepFreq * LFNoise2.kr(turb * 5).range(0.95, 1.05),
        0.15) * turb);

    // Stereo sweep offset for width
    leftSweep = sweepFreq * LFNoise2.kr(0.3).range(1 - (wide * 0.1), 1);
    rightSweep = sweepFreq * LFNoise2.kr(0.35).range(1, 1 + (wide * 0.1));

    sig = [
        BPF.ar(core, leftSweep, 0.15 + (turb * 0.1)) * 2,
        BPF.ar(core, rightSweep, 0.15 + (turb * 0.1)) * 2
    ];

    // Wake: trailing comb echoes
    wakeTrail = CombC.ar(sig, 0.5, 1 / (freq * 2), wake.linlin(0, 1, 0.1, 2));
    wakeTrail = LPF.ar(wakeTrail, 2000);
    sig = sig + (wakeTrail * wake * 0.4);

    // Additional wake allpass diffusion
    sig = AllpassC.ar(sig, 0.2, wake.linlin(0, 1, 0.02, 0.12), wake * 1.5);

    // Soft limit
    sig = sig.tanh;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_passage loaded".postln;
