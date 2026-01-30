// oldwinch/beacon — Lightweight end-stage generator
SynthDef(\forge_oldwinch_beacon, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var flame, smoke, signalAmt, wood, windAmt;
    var trig, crackle, smokeNoise, resonances, woodRumble, windMod;

    flame = p[0];
    smoke = p[1];
    signalAmt = p[2];
    wood = p[3];
    windAmt = p[4];

    freq = In.kr(freqBus);

    // Wind modulation
    windMod = LFNoise2.kr(0.5 + (windAmt * 1.5)).range(0.6, 1.0);

    // Fire crackle trigger
    trig = Dust.ar(flame.linexp(0, 1, 5, 40));

    // Crackle texture
    crackle = Crackle.ar(1.7 + (flame * 0.25), 0.35 * flame);
    crackle = BPF.ar(crackle, freq * 2, 0.5) * 2;
    crackle = crackle * windMod;

    // Resonances - fire pops and snaps
    resonances = Ringz.ar(trig, freq * (1 + (LFNoise0.kr(5) * 0.2)), 0.05 + (signalAmt * 0.1), 0.3);
    resonances = resonances + Ringz.ar(trig, freq * 2 * (1 + (LFNoise0.kr(4) * 0.15)), 0.04, 0.2);
    resonances = resonances + Ringz.ar(trig, freq * 3, 0.03, 0.15 * signalAmt);

    // Smoke - filtered rising noise
    smokeNoise = BPF.ar(PinkNoise.ar(0.35), freq * smoke.linlin(0, 1, 1, 3), 0.5) * 2;
    smokeNoise = smokeNoise * LFNoise2.kr(0.3 + (smoke * 0.5)).range(0.4, 1.0);
    smokeNoise = smokeNoise * smoke;

    // Wood fuel rumble
    woodRumble = LPF.ar(BrownNoise.ar(0.4), 150 + (freq * 0.3));
    woodRumble = woodRumble * LFNoise2.kr(0.5).range(0.5, 1.0);
    woodRumble = woodRumble * (0.3 + (wood * 0.7));

    sig = crackle + resonances + smokeNoise + woodRumble;

    // Fire roar base
    sig = sig + BPF.ar(BrownNoise.ar(0.25), freq * 0.7, 0.4) * 2 * flame;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.12), 400);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_oldwinch_beacon loaded".postln;
