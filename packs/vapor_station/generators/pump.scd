// pump: Mechanical fuel pump rhythm
SynthDef(\forge_vapor_station_pump, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rate, stroke, mech, pressure, grind;
    var pumpEnv;

    // Theme params
    rate = In.kr(customBus0).linlin(0, 1, 0.5, 4);         // P1: Pump rate
    stroke = In.kr(customBus1).linlin(0, 1, 0.3, 1);       // P2: Stroke intensity
    mech = In.kr(customBus2).linlin(0, 1, 0, 0.6);         // P3: Mechanical clatter
    pressure = In.kr(customBus3).linlin(0, 1, 0.2, 0.8);   // P4: Pressure hiss
    grind = In.kr(customBus4).linlin(0, 1, 0, 0.5);        // P5: Grinding texture

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

    // DSP: Pump stroke - low thump
    pumpEnv = LFPulse.kr(rate, 0, 0.3).lag(0.02, 0.1);
    sig = SinOsc.ar(freq * 0.5) * pumpEnv * stroke;
    sig = sig + (LPF.ar(PinkNoise.ar(stroke * 0.3), freq) * pumpEnv);

    // Mechanical clatter
    sig = sig + (Ringz.ar(Dust.ar(rate * 5) * mech, freq * [2, 3.5], 0.05) * 0.4);

    // Pressure hiss (continuous)
    sig = sig + (HPF.ar(PinkNoise.ar(pressure * 0.3), 2000) * LFNoise1.kr(rate).range(0.5, 1));

    // Grinding undertone
    sig = sig + (LPF.ar(Crackle.ar(1.5) * grind * 0.2, freq * 3));

    sig = sig * 0.35;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_pump loaded".postln;
