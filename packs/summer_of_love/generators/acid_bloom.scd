SynthDef(\forge_summer_of_love_acid_bloom, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                               filterTypeBus, envEnabledBus, envSourceBus=0,
                                               clockRateBus, clockTrigBus,
                                               midiTrigBus=0, slotIndex=0,
                                               customBus0, customBus1, customBus2, customBus3, customBus4,
                                               portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var squelch, bloom, trip, dose, sub;
    var osc, subOsc, filtEnv, envTrig, filtFreqMod, saturated;

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
    envTrig = Select.ar(envSource, [
        DC.ar(0),                                                        // OFF - no trigger
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),            // CLK
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))                     // MIDI
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

    // Note: We skip ~multiFilter here since we're doing our own acid filter
    // But we still use ~envVCA for amplitude
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_acid_bloom loaded".postln;
