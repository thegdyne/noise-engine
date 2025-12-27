// throb: Biological pulse - deep rhythm
SynthDef(\forge_scorn_throb, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rate, deep, organ, pressure, alive;
    var throbMod;

    // Theme params
    rate = In.kr(customBus0).linexp(0, 1, 0.5, 2.5);        // P1: Throb rate
    deep = In.kr(customBus1).linlin(0, 1, 0.3, 1);          // P2: Deep sub
    organ = In.kr(customBus2).linlin(0, 1, 0.2, 0.7);       // P3: Organ resonance
    pressure = In.kr(customBus3).linlin(0, 1, 0.1, 0.6);    // P4: Blood pressure
    alive = In.kr(customBus4).linlin(0, 1, 0.2, 0.7);       // P5: Alive feeling

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

    // DSP: Throb modulation
    throbMod = LFPulse.kr(rate, 0, 0.35).lag(0.03, 0.2);

    // Deep sub pulse
    sig = SinOsc.ar(freq * 0.5) * deep * throbMod * 0.5;

    // Organ resonance - body cavity
    sig = sig + (BPF.ar(PinkNoise.ar(organ * 0.4), freq * [1, 2], 0.3) * throbMod.range(0.4, 1));

    // Blood pressure - rushing sound
    sig = sig + (LPF.ar(BrownNoise.ar(pressure * 0.4), 400 * throbMod.range(0.5, 1.5)));

    // Alive continuous presence
    sig = sig + (Saw.ar(freq * [1, 1.003]) * alive * 0.2);

    // Body warmth
    sig = sig + (SinOsc.ar(freq) * alive * 0.15);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_throb loaded".postln;
