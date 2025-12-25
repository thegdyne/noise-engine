// Fang Strike — Modal synthesis of bone/ivory tusks
// Role: accent | Family: physical

SynthDef(\forge_rakshasa_fang_strike, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bone, bite, tusk, gnaw, snap;
    var exciter, modes, modeFreqs, modeDecays, gnawMod, tuskShift;

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
    bone = In.kr(customBus0).linlin(0, 1, 0.9, 0.995);    // Ring time multiplier
    bite = In.kr(customBus1).linexp(0, 1, 0.0001, 0.01); // Click attack time
    tusk = In.kr(customBus2).linexp(0, 1, 0.5, 2);        // Formant shift
    gnaw = In.kr(customBus3).linlin(0, 1, 0, 0.3);        // Grind modulation depth
    snap = In.kr(customBus4).linlin(0, 1, 0.1, 1.5);      // Release modifier

    // Tusk size shifts all modal frequencies
    tuskShift = tusk;

    // Inharmonic modal frequencies for bone/ivory (not integer ratios)
    modeFreqs = [1.0, 2.76, 5.4, 8.93, 13.34] * freq * tuskShift;

    // Gnawing modulation
    gnawMod = LFNoise1.kr(7) * gnaw;

    // Apply gnaw to frequencies
    modeFreqs = modeFreqs * (1 + gnawMod);

    // Modal decay times based on bone hardness
    modeDecays = [1.0, 0.7, 0.4, 0.25, 0.15] * decay * snap * bone.linlin(0.9, 0.995, 0.5, 2);

    // Exciter — sharp click
    exciter = Impulse.ar(0) * EnvGen.ar(Env.perc(bite, 0.001), doneAction: 0);
    exciter = exciter + (WhiteNoise.ar * EnvGen.ar(Env.perc(0.0001, bite * 10)));

    // Modal resonators
    modes = Klank.ar(
        `[modeFreqs, [0.5, 0.4, 0.25, 0.15, 0.1], modeDecays],
        exciter
    );

    // Mix with a bit of the exciter for transient
    sig = modes + (exciter * 0.3 * (1 - bone.linlin(0.9, 0.995, 0, 0.5)));

    // Stereo spread based on gnaw
    sig = Pan2.ar(sig, LFNoise2.kr(3) * gnaw * 0.5);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay * snap, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_fang_strike loaded".postln;
