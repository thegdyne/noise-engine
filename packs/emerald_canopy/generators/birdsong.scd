// Birdsong - FM chirps and melodic trills
// Role: foreground | Family: FM

SynthDef(\forge_emerald_canopy_birdsong, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var trill, wing, beak, plumage, flutter;
    var trillLfo, flutterNoise, modRatio, modIndex, modulator, carrier;

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
    trill = In.kr(customBus0);    // Vibrato speed
    wing = In.kr(customBus1);     // Vibrato depth
    beak = In.kr(customBus2);     // FM ratio
    plumage = In.kr(customBus3);  // Brightness
    flutter = In.kr(customBus4);  // Randomness

    // Trill LFO - fast vibrato like a bird call
    trillLfo = SinOsc.kr(trill.linexp(0, 1, 4, 30));

    // Flutter adds randomness to the trill
    flutterNoise = LFNoise1.kr(20) * flutter;
    trillLfo = trillLfo + (flutterNoise * 0.5);

    // Modulate pitch with trill
    freq = freq * (1 + (trillLfo * wing * 0.1));

    // FM synthesis
    // Beak controls harmonic ratio - bird-like partials
    modRatio = beak.linlin(0, 1, 1.5, 4.0);  // Non-integer for complex harmonics
    modIndex = plumage.linexp(0, 1, 0.5, 8);

    // Add flutter to mod index for organic variation
    modIndex = modIndex * (1 + (LFNoise2.kr(5) * flutter * 0.3));

    modulator = SinOsc.ar(freq * modRatio) * modIndex * freq;
    carrier = SinOsc.ar(freq + modulator);

    // Add brightness harmonic
    sig = carrier + (SinOsc.ar(freq * 2) * plumage * 0.3);

    // Slight chorus for richness
    sig = sig + (SinOsc.ar(freq * 1.003 + modulator) * 0.2);

    // Stereo movement like bird hopping between branches
    sig = Pan2.ar(sig, SinOsc.kr(trill.linlin(0, 1, 0.5, 3)) * 0.4);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_birdsong loaded".postln;
