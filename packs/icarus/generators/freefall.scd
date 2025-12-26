// Freefall -- rushing descent, wind roar, tumbling
// Role: motion

SynthDef(\forge_icarus_freefall, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tumble, rush, void, spin, drag;
    var noise, sub, tumbleLfo, panLfo;

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

    // Theme params
    tumble = In.kr(customBus0).linlin(0, 1, 0.5, 12);    // Tumble rate Hz
    rush = In.kr(customBus1).linlin(0, 1, 0.1, 1.0);     // Noise intensity
    void = In.kr(customBus2).linlin(0, 1, 0.0, 0.6);     // Sub weight
    spin = In.kr(customBus3).linlin(0, 1, 0.1, 4);       // Pan rotation Hz
    drag = In.kr(customBus4).linexp(0, 1, 200, 4000);    // Internal filter

    // Tumbling modulation
    tumbleLfo = SinOsc.kr(tumble, 0, 0.3, 1);

    // Wind rush - filtered noise bands
    noise = PinkNoise.ar(rush) + WhiteNoise.ar(rush * 0.3);
    noise = BPF.ar(noise, freq * tumbleLfo, 0.4);
    noise = noise + BPF.ar(PinkNoise.ar(rush * 0.5), freq * 2 * tumbleLfo, 0.3);

    // Additional drag filtering
    noise = LPF.ar(noise, drag);

    // Sub void beneath
    sub = SinOsc.ar(freq * 0.25, 0, void);

    // Combine
    sig = noise + sub;

    // Stereo rotation - the tumble through space
    panLfo = SinOsc.kr(spin);
    sig = Pan2.ar(sig, panLfo);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_freefall loaded".postln;
