SynthDef(\forge_summer_of_love_psyche_swirl, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                                 clockRateBus, clockTrigBus,
                                                 midiTrigBus=0, slotIndex=0,
                                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                                 portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var spin, depth, spiral, kaleid, cosmos;
    var spinRate, phases, phaseMod, voices, folded, smear;

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
    spin = In.kr(customBus0);      // Rotation speed
    depth = In.kr(customBus1);     // Modulation depth
    spiral = In.kr(customBus2);    // Complexity
    kaleid = In.kr(customBus3);    // Wavefolding
    cosmos = In.kr(customBus4);    // Reverb smear

    // Spin rate - from very slow to medium-fast
    spinRate = spin.linexp(0, 1, 0.05, 4);

    // Phase offsets for quadrature-style rotation
    phases = [0, 0.25, 0.5, 0.75];

    // Create rotating phase-modulated voices
    voices = phases.collect({ |phaseOff, i|
        var lfo, modSig, carrier, pan;
        var spiralLfo;

        // Main rotation LFO with phase offset
        lfo = SinOsc.kr(spinRate, phaseOff * 2pi);

        // Spiral adds secondary modulation
        spiralLfo = SinOsc.kr(spinRate * (2 + i), phaseOff * 2pi) * spiral * 0.5;

        // Phase modulation signal
        modSig = SinOsc.ar(freq * (1 + (i * 0.002))) * (depth * 4 + (spiralLfo * depth * 2));

        // Carrier with phase modulation
        carrier = SinOsc.ar(freq * (1 + (i * 0.001)), modSig);

        // Add some harmonics for richness
        carrier = carrier + (SinOsc.ar(freq * 2 * (1 + (i * 0.002)), modSig * 1.5) * 0.3);
        carrier = carrier + (SinOsc.ar(freq * 3 * (1 + (i * 0.003)), modSig * 2) * 0.15 * spiral);

        // Pan based on LFO for rotation
        pan = lfo;
        Pan2.ar(carrier, pan)
    }).sum;

    sig = voices * 0.35;

    // Kaleidoscope - wavefolding for harmonic complexity
    folded = sig.fold2(1 - (kaleid * 0.5));
    sig = XFade2.ar(sig, folded, kaleid.linlin(0, 1, -1, 0.5));

    // Cosmos - smeared reverb-like tail using allpass delays
    smear = sig;
    4.do({ |i|
        smear = AllpassL.ar(smear, 0.2, (0.03 + (i * 0.017)).clip(0.01, 0.2), cosmos * 2);
    });
    sig = sig + (smear * cosmos * 0.5);

    // Apply standard processing chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_psyche_swirl loaded".postln;
