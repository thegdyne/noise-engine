// filter: Resonant filter sweep - self-oscillation territory
SynthDef(\forge_mod_caf_filter, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var resonance, sweep, input, feedback, ping;
    var sweepMod, filterCut;

    // Theme params
    resonance = In.kr(customBus0).linlin(0, 1, 0.5, 0.05);  // P1: Resonance (lower rq = more res)
    sweep = In.kr(customBus1).linlin(0, 1, 0.05, 2);        // P2: Sweep rate
    input = In.kr(customBus2).linlin(0, 1, 0.2, 0.8);       // P3: Input level
    feedback = In.kr(customBus3).linlin(0, 1, 0, 0.7);      // P4: Feedback
    ping = In.kr(customBus4).linlin(0, 1, 1, 10);           // P5: Ping rate

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

    // DSP: Sweep modulation
    sweepMod = LFTri.kr(sweep).range(0.5, 2);
    filterCut = freq * 4 * sweepMod;

    // Input noise
    sig = PinkNoise.ar(input) + (Saw.ar(freq * [1, 1.003]) * input * 0.3);

    // Resonant filter
    sig = RLPF.ar(sig, filterCut.clip(20, 18000), resonance);

    // Filter ping - excite the resonance
    sig = sig + (Ringz.ar(Dust.ar(ping) * 0.2, filterCut.clip(100, 8000), resonance * 2) * 0.3);

    // Feedback saturation
    sig = (sig * (1 + feedback)).tanh;

    sig = sig * 0.4;

    // Output chain (with Limiter for resonance)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_filter loaded".postln;
