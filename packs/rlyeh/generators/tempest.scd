// tempest: The storm summoned - chaos of wind and wave
SynthDef(\forge_rlyeh_tempest, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wind, waves, thunder, rain, chaos;

    // Theme params
    wind = In.kr(customBus0).linlin(0, 1, 0.3, 1);         // P1: Wind intensity
    waves = In.kr(customBus1).linlin(0, 1, 0.1, 0.8);      // P2: Wave rate
    thunder = In.kr(customBus2).linlin(0, 1, 0.1, 0.6);    // P3: Thunder rumble
    rain = In.kr(customBus3).linlin(0, 1, 5, 100);         // P4: Rain density
    chaos = In.kr(customBus4).linlin(0, 1, 0.2, 1);        // P5: Storm chaos

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

    // DSP: Wind - continuous filtered noise
    sig = BPF.ar(PinkNoise.ar(wind), freq * LFNoise1.kr(chaos).exprange(0.5, 3), 0.4) * 3;
    sig = sig + (LPF.ar(BrownNoise.ar(wind * 0.6), freq * 2));

    // Wave modulation - continuous
    sig = sig * SinOsc.kr(waves).range(0.6, 1);

    // Thunder rumble - continuous low drone with variation
    sig = sig + (LPF.ar(BrownNoise.ar(thunder), 80 + (LFNoise1.kr(0.3) * 40)) * 0.5);

    // Rain texture - continuous high crackle
    sig = sig + (HPF.ar(Dust2.ar(rain) * 0.15, 3000));

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_tempest loaded".postln;
