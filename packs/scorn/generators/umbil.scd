// umbil: Umbilical cables - pulsing tubes
SynthDef(\forge_scorn_umbil, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pulse, tube, flow, taut, connect;
    var pulseMod;

    // Theme params
    pulse = In.kr(customBus0).linexp(0, 1, 0.5, 3);         // P1: Pulse rate
    tube = In.kr(customBus1).linlin(0, 1, 0.3, 0.9);        // P2: Tube resonance
    flow = In.kr(customBus2).linlin(0, 1, 0.2, 0.7);        // P3: Fluid flow
    taut = In.kr(customBus3).linlin(0, 1, 500, 3000);       // P4: Tautness
    connect = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);     // P5: Connection strength

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

    // DSP: Pulsing rhythm
    pulseMod = LFPulse.kr(pulse, 0, 0.4).lag(0.05, 0.15);

    // Tube resonance - filtered with pulse
    sig = BPF.ar(PinkNoise.ar(tube * 0.5), taut * pulseMod.range(0.5, 1), 0.2);

    // Fluid flow through tube
    sig = sig + (LPF.ar(BrownNoise.ar(flow * 0.4), 600) * pulseMod.range(0.3, 1));

    // Connection tone - continuous
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * connect * 0.3);

    // Tube body hum
    sig = sig + (Saw.ar(freq * [1, 1.002]) * tube * 0.15);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_umbil loaded".postln;
