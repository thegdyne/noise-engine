// GLACLEAD - Crystalline melodic lead
// Phase modulation with faceted detuning

SynthDef(\forge_glacialis_glaclead, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ice, facet, prism, melt, glass;
    var carrier, modulator, detuned, harmonics, lfo;

    // Theme params
    ice = In.kr(customBus0);     // Brightness
    facet = In.kr(customBus1);   // Detuning
    prism = In.kr(customBus2);   // PM depth
    melt = In.kr(customBus3);    // Filter env
    glass = In.kr(customBus4);   // Harmonic emphasis

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

    // Subtle shimmer LFO
    lfo = SinOsc.kr(4 + (ice * 3)).range(0.98, 1.02);

    // Phase modulation - carrier with modulator
    modulator = SinOsc.ar(freq * 2) * prism.linexp(0, 1, 0.5, 4) * freq;
    carrier = SinOsc.ar(freq + modulator);

    // Faceted detuning - multiple slightly detuned copies
    detuned = Mix.fill(4, { |i|
        var detune, phase;
        detune = facet.linexp(0, 1, 1, 1.01) ** (i - 1.5);
        phase = i * 0.25 * pi;
        SinOsc.ar((freq * detune * lfo) + (modulator * (1 - (i * 0.15))), phase)
    }) * 0.3;

    sig = (carrier * 0.4) + detuned;

    // Glassy harmonics - add upper partials
    harmonics = SinOsc.ar(freq * 3, SinOsc.ar(freq * 5) * glass) * 0.2;
    harmonics = harmonics + (SinOsc.ar(freq * 5) * 0.1);
    sig = sig + (harmonics * glass);

    // Brightness control via high shelf
    sig = sig + (HPF.ar(sig, 2000) * ice * 0.5);

    // Subtle stereo from facet
    sig = [sig, DelayC.ar(sig, 0.01, facet * 0.003)];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_glacialis_glaclead loaded".postln;
