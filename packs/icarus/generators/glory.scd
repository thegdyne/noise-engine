// Glory — blinding beauty of the sun up close
// Role: accent

SynthDef(\forge_icarus_glory, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                 clockRateBus, clockTrigBus,
                                 midiTrigBus=0, slotIndex=0,
                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                 portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var blind, awe, rays, divine, moment;
    var light, harmonics, shimmer, frozen, numRays;

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

    // Theme params
    blind = In.kr(customBus0).linlin(0, 1, 0.3, 1.0);     // Overall brightness
    awe = In.kr(customBus1).linlin(0, 1, 0.5, 6);         // FM index (harmonic richness)
    rays = In.kr(customBus2);                              // Ray count (discrete)
    divine = In.kr(customBus3).linlin(0, 1, 0.0, 0.5);    // Upper shimmer
    moment = In.kr(customBus4).linlin(0, 1, 1, 0.1);      // Time dilation (mod speed)

    // Number of light rays (2-8)
    numRays = rays.linlin(0, 1, 2, 8).round;

    // Core blinding light - FM synthesis
    light = SinOsc.ar(freq, SinOsc.ar(freq * 2.01, 0, awe));

    // Harmonic rays - additive partials
    harmonics = SinOsc.ar(freq * 2, 0, 0.3);
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, 0.2 * (numRays > 2));
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, 0.15 * (numRays > 3));
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, 0.12 * (numRays > 4));
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, 0.1 * (numRays > 5));
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, 0.08 * (numRays > 6));
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, 0.06 * (numRays > 7));

    // Divine shimmer - detuned high partials
    shimmer = SinOsc.ar(freq * 4 * LFNoise2.kr(moment, 0.02, 1), 0, divine);
    shimmer = shimmer + SinOsc.ar(freq * 6 * LFNoise2.kr(moment * 1.1, 0.02, 1), 0, divine * 0.7);

    // Combine in blinding glory
    sig = (light + harmonics + shimmer) * blind;

    // Wide stereo spread - enveloping light
    sig = ~stereoSpread.(sig, 0.3 * moment, 0.6);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_glory loaded".postln;
