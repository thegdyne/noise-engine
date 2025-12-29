SynthDef(\forge_duga_woodpck, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rate, sharp, band, noise, drift;
    var tapRate, tapSig, noiseSig, driftMod, pulseWidth;

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

    // Custom params
    rate = In.kr(customBus0);
    sharp = In.kr(customBus1);
    band = In.kr(customBus2);
    noise = In.kr(customBus3);
    drift = In.kr(customBus4);

    // Tap rate - classic woodpecker was ~10Hz
    tapRate = rate.linexp(0, 1, 5, 20);
    driftMod = LFNoise2.kr(0.2).range(1 - (drift * 0.1), 1 + (drift * 0.1));
    tapRate = tapRate * driftMod;

    // Pulse width based on sharpness
    pulseWidth = sharp.linlin(0, 1, 0.3, 0.05);

    // The tapping signal - boosted
    tapSig = LFPulse.ar(tapRate, 0, pulseWidth);
    tapSig = tapSig * BPF.ar(WhiteNoise.ar(1), freq * driftMod, band.linexp(0, 1, 0.5, 0.05));
    tapSig = tapSig * 2;

    // Background shortwave static - continuous and louder
    noiseSig = BPF.ar(PinkNoise.ar(1), freq * 0.5, 0.3);
    noiseSig = noiseSig + (PinkNoise.ar(0.1)); // Continuous bed
    noiseSig = noiseSig * (0.3 + (noise * 0.4));

    // Mix
    sig = tapSig + noiseSig;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_woodpck loaded".postln;
