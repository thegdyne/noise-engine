// rlyeh: The sunken city - impossible architecture emerging
SynthDef(\forge_rlyeh_rlyeh, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var angles, depth, stone, echo, wrongness;

    // Theme params
    angles = In.kr(customBus0).linlin(0, 1, 0, 0.1);       // P1: Wrong angles detune
    depth = In.kr(customBus1).linlin(0, 1, 0.5, 2);        // P2: Submerged depth
    stone = In.kr(customBus2).linlin(0, 1, 0.1, 0.8);      // P3: Ancient stone resonance
    echo = In.kr(customBus3).linlin(0, 1, 0.1, 0.7);       // P4: Cyclopean echo
    wrongness = In.kr(customBus4).linlin(0, 1, 0, 0.5);    // P5: Geometric wrongness

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

    // DSP: Non-Euclidean harmonics
    sig = Saw.ar(freq * [1, 1 + angles, 1 + (angles * 1.7), 1 + (angles * 2.3)]);
    sig = sig * [1, 0.7, 0.5, 0.3];
    sig = Splay.ar(sig, wrongness);

    // Submerged filtering
    sig = LPF.ar(sig, freq * depth * 4);

    // Stone resonance
    sig = sig + (Ringz.ar(sig * 0.1, freq * [2, 3.01, 4.02], stone) * stone * 0.3);

    // Cyclopean echo
    sig = sig + (CombL.ar(sig, 0.5, LFNoise1.kr(0.1).range(0.15, 0.25), echo * 3) * echo * 0.4);

    sig = sig * 0.2;

    // Output chain (with Limiter for comb feedback)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_rlyeh loaded".postln;
