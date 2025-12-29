SynthDef(\forge_ekrano_ground, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var altitude, airflow, lift, turbulence, hiss;
    var exciter, tubeDelay, tubeSig, turbMod, hissSig;

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
    altitude = In.kr(customBus0).linexp(0, 1, 0.5, 4);
    airflow = In.kr(customBus1).linlin(0, 1, 0.1, 0.8);
    lift = In.kr(customBus2).linlin(0, 1, 0.1, 0.9);
    turbulence = In.kr(customBus3).linexp(0, 1, 0.5, 15);
    hiss = In.kr(customBus4);

    // Turbulence modulation
    turbMod = LFNoise1.kr(turbulence).range(0.9, 1.1);

    // Air flow excitation
    exciter = PinkNoise.ar(airflow) + (BrownNoise.ar(airflow * 0.3));

    // Tube resonator - waveguide style
    tubeDelay = (1 / (freq * altitude * turbMod)).clip(0.0001, 0.05);
    tubeSig = CombL.ar(exciter, 0.05, tubeDelay, lift * 0.5);
    tubeSig = tubeSig + CombL.ar(exciter, 0.05, tubeDelay * 1.5, lift * 0.3);

    // High frequency hiss layer
    hissSig = HPF.ar(WhiteNoise.ar(hiss * 0.3), 4000);

    sig = (tubeSig * 0.6) + (hissSig * 0.4);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_ground loaded".postln;
