// breath: Human warmth - organic, living
SynthDef(\forge_ex_machina_breath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var inhale, warmth, life, pulse, soft;
    var breathCycle;

    // Theme params
    inhale = In.kr(customBus0).linlin(0, 1, 0.1, 0.3);      // P1: Breath rate
    warmth = In.kr(customBus1).linlin(0, 1, 0.3, 1);        // P2: Body warmth
    life = In.kr(customBus2).linlin(0, 1, 0.1, 0.5);        // P3: Life signs
    pulse = In.kr(customBus3).linlin(0, 1, 0.8, 1.5);       // P4: Heart pulse rate
    soft = In.kr(customBus4).linlin(0, 1, 400, 2000);       // P5: Softness filter

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

    // DSP: Breath cycle - slow modulated noise
    breathCycle = SinOsc.kr(inhale).range(0.3, 1);
    sig = BPF.ar(PinkNoise.ar(warmth * 0.5), freq * 2, 0.4) * breathCycle;

    // Body warmth - low filtered tone
    sig = sig + (LPF.ar(Saw.ar(freq * [0.5, 0.501]) * warmth, soft) * 0.25);

    // Life signs - subtle variations
    sig = sig + (SinOsc.ar(freq * LFNoise1.kr(0.1).range(0.99, 1.01)) * life * 0.2);

    // Heart pulse - sub rhythm
    sig = sig + (SinOsc.ar(freq * 0.25) * LFPulse.kr(pulse, 0, 0.1).lag(0.05, 0.2) * 0.2);

    // Continuous warmth
    sig = sig + (SinOsc.ar(freq * 0.5) * warmth * 0.15);

    sig = LPF.ar(sig, soft) * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_breath loaded".postln;
