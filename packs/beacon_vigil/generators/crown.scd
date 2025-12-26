// CROWN - Seven-ray metallic resonator
// Source: Liberty's crown - 7 rays representing the 7 seas/continents
// Role: Accent - struck metallic resonance

SynthDef(\forge_beacon_vigil_crown, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                 clockRateBus, clockTrigBus,
                                 midiTrigBus=0, slotIndex=0,
                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                 portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rays, ring, strk, tine, span;
    var exciter, modes, ratios, decays, amps, numRays;

    // Custom params
    rays = In.kr(customBus0);  // Number of rays (1-7)
    ring = In.kr(customBus1);  // Ring time
    strk = In.kr(customBus2);  // Strike hardness
    tine = In.kr(customBus3);  // Brightness
    span = In.kr(customBus4);  // Frequency span

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

    // === DSP: 7-Ray Modal Resonator ===

    // 7 harmonic ratios (metallic/bell-like partials)
    ratios = [1, 1.5, 2.1, 2.9, 3.6, 4.4, 5.3];

    // Strike exciter - harder = brighter impulse
    exciter = Impulse.ar(0) * 0;  // Placeholder, real trigger from env
    exciter = WhiteNoise.ar * EnvGen.ar(
        Env.perc(0.0001, strk.linexp(0, 1, 0.001, 0.02)),
        1
    );
    exciter = exciter + (Impulse.ar(0) * strk.linlin(0, 1, 0.5, 1.0));

    // Apply hardness filtering to exciter
    exciter = HPF.ar(exciter, strk.linexp(0, 1, 200, 2000));
    exciter = LPF.ar(exciter, tine.linexp(0, 1, 3000, 12000));

    // Build 7 resonant modes using Ringz
    modes = ratios.collect({ |ratio, i|
        var modeFreq, modeDecay, modeAmp, active;
        // Spread based on span param
        modeFreq = freq * ratio * (1 + (span * (ratio - 1) * 0.2));
        // Each mode's decay time
        modeDecay = ring.linexp(0, 1, 0.1, 4.0) * (1 / ratio.sqrt);
        // Amplitude rolloff
        modeAmp = (1 / (i + 1).sqrt) * (rays.linlin(0, 1, 1, 7) >= (i + 1)).asInteger;
        Ringz.ar(exciter, modeFreq.min(18000), modeDecay) * modeAmp;
    });

    sig = Mix(modes) * 0.15;

    // Add subtle inharmonic shimmer
    sig = sig + (Ringz.ar(exciter, freq * 7.1, ring.linexp(0, 1, 0.05, 0.5)) * tine * 0.05);

    // Soft clip for density at high levels
    sig = sig.tanh;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    sig = Limiter.ar(sig, 0.95);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_crown loaded".postln;
