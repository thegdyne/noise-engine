SynthDef(\forge_block_walk_rhodes_sun, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sun, bell, tremolo, vibrato, depth;
    var carrier, modulator, index, trem, vib, body, bellTone, envTrig, tineEnv;

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

    // Theme params
    sun = In.kr(customBus0);        // Brightness/FM index
    bell = In.kr(customBus1);       // High harmonic shimmer
    tremolo = In.kr(customBus2);    // Amp wobble
    vibrato = In.kr(customBus3);    // Pitch mod
    depth = In.kr(customBus4);      // Body resonance

    // Vibrato LFO
    vib = SinOsc.kr(5.2) * vibrato.linlin(0, 1, 0, 0.008) * freq;
    freq = freq + vib;

    // FM index from sun parameter
    index = sun.linexp(0, 1, 0.5, 4);

    // Tine envelope for percussive FM
    envTrig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    tineEnv = EnvGen.ar(Env.perc(0.001, 0.15), envTrig);

    // FM synthesis - modulator at harmonic ratio for bell-like tone
    modulator = SinOsc.ar(freq * 14) * index * (1 + (tineEnv * 2));
    carrier = SinOsc.ar(freq + modulator);

    // Bell overtone layer
    bellTone = SinOsc.ar(freq * 7) * bell.linlin(0, 1, 0, 0.15) * tineEnv;

    // Body resonance - lower partial
    body = SinOsc.ar(freq * 0.5) * depth.linlin(0, 1, 0.1, 0.4);

    sig = (carrier * 0.6) + bellTone + body;

    // Tremolo
    trem = SinOsc.kr(4.8).range(1 - (tremolo.linlin(0, 1, 0, 0.3)), 1);
    sig = sig * trem;

    // Soft saturation for warmth
    sig = sig.tanh * 0.8;

    // Output chain
    sig = ~stereoSpread.(sig, 0.15, 0.25);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_block_walk_rhodes_sun loaded".postln;
