// fluoro: Cold flickering fluorescent tubes
SynthDef(\forge_vapor_station_fluoro, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var buzz, cold, strobe, failing, tubes;

    // Theme params
    buzz = In.kr(customBus0).linlin(0, 1, 0.3, 1);         // P1: Buzz intensity
    cold = In.kr(customBus1).linlin(0, 1, 0.2, 0.8);       // P2: Cold high harmonics
    strobe = In.kr(customBus2).linlin(0, 1, 0, 0.5);       // P3: Strobe flicker
    failing = In.kr(customBus3).linlin(0, 1, 0, 0.6);      // P4: Failing tube crackle
    tubes = In.kr(customBus4).linlin(0, 1, 1, 4);          // P5: Number of tubes

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

    // DSP: High frequency buzz (different from sodium)
    sig = SinOsc.ar(120 * [1, 2, 3, 5]) * [1, 0.6, 0.3, 0.15] * buzz;
    sig = sig.sum;

    // Cold high harmonics
    sig = sig + (Blip.ar(freq * 2, tubes.round * 3) * cold * 0.2);

    // Strobe flicker - rapid on/off
    sig = sig * (1 - (LFPulse.kr(LFNoise0.kr(3).range(5, 15), 0, 0.5) * strobe));

    // Failing tube - crackle and sputter
    sig = sig + (HPF.ar(Dust2.ar(failing * 30) * 0.2, 1000));
    sig = sig * (1 - (Dust.kr(failing * 2) * 0.5).lag(0.001, 0.05));

    // Slight detuned copies for multiple tubes
    sig = sig + (DelayN.ar(sig, 0.01, 0.003) * 0.3);

    sig = sig * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_fluoro loaded".postln;
