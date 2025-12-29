SynthDef(\forge_pripyat_siren, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var dist, wail, rate, tone, dopp;
    var sweepFreq, harmonics, dopplerMod;

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
    dist = In.kr(customBus0);
    wail = In.kr(customBus1);
    rate = In.kr(customBus2);
    tone = In.kr(customBus3);
    dopp = In.kr(customBus4);

    // Sweep oscillator for wailing
    sweepFreq = SinOsc.kr(rate.linexp(0, 1, 0.1, 2)).range(
        freq * (1 - (wail * 0.3)),
        freq * (1 + (wail * 0.3))
    );

    // Doppler drift
    dopplerMod = LFNoise2.kr(0.1).range(1 - (dopp * 0.05), 1 + (dopp * 0.05));
    sweepFreq = sweepFreq * dopplerMod;

    // Harmonic series - civil defense siren character
    harmonics = Mix.fill(8, { |i|
        SinOsc.ar(
            sweepFreq * (i + 1),
            0,
            (1 / (i + 1)) * (tone.linlin(0, 1, 0.3, 1) ** i) * if((i + 1).odd, 1, 0.6)
        );
    });

    sig = harmonics * 0.6;

    // Distance processing - gentler lowpass, boost before filter
    sig = LPF.ar(sig, dist.linexp(0, 1, 10000, 1500));

    // Compensate for distance attenuation
    sig = sig * dist.linlin(0, 1, 1, 2);

    // Simple distance reverb
    sig = sig + (CombL.ar(sig, 0.2, dist.linlin(0, 1, 0.02, 0.12), dist.linlin(0, 1, 0.1, 1.2)) * dist * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pripyat_siren loaded".postln;
