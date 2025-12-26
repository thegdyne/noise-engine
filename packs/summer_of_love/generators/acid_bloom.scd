SynthDef(\forge_summer_of_love_acid_bloom, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                               filterTypeBus, envEnabledBus, envSourceBus=0,
                                               clockRateBus, clockTrigBus,
                                               midiTrigBus=0, slotIndex=0,
                                               customBus0, customBus1, customBus2, customBus3, customBus4,
                                               portamentoBus,
                                               ampBus=(-1)|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var squelch, bloom, trip, dose, sub;
    var osc, subOsc, filtEnv, envTrig, filtFreqMod, saturated;
    var fallbackAmpBus, envSel, clockIdx, midiIdx, ampEnv;
    // @forge: inline_post_chain

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    // Safety clamp: rq=0 (or negative) can break RLPF / render
    rq = rq.clip(0.05, 1.0);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    // amp: prefer explicit ampBus if provided; otherwise fall back to ~params safely
    fallbackAmpBus = ((~params ? IdentityDictionary.new)[\amplitude] ? 0);
    amp = In.kr(Select.kr((ampBus >= 0), [fallbackAmpBus, ampBus]));
    // Theme params
    squelch = In.kr(customBus0);   // Filter env amount
    bloom = In.kr(customBus1);     // Filter env decay
    trip = In.kr(customBus2);      // Resonance boost
    dose = In.kr(customBus3);      // Distortion
    sub = In.kr(customBus4);       // Sub oscillator

    // Main saw oscillator with slight detuning for thickness
    osc = Saw.ar(freq) + (Saw.ar(freq * 1.005) * 0.5) + (Pulse.ar(freq, 0.5) * 0.3);
    osc = osc * 0.5;

    // Sub oscillator - one octave down square
    subOsc = Pulse.ar(freq * 0.5, 0.5) * sub * 0.6;

    sig = osc + subOsc;

    // Create trigger for filter envelope from same sources as amp env
    // This reads the audio-rate trigger buses
        envSel = envSource.round.clip(0, 2);
    clockIdx = clockRate.round.clip(0, 12);
    midiIdx = slotIndex.round.clip(0, 7);

    envTrig = Select.ar(envSel, [
        DC.ar(0),                                                        // OFF - no trigger
        Select.ar(clockIdx, In.ar(clockTrigBus, 13)),                   // CLK
        Select.ar(midiIdx, In.ar(midiTrigBus, 8))                       // MIDI
    ]);
// Filter envelope - this is the "acid" character
    filtEnv = EnvGen.ar(
        Env.perc(0.001, bloom.linexp(0, 1, 0.05, 0.8)),
        envTrig
    );

    // Modulate filter cutoff with envelope
    filtFreqMod = filterFreq * (1 + (filtEnv * squelch * 8));

    // Resonant lowpass - trip boosts resonance beyond UI setting
    // Using RLPF for that 303 character
    sig = RLPF.ar(sig, filtFreqMod.clip(50, 16000), rq * (1 - (trip * 0.7)).clip(0.1, 1));

    // Distortion/overdrive
    saturated = (sig * (1 + (dose * 4))).tanh;
    sig = XFade2.ar(sig, saturated, dose.linlin(0, 1, -1, 0.8));

    // Compensate for resonance volume loss
    sig = sig * (1 + (trip * 0.5));

    // Note: We skip multiFilter here since we're doing our own acid filter
    // Inline envVCA + ensure2ch (renderer-safe)
    ampEnv = Select.ar(envSel, [
        DC.ar(1),
        EnvGen.ar(Env.perc(attack.max(0.001), decay.max(0.001)), envTrig),
        EnvGen.ar(Env.perc(attack.max(0.001), decay.max(0.001)), envTrig)
    ]);
    sig = sig * amp * ampEnv;
    sig = LeakDC.ar(sig);
    sig = sig.asArray;
    sig = (sig.size == 1).if({ [sig[0], sig[0]] }, { sig });
    sig = Limiter.ar(sig, 0.95);
    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_acid_bloom loaded".postln;
