// pilgrim: Hooded wanderer in the ruins
SynthDef(\forge_drowned_temple_pilgrim, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var breath, solitude, cloak, steps, reverence;

    // Theme params
    breath = In.kr(customBus0).linlin(0, 1, 0.2, 0.8);      // P1: Breath noise
    solitude = In.kr(customBus1).linlin(0, 1, 0.1, 0.6);    // P2: Lonely tone
    cloak = In.kr(customBus2).linlin(0, 1, 0.1, 0.5);       // P3: Fabric rustle
    steps = In.kr(customBus3).linlin(0, 1, 0.5, 3);         // P4: Footstep rate
    reverence = In.kr(customBus4).linlin(0, 1, 0.2, 0.7);   // P5: Reverent sub

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

    // DSP: Breath - filtered noise with slow modulation
    sig = BPF.ar(PinkNoise.ar(breath), freq * 2 * LFNoise1.kr(0.2).range(0.8, 1.2), 0.3) * 2;

    // Solitude - lonely wavering tone
    sig = sig + (SinOsc.ar(freq * [1, 1.003] * LFNoise1.kr(0.15).range(0.995, 1.005)) * solitude * 0.3);

    // Cloak rustle
    sig = sig + (HPF.ar(Dust2.ar(cloak * 10) * 0.1, 1500));

    // Soft footsteps
    sig = sig + (LPF.ar(Dust.ar(steps) * 0.2, 300).lag(0.01, 0.1));

    // Reverent sub drone
    sig = sig + (SinOsc.ar(freq * 0.5) * reverence * 0.25);

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_pilgrim loaded".postln;
