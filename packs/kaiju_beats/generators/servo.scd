// kaiju_beats/servo — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_servo, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var ratio, whine, torque, jitter, motor;
    var master, slave, syncSig, motorNoise;

    ratio = p[0];  // P1: Sync ratio - harmonic content
    whine = p[1];  // P2: High frequency whine
    torque = p[2];  // P3: Motor torque/strain
    jitter = p[3];  // P4: Mechanical jitter
    motor = p[4];  // P5: Motor hum mix

    freq = In.kr(freqBus);
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

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_servo loaded".postln;
