// AURORA - Spectral aurora shimmer
// Additive synthesis with drifting phase interference

SynthDef(\forge_glacialis_aurora, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bands, drift, glow, shift, veil;
    var partials, driftLFOs, shiftMod;

    // Theme params
    bands = In.kr(customBus0);     // Band density
    drift = In.kr(customBus1);     // Phase drift rate
    glow = In.kr(customBus2);      // Brightness
    shift = In.kr(customBus3);     // Spectral shift
    veil = In.kr(customBus4);      // Diffusion

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

    // Spectral shift modulation
    shiftMod = SinOsc.kr(drift.linexp(0, 1, 0.02, 0.15)).range(1, 1 + (shift * 0.1));

    // Additive partials with phase drift - 8 fixed partials with crossfade
    partials = Mix.fill(8, { |i|
        var ratio, ampScale, driftRate, phase;
        ratio = (i + 1) * shiftMod;
        ampScale = (bands * 8 - i).clip(0, 1) * ((i + 1).reciprocal ** (1 - glow));
        driftRate = drift.linexp(0, 1, 0.01, 0.1) * (i + 1).sqrt * 0.3;
        phase = SinOsc.kr(driftRate, i * 0.7).range(0, 2pi);
        SinOsc.ar(freq * ratio, phase) * ampScale
    });

    sig = partials * 0.3;

    // Veil/diffusion via chorus
    sig = sig + (DelayC.ar(sig, 0.05,
        SinOsc.kr(veil.linexp(0, 1, 0.1, 2), 0).range(0.005, 0.02)
    ) * veil * 0.5);

    // Stereo shimmer
    sig = [
        sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.13).range(0.003, 0.015)) * 0.3),
        sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.17).range(0.004, 0.018)) * 0.3)
    ];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_glacialis_aurora loaded".postln;
