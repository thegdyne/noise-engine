// Crystal Tone - Perfect crystal clarity
// Pure FM synthesis for bell-like, crystalline melody

SynthDef(\forge_dew_sphere_crystal_tone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pure, glow, round, shine, warm;
    var fund, harm2, harm3, shineOsc, warmOsc;
    var modIndex, modFreq;

    // Standard bus reads
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

    // Theme params
    pure = In.kr(customBus0);       // Purity
    glow = In.kr(customBus1);       // Inner warmth/brightness
    round = In.kr(customBus2);      // Roundness
    shine = In.kr(customBus3);      // High sparkle
    warm = In.kr(customBus4);       // Low warmth

    // FM modulation - purity controls complexity
    modIndex = (1 - pure).linexp(0, 1, 0.5, 4);
    modFreq = freq * (2 + (glow * 0.5));

    // Fundamental with subtle FM
    fund = SinOsc.ar(freq + (SinOsc.ar(modFreq) * modIndex * freq * 0.1));

    // Second harmonic - round controls amount
    harm2 = SinOsc.ar(freq * 2 + (SinOsc.ar(modFreq * 2) * modIndex * 0.5 * freq)) * round * 0.4;

    // Third harmonic - adds clarity
    harm3 = SinOsc.ar(freq * 3) * pure * 0.2;

    // Shine - high frequency shimmer
    shineOsc = SinOsc.ar(freq * 5 + (SinOsc.ar(freq * 7) * shine * 50)) * shine * 0.15;

    // Warm sub layer
    warmOsc = SinOsc.ar(freq * 0.5) * warm * 0.25;

    // Mix harmonics
    sig = fund + harm2 + harm3 + shineOsc + warmOsc;

    // Glow - subtle saturation for inner warmth
    sig = (sig * (1 + (glow * 0.3))).tanh;

    // Round shaping - gentle lowpass for rounder tone
    sig = LPF.ar(sig, round.linexp(0, 1, 8000, 20000));

    // Normalize
    sig = sig * 0.5;

    // Output chain
    sig = ~stereoSpread.(sig, 0.1, 0.15);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_crystal_tone loaded".postln;
