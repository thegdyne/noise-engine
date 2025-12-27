// sodium: Warm sodium lamp buzz and flicker
SynthDef(\forge_vapor_station_sodium, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var hum, warmth, flicker, ballast, glow;

    // Theme params
    hum = In.kr(customBus0).linlin(0, 1, 0.3, 1);          // P1: 60Hz hum level
    warmth = In.kr(customBus1).linlin(0, 1, 0.2, 0.8);     // P2: Warm harmonics
    flicker = In.kr(customBus2).linlin(0, 1, 0, 0.3);      // P3: Flicker amount
    ballast = In.kr(customBus3).linlin(0, 1, 0, 0.5);      // P4: Ballast whine
    glow = In.kr(customBus4).linlin(0, 1, 0.1, 0.6);       // P5: Warm glow pad

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

    // DSP: 60Hz hum with harmonics
    sig = SinOsc.ar(60 * [1, 2, 3, 4]) * [1, 0.5, 0.25, 0.12] * hum;
    sig = sig.sum;

    // Warm harmonics - pitched to freq
    sig = sig + (SinOsc.ar(freq * [1, 2, 3]) * [1, 0.4, 0.2] * warmth * 0.3).sum;

    // Flicker modulation
    sig = sig * (1 - (LFNoise2.kr(8) * flicker));

    // Ballast whine - high pitched
    sig = sig + (SinOsc.ar(120 * LFNoise1.kr(0.2).range(30, 35)) * ballast * 0.15);

    // Warm glow pad
    sig = sig + (LPF.ar(Saw.ar(freq * [0.5, 0.501]), 500) * glow * 0.3);

    sig = sig * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_sodium loaded".postln;
