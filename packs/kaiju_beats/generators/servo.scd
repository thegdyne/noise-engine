SynthDef(\forge_kaiju_beats_servo, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var ratio, whine, torque, jitter, motor;
    var master, slave, syncSig, motorNoise;

    // Theme params
    ratio = In.kr(customBus0);        // P1: Sync ratio - harmonic content
    whine = In.kr(customBus1);        // P2: High frequency whine
    torque = In.kr(customBus2);       // P3: Motor torque/strain
    jitter = In.kr(customBus3);       // P4: Mechanical jitter
    motor = In.kr(customBus4);        // P5: Motor hum mix

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
    ampVal = 0.2;

    // Jitter modulation
    freq = freq * (1 + (LFNoise0.kr(10 + (jitter * 40)) * jitter * 0.02));

    // Hard sync - master resets slave
    master = LFSaw.ar(freq);
    slave = SyncSaw.ar(freq, freq * (1.5 + (ratio * 6)));

    // Blend based on torque
    syncSig = XFade2.ar(master, slave, torque * 2 - 1);

    // High frequency whine - FM component
    syncSig = syncSig + (SinOsc.ar(freq * 8 * (1 + (whine * 4)), SinOsc.ar(freq * 12) * whine) * whine * 0.3);

    // Motor hum - low frequency
    motorNoise = SinOsc.ar(freq * 0.5) + (SinOsc.ar(freq * 0.25) * 0.5);
    motorNoise = motorNoise * motor * 0.3;

    // Add mechanical noise
    motorNoise = motorNoise + (BPF.ar(WhiteNoise.ar(0.2), freq * 4, 0.1) * jitter * 0.3);

    // Mix
    sig = (syncSig * 0.6) + motorNoise;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_kaiju_beats_servo loaded".postln;
