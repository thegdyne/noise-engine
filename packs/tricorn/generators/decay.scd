SynthDef(\forge_tricorn_decay, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var erosion, crumble, stain, moss, fracture;
    var source, crushed, bits, sampleRate, stainMod, glitch;

    // Theme params
    erosion = In.kr(customBus0);
    crumble = In.kr(customBus1);
    stain = In.kr(customBus2);
    moss = In.kr(customBus3);
    fracture = In.kr(customBus4);

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

    // Source - oscillator + noise mix
    source = Saw.ar(freq, 0.3);
    source = source + Pulse.ar(freq * 0.5, 0.4, 0.2);
    source = source + (PinkNoise.ar(0.2) * moss);

    // Moss - organic texture layer
    source = source + (LFNoise1.ar(freq * 0.1, 0.15) * moss);

    // Stain modulation - wandering filter
    stainMod = LFNoise2.kr(0.3 + (stain * 0.5)).range(0.5, 2.0);
    source = BPF.ar(source, freq * stainMod, 0.5 + (stain * 0.4)) * 2;
    source = source + (BrownNoise.ar(0.1) * stain);

    // Bit depth reduction (erosion)
    bits = erosion.linexp(0, 1, 16, 3);
    crushed = source.round(2.pow(bits.neg));

    // Sample rate reduction (crumble)
    sampleRate = crumble.linexp(0, 1, 44100, 2000);
    crushed = Latch.ar(crushed, Impulse.ar(sampleRate));

    // Blend original with crushed
    sig = (source * (1 - (erosion * 0.7))) + (crushed * erosion * 0.8);

    // Fracture glitches - sample and hold stutters
    glitch = Latch.ar(sig, Dust.ar(fracture.linexp(0, 1, 1, 50)));
    sig = Select.ar(LFPulse.kr(fracture.linexp(0, 1, 0.5, 8), 0, fracture * 0.3), [sig, glitch]);

    // Add continuous noise bed for presence
    sig = sig + (PinkNoise.ar(0.05));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_decay loaded".postln;
