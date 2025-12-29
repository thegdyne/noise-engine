SynthDef(\forge_duga_signal, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var harm, warb, fade, data, dist;
    var harmonics, warbMod, fadeMod, dataSig;

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
    harm = In.kr(customBus0);
    warb = In.kr(customBus1);
    fade = In.kr(customBus2);
    data = In.kr(customBus3);
    dist = In.kr(customBus4);

    // Signal warble - ionospheric effects
    warbMod = SinOsc.kr(warb.linexp(0, 1, 0.5, 8)).range(0.98, 1.02);

    // Fading - signal strength variation
    fadeMod = LFNoise2.kr(fade.linexp(0, 1, 0.1, 1)).range(1 - (fade * 0.6), 1);

    // Harmonic series - NO var inside Mix.fill
    harmonics = Mix.fill(8, { |i|
        SinOsc.ar(
            freq * (i + 1) * warbMod,
            0,
            (1 / (i + 1)) * (harm.linlin(0, 1, 0.3, 1) ** (i * 0.5))
        );
    });

    sig = harmonics * 0.4 * fadeMod;

    // Data bursts - digital transmission sounds
    dataSig = Pulse.ar(freq * 2, LFNoise0.kr(15).range(0.2, 0.8));
    dataSig = dataSig * LFPulse.kr(data.linexp(0, 1, 0.5, 4), 0, 0.3);
    dataSig = LPF.ar(dataSig, 3000) * data * 0.2;

    sig = sig + dataSig;

    // Distance - lowpass for propagation loss
    sig = LPF.ar(sig, dist.linexp(0, 1, 10000, 2000));

    // Add some static
    sig = sig + (BPF.ar(WhiteNoise.ar(1), freq, 0.5) * dist * 0.1);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_signal loaded".postln;
