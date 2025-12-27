// nozzle: Hissing fuel spray and drip
SynthDef(\forge_vapor_station_nozzle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var spray, drip, splatter, flow, vapors;

    // Theme params
    spray = In.kr(customBus0).linlin(0, 1, 0.2, 1);        // P1: Spray intensity
    drip = In.kr(customBus1).linlin(0, 1, 1, 15);          // P2: Drip rate
    splatter = In.kr(customBus2).linlin(0, 1, 0, 0.6);     // P3: Splatter amount
    flow = In.kr(customBus3).linlin(0, 1, 0.1, 0.7);       // P4: Flow noise
    vapors = In.kr(customBus4).linlin(0, 1, 0, 0.5);       // P5: Vapor shimmer

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

    // DSP: Spray hiss - filtered noise
    sig = BPF.ar(WhiteNoise.ar(spray), 4000 * LFNoise1.kr(0.5).range(0.7, 1.3), 0.5) * 2;

    // Drip impacts
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.3, freq * [3, 4.5], 0.03) * splatter);

    // Flow noise - continuous
    sig = sig + (LPF.ar(PinkNoise.ar(flow), freq * 4) * 0.5);

    // Vapor shimmer - high ethereal
    sig = sig + (SinOsc.ar(freq * [6, 8.01, 10.02]) * vapors * LFNoise1.kr(0.3).range(0.2, 1) * 0.15);

    sig = sig * 0.35;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_nozzle loaded".postln;
