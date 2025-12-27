// hose: Resonant rubber fuel hose
SynthDef(\forge_vapor_station_hose, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tension, length, excite, rubber, flow;
    var delTime, exciter;

    // Theme params
    tension = In.kr(customBus0).linlin(0, 1, 0.9, 0.99);   // P1: Tube tension (feedback)
    length = In.kr(customBus1).linlin(0, 1, 0.5, 2);       // P2: Tube length multiplier
    excite = In.kr(customBus2).linlin(0, 1, 3, 20);        // P3: Excitation rate (boosted)
    rubber = In.kr(customBus3).linlin(0, 1, 800, 4000);    // P4: Rubber damping freq
    flow = In.kr(customBus4).linlin(0, 1, 0.2, 0.7);       // P5: Flow through tube

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

    // DSP: Karplus-Strong style waveguide
    delTime = (1 / freq) * length;
    exciter = Dust.ar(excite) * 0.8;

    // Comb resonator for tube - boosted feedback time
    sig = CombL.ar(exciter, 0.1, delTime.clip(0.001, 0.1), tension * 3);
    sig = LPF.ar(sig, rubber);

    // Flow noise through tube - boosted
    sig = sig + (BPF.ar(PinkNoise.ar(flow), freq * [1.5, 2.5], 0.4) * 0.8);

    // Continuous tonal anchor
    sig = sig + (SinOsc.ar(freq * [0.5, 0.501]) * 0.15);

    sig = sig * 0.5;

    // Output chain (with Limiter for comb feedback)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_hose loaded".postln;
