// Emerald Pad - Rich gem-like harmonics
// Role: bed | Family: subtractive

SynthDef(\forge_emerald_canopy_emerald_pad, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                               filterTypeBus, envEnabledBus, envSourceBus=0,
                                               clockRateBus, clockTrigBus,
                                               midiTrigBus=0, slotIndex=0,
                                               customBus0, customBus1, customBus2, customBus3, customBus4,
                                               portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gem, facets, glow, drift, thickness;
    var driftLfo, voices, sub, detune, saturated;

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
    gem = In.kr(customBus0);       // Harmonic structure
    facets = In.kr(customBus1);    // Unison detune
    glow = In.kr(customBus2);      // Saturation
    drift = In.kr(customBus3);     // Movement
    thickness = In.kr(customBus4); // Sub blend

    // Drift LFO - slow organic movement
    driftLfo = LFNoise2.kr(0.05 + (drift * 0.15));

    // Detune amount from facets
    detune = facets.linexp(0, 1, 0.001, 0.012);

    // Create unison voices with different waveforms based on gem
    voices = Array.fill(5, { |i|
        var ratio = (i - 2) * detune + 1;
        var voiceFreq = freq * ratio * (1 + (driftLfo * drift * 0.01));
        var voicePan = (i - 2) / 2 * facets * 0.8;

        // Mix saw and pulse based on gem parameter
        var saw = Saw.ar(voiceFreq);
        var pulse = Pulse.ar(voiceFreq, 0.3 + (gem * 0.4));
        var mix = (saw * (1 - gem)) + (pulse * gem);

        Pan2.ar(mix, voicePan)
    }).sum / 5;

    // Sub octave for thickness
    sub = SinOsc.ar(freq * 0.5) * thickness * 0.4;
    sub = sub + (Saw.ar(freq * 0.5) * thickness * 0.2);

    sig = voices + sub;

    // Glow - soft saturation for warmth
    saturated = (sig * (1 + (glow * 3))).tanh;
    sig = (sig * (1 - glow)) + (saturated * glow * 0.7);

    // Add subtle chorus movement
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.3 + drift).range(0.01, 0.02)) * facets * 0.3);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_emerald_pad loaded".postln;
