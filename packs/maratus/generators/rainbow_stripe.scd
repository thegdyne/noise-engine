// Rainbow Stripe - Formant synthesis with color-mapped harmonic bands
// Like the iridescent stripes on the spider's display fan

SynthDef(\forge_maratus_rainbow_stripe, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var red, blue, green, yellow, blend;
    var source, redBand, blueBand, greenBand, yellowBand;
    var formantFreqs, formantQ;

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

    // Theme params - color band intensities
    red = In.kr(customBus0);
    blue = In.kr(customBus1);
    green = In.kr(customBus2);
    yellow = In.kr(customBus3);
    blend = In.kr(customBus4);

    // Formant Q (sharpness) from blend - inverse relationship
    formantQ = blend.linexp(0, 1, 0.05, 0.3);

    // Rich harmonic source - mix of saw and pulse
    source = (Saw.ar(freq) * 0.7) + (Pulse.ar(freq, 0.3) * 0.3);

    // Red band - low formant (warm, bass emphasis)
    // Around 400-600 Hz range, scaled to freq
    redBand = BPF.ar(source, (freq * 2).clip(200, 800), formantQ);
    redBand = redBand * red;

    // Blue band - mid formant (cool, clear)
    // Around 1-2 kHz range
    blueBand = BPF.ar(source, (freq * 5).clip(500, 3000), formantQ);
    blueBand = blueBand * blue;

    // Green band - high formant (natural, presence)
    // Around 2-4 kHz
    greenBand = BPF.ar(source, (freq * 10).clip(1000, 6000), formantQ);
    greenBand = greenBand * green;

    // Yellow band - presence/air formant
    // Around 4-8 kHz
    yellowBand = BPF.ar(source, (freq * 20).clip(2000, 10000), formantQ * 1.5);
    yellowBand = yellowBand * yellow;

    // Mix all color bands
    sig = (redBand + blueBand + greenBand + yellowBand);

    // Add fundamental for body
    sig = sig + (SinOsc.ar(freq) * 0.3);

    // Blend smooths the transitions with a subtle chorus
    sig = sig + (DelayC.ar(sig, 0.02, LFNoise1.kr(2).range(0.001, 0.008)) * blend * 0.3);

    // Normalize and soft limit
    sig = (sig * 2).tanh * 0.6;

    // Good stereo spread for the rainbow effect
    sig = ~stereoSpread.(sig, 0.3, 0.5);

    // Mandatory output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_maratus_rainbow_stripe loaded".postln;
