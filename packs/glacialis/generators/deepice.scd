// DEEPICE - Sub-harmonic frozen mass
// Glacial drone with ice stress crackles

SynthDef(\forge_glacialis_deepice, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, flow, crack, depth, vast;
    var sub, fund, noise, lfo, crackle;

    // Theme params
    mass = In.kr(customBus0);      // Sub vs fundamental
    flow = In.kr(customBus1);      // Movement rate
    crack = In.kr(customBus2);     // Ice stress noise
    depth = In.kr(customBus3);     // Resonant depth
    vast = In.kr(customBus4);      // Stereo width

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

    // Glacial LFO for movement
    lfo = SinOsc.kr(flow.linexp(0, 1, 0.01, 0.2));

    // Sub-harmonic (one octave down)
    sub = SinOsc.ar(freq * 0.5) + (SinOsc.ar(freq * 0.25) * 0.5);
    sub = sub * mass;

    // Fundamental with slow PWM
    fund = Pulse.ar(freq, lfo.range(0.3, 0.7)) * 0.7;
    fund = fund + (Saw.ar(freq * 1.002) * 0.3);
    fund = fund * (1 - (mass * 0.5));

    // Ice stress crackles
    crackle = Dust.ar(crack.linexp(0, 1, 0.5, 30));
    crackle = Ringz.ar(crackle, freq * [2, 3.17, 5.43], 0.1).sum * 0.3;
    crackle = crackle * crack;

    // Combine
    sig = sub + fund + crackle;

    // Resonant filtering for depth
    sig = sig + (BPF.ar(sig, freq * 2, 0.1) * depth * 2);

    // Stereo spread
    sig = sig + (DelayC.ar(sig, 0.05, vast.linlin(0, 1, 0.001, 0.03)) * vast * 0.5);
    sig = [sig, DelayC.ar(sig, 0.05, vast.linlin(0, 1, 0.002, 0.04))];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_glacialis_deepice loaded".postln;
