// VIGIL - Breathing, waiting pad
// Source: Candlelight vigil acoustics, breath rhythms
// Role: Motion - slow pulse texture

SynthDef(\forge_beacon_vigil_vigil, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                 clockRateBus, clockTrigBus,
                                 midiTrigBus=0, slotIndex=0,
                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                 portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var brth, hope, wait, flck, wrmt;
    var breathEnv, flicker, pad, harmonics, breathRate;

    // Custom params
    brth = In.kr(customBus0);  // Breath rate
    hope = In.kr(customBus1);  // Brightness lift
    wait = In.kr(customBus2);  // Sustain between pulses
    flck = In.kr(customBus3);  // Candle flicker
    wrmt = In.kr(customBus4);  // Harmonic warmth

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

    // === DSP: Vigil Breathing ===

    // Breath envelope - smooth in/out cycle
    breathRate = brth.linexp(0, 1, 0.1, 2);
    breathEnv = SinOsc.kr(breathRate, 1.5pi).range(0, 1);
    // Modify shape: longer sustain with wait param
    breathEnv = breathEnv.pow(1 / (1 + (wait * 2)));
    // Smooth transitions
    breathEnv = Lag.kr(breathEnv, 0.1);

    // Candle flicker - irregular tremolo
    flicker = LFNoise1.kr(flck.linexp(0, 1, 2, 15)).range(1 - (flck * 0.3), 1.0);
    flicker = flicker * LFNoise2.kr(flck.linexp(0, 1, 5, 25)).range(0.9, 1.0);

    // Warm pad core - triangle with harmonics
    pad = LFTri.ar(freq) * 0.5;
    pad = pad + (LFTri.ar(freq * 2) * 0.25 * wrmt);
    pad = pad + (SinOsc.ar(freq * 0.5) * 0.3);

    // Additional warmth harmonics
    harmonics = Pulse.ar(freq, wrmt.linlin(0, 1, 0.5, 0.3)) * wrmt * 0.2;
    harmonics = LPF.ar(harmonics, freq * (3 + (hope * 5)));

    // Hope: upper register shimmer
    pad = pad + (SinOsc.ar(freq * 3) * hope * 0.1);
    pad = pad + (SinOsc.ar(freq * 4) * hope * 0.05);

    sig = pad + harmonics;

    // Apply breath and flicker modulation
    sig = sig * breathEnv * flicker;

    // Gentle saturation for presence
    sig = (sig * 1.5).tanh * 0.7;

    // Small stereo movement
    sig = [
        sig + (DelayC.ar(sig, 0.02, SinOsc.kr(0.13).range(0.003, 0.008)) * 0.2),
        sig + (DelayC.ar(sig, 0.02, SinOsc.kr(0.11).range(0.004, 0.009)) * 0.2)
    ];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_vigil loaded".postln;
