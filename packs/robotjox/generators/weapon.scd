// robotjox/weapon — Lightweight end-stage generator
SynthDef(\forge_robotjox_weapon, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spinRate, charge, teeth, motor, sparks;
    var chainsaw, beam, motorDrone, sparkBurst, teethRate;

    spinRate = p[0];
    charge = p[1];
    teeth = p[2];
    motor = p[3];
    sparks = p[4];

    freq = In.kr(freqBus);

    // Teeth rate for chainsaw rhythm
    teethRate = spinRate.linexp(0, 1, 10, 80);

    // Chainsaw - rhythmic noise bursts
    chainsaw = PinkNoise.ar(0.4) * LFPulse.ar(teethRate, 0, 0.5 + (teeth * 0.3)).lag(0.002);
    chainsaw = BPF.ar(chainsaw, freq * 2, 0.4) * 3;
    chainsaw = chainsaw + (Saw.ar(teethRate, 0.2) * teeth);

    // Motor drone base
    motorDrone = Saw.ar(freq * 0.5, 0.2 * motor);
    motorDrone = motorDrone + Pulse.ar(freq * 0.25, 0.4, 0.15 * motor);
    motorDrone = motorDrone * LFNoise2.kr(spinRate * 2).range(0.85, 1.0);

    // Beam charge - rising tone
    beam = SinOsc.ar(freq * (1 + (charge * LFSaw.kr(0.3).range(0, 1))), 0, 0.25 * charge);
    beam = beam + (WhiteNoise.ar(0.15) * charge * LFNoise2.kr(5).range(0, 1));
    beam = HPF.ar(beam, 500);

    // Contact sparks
    sparkBurst = WhiteNoise.ar(0.5) * Decay.ar(Dust.ar(sparks.linexp(0, 1, 2, 30)), 0.02);
    sparkBurst = HPF.ar(sparkBurst, 3000);

    sig = chainsaw + motorDrone + beam + sparkBurst;

    // Add mechanical base noise
    sig = sig + BPF.ar(BrownNoise.ar(0.2), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.1), 400);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_weapon loaded".postln;
