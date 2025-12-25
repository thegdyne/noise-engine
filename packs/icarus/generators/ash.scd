// Ash — disintegration, becoming particles
// Role: accent

SynthDef(\forge_icarus_ash, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var scatter, ember, dust, fade, memory;
    var particles, glow, fine, echo, scatterRate;

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
    scatter = In.kr(customBus0).linlin(0, 1, 5, 60);      // Particle rate
    ember = In.kr(customBus1).linlin(0, 1, 0.0, 0.5);     // Glow level
    dust = In.kr(customBus2).linlin(0, 1, 20, 200);       // Fine dust density
    fade = In.kr(customBus3).linlin(0, 1, 0.5, 0.05);     // Ring time
    memory = In.kr(customBus4).linlin(0, 1, 0.0, 0.5);    // Echo feedback

    // Scattering particles - pitched impulses
    particles = Dust.ar(scatter);
    particles = Ringz.ar(particles, freq * LFNoise0.kr(scatter * 0.1, 1, 2), fade);

    // Glowing embers - sine tones with random decay
    glow = SinOsc.ar(freq * LFNoise2.kr(2, 0.1, 1), 0, ember);
    glow = glow * LFNoise2.kr(4, 0.5, 0.5);

    // Fine dust - high density tiny particles
    fine = Dust2.ar(dust) * 0.2;
    fine = HPF.ar(fine, 2000);
    fine = Ringz.ar(fine, freq * 4 * LFNoise0.kr(10, 0.5, 1), 0.01);

    // Memory echoes - comb filter feedback
    echo = particles + glow;
    echo = CombL.ar(echo, 0.5, freq.reciprocal, memory * 2);

    // Combine - everything dissolving
    sig = particles + glow + fine + (echo * memory);

    // Wide scatter across stereo field
    sig = ~stereoSpread.(sig, 0.5, 0.8);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_ash loaded".postln;
