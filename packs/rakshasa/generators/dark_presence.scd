// Dark Presence -- Deep sub drone from the void
// Role: bed | Family: subtractive

SynthDef(\forge_rakshasa_dark_presence, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var void, mass, dread, creep, abyss;
    var subOsc, massLayers, dreadDetune, creepMod, abyssFreq;
    var layer1, layer2, layer3, dissonance;

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

    // Custom parameters
    void = In.kr(customBus0).linlin(0, 1, 0, 0.8);         // Sub amount
    mass = In.kr(customBus1).linlin(0, 1, 1, 4);           // Layer count/thickness
    dread = In.kr(customBus2).linlin(0, 1, 0, 0.05);       // Detune for dissonance
    creep = In.kr(customBus3).linexp(0, 1, 0.01, 0.3);     // Modulation rate
    abyss = In.kr(customBus4).linlin(0, 1, 1, 0.25);       // Octave multiplier (lower = deeper)

    // Base frequency goes into the abyss
    abyssFreq = freq * abyss;

    // Creeping slow modulation
    creepMod = LFNoise1.kr(creep).range(0.98, 1.02);

    // Primary sub oscillator
    subOsc = SinOsc.ar(abyssFreq * creepMod) * void;

    // Add second harmonic for presence
    subOsc = subOsc + (SinOsc.ar(abyssFreq * 2 * creepMod) * void * 0.3);

    // Mass layers -- stacked oscillators for thickness
    layer1 = SinOsc.ar(abyssFreq * creepMod);
    layer2 = SinOsc.ar(abyssFreq * 1.5 * creepMod * LFNoise1.kr(creep * 0.5).range(0.99, 1.01));
    layer3 = SinOsc.ar(abyssFreq * 2 * creepMod * LFNoise1.kr(creep * 0.3).range(0.99, 1.01));

    massLayers = (layer1 + (layer2 * 0.5) + (layer3 * 0.3)) * mass.linlin(1, 4, 0.2, 0.5);

    // Dread -- dissonant detuning
    dissonance = SinOsc.ar(abyssFreq * (1 + dread) * creepMod) * dread * 10;
    dissonance = dissonance + (SinOsc.ar(abyssFreq * (1 - (dread * 0.7)) * creepMod) * dread * 8);

    // Combine all
    sig = subOsc + massLayers + dissonance;

    // Very subtle stereo movement
    sig = Pan2.ar(sig, SinOsc.kr(creep * 0.2).range(-0.15, 0.15));

    // Low pass to keep it in the sub/low-mid range
    sig = LPF.ar(sig, abyssFreq * 8);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_dark_presence loaded".postln;
