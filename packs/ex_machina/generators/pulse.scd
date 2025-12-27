// pulse: Power source - rhythmic energy core
SynthDef(\forge_ex_machina_pulse, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rate, power, surge, glow, stable;
    var pulseMod;

    // Theme params
    rate = In.kr(customBus0).linexp(0, 1, 0.5, 4);          // P1: Pulse rate
    power = In.kr(customBus1).linlin(0, 1, 0.3, 1);         // P2: Power level
    surge = In.kr(customBus2).linlin(0, 1, 0, 0.5);         // P3: Power surge
    glow = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);        // P4: Amber glow
    stable = In.kr(customBus4).linlin(0, 1, 0.95, 1);       // P5: Stability

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

    // DSP: Pulse modulation
    pulseMod = LFPulse.kr(rate, 0, 0.3).lag(0.02, 0.1);

    // Power core - pulsing sub
    sig = SinOsc.ar(freq * 0.5 * LFNoise1.kr(0.1).range(stable, 1.01)) * power * 0.5;
    sig = sig * (0.5 + (pulseMod * 0.5));

    // Electrical hum
    sig = sig + (Saw.ar(freq * [1, 1.002]) * power * 0.2);

    // Surge events
    sig = sig + (Ringz.ar(Dust.ar(surge * 5) * 0.25, freq * [2, 4], 0.1) * surge);

    // Amber glow - warm continuous
    sig = sig + (SinOsc.ar(freq * [1, 2]) * glow * 0.2);

    // Stability noise
    sig = sig + (LPF.ar(PinkNoise.ar((1 - stable) * 0.3), 500));

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_pulse loaded".postln;
