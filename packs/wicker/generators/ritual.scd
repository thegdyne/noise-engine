// wicker/ritual — Lightweight end-stage generator
SynthDef(\forge_wicker_ritual, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var drum, blood, bone, earth, fate;
    var drumMod, bloodMod, boneMod, earthMod, fateMod;
    var membrane, heartbeat, rattle, drone, strike;

    // Read custom params
    drum = p[0];  // P1: Drum tension - scaled by bone
    blood = p[1];  // P2: Blood pulse rate - curve set by fate
    bone = p[2];  // P3: Bone resonance - modulates drum AND earth
    earth = p[3];  // P4: Earth depth - feeds back to blood
    fate = p[4];  // P5: Fate inevitability - master doom axis

    // BUTTERFLY EFFECT: Cross-modulation network
    drumMod = drum * (0.4 + (bone * 0.6));
    bloodMod = blood.linexp(0, 1, 0.5, 6) * (1 + (earth * fate * 1.5));
    boneMod = bone * (1 + (fate.squared * 0.5));
    earthMod = earth * (0.35 + (drum * blood * 0.65));
    fateMod = fate * (1 + (bone * earth * 0.4));

    freq = In.kr(freqBus);

    // DSP: Tribal ritual drums

    // Strike: continuous triggering
    strike = Dust.ar(bloodMod * 2 * [1, 1.1]) + (Impulse.ar(0) * 0.5);

    // Membrane: drum body simulation
    membrane = Ringz.ar(
        strike,
        freq * drumMod.linlin(0, 1, 0.8, 1.5) * [1, 1.47, 2.09, 2.56],
        boneMod.linlin(0, 1, 0.08, 0.3)
    ).sum * 0.3;
    membrane = membrane + (SinOsc.ar(freq * 0.5, 0, 0.15) * Decay.ar(strike.sum, 0.2));

    // Heartbeat: low foundation pulse
    heartbeat = SinOsc.ar(freq * [0.25, 0.5], 0, [0.2, 0.12]).sum;
    heartbeat = heartbeat * (1 + (SinOsc.kr(bloodMod * 0.3) * earthMod * 0.3));
    heartbeat = heartbeat + (LFPulse.ar(freq * 0.25, 0, 0.3) * 0.08 * fateMod);

    // Rattle: bone percussion
    rattle = Dust.ar(drumMod.linexp(0, 1, 3, 25) * [1, 0.9]);
    rattle = Ringz.ar(rattle, freq * [3.2, 5.1, 7.4, 9.8], 0.02).sum * 0.15;
    rattle = rattle * boneMod.linlin(0, 1, 0.3, 1);

    // Drone: earth rumble
    drone = BrownNoise.ar(0.15) + (LFNoise1.ar(earthMod * 5) * 0.1);
    drone = RLPF.ar(drone, freq * earthMod.linlin(0, 1, 0.5, 2), 0.4);
    drone = drone * earthMod.linlin(0, 1, 0.2, 0.7);

    // Mix based on fate (doom axis)
    sig = membrane + heartbeat + (rattle * fateMod.linlin(0, 1, 0.5, 1.2)) + (drone * (1 + (fateMod * 0.5)));

    // Doom reverb tail
    sig = sig + (CombL.ar(sig, 0.2, earthMod.linlin(0, 1, 0.05, 0.15), fateMod * 0.8) * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_wicker_ritual loaded".postln;
