// Tongue Lash -- Forked tongue with pitch dive and squelchy FM
// Role: accent | Family: FM

SynthDef(\forge_rakshasa_tongue_lash, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var fork, lash, slime, curl, drip;
    var tongue1, tongue2, modulator, pitchEnv, detuneAmt, fmDepth, vibrato;

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
    fork = In.kr(customBus0).linlin(0, 1, 1, 2.5);        // Detune ratio
    lash = In.kr(customBus1).linexp(0, 1, 1.01, 4);       // Pitch dive multiplier
    slime = In.kr(customBus2).linexp(0, 1, 0.5, 8);       // FM index
    curl = In.kr(customBus3).linlin(0, 1, 0, 12);         // Vibrato Hz
    drip = In.kr(customBus4).linlin(0, 1, 0.3, 2);        // Decay modifier

    // Pitch envelope -- dives down from high on trigger
    pitchEnv = EnvGen.kr(Env.perc(0.001, decay * drip), doneAction: 0);
    freq = freq * (1 + ((lash - 1) * pitchEnv));

    // Vibrato/curl
    vibrato = SinOsc.kr(curl, 0, curl.linlin(0, 12, 0, 0.02));
    freq = freq * (1 + vibrato);

    // Detuning for forked tongues
    detuneAmt = (fork - 1) * 0.5;

    // FM modulator -- squelchy character
    modulator = SinOsc.ar(freq * 2) * slime * freq;

    // Two forked tongue oscillators
    tongue1 = SinOsc.ar(freq * (1 - detuneAmt) + modulator);
    tongue2 = SinOsc.ar(freq * (1 + detuneAmt) + (modulator * 0.7));

    // Combine with stereo split
    sig = [tongue1 * 0.7 + (tongue2 * 0.3), tongue2 * 0.7 + (tongue1 * 0.3)];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay * drip, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_tongue_lash loaded".postln;
