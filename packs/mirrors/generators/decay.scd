// mirrors/decay — Lightweight end-stage generator
SynthDef(\forge_mirrors_decay, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crumble, rust, crack, moss, years;
    var trig, crumbleNoise, rustCreak, resonances, ringTime;

    crumble = p[0];
    rust = p[1];
    crack = p[2];
    moss = p[3];
    years = p[4];

    freq = In.kr(freqBus);

    // Crumble trigger
    trig = Dust.ar(crumble.linexp(0, 1, 2, 20));

    // Ring time affected by moss damping
    ringTime = years.linexp(0, 1, 0.2, 0.08) * (1 - (moss * 0.4));

    // Resonances - cracked concrete
    resonances = Ringz.ar(trig, freq * (1 + (LFNoise0.kr(3) * crack * 0.2)), ringTime, 0.3);
    resonances = resonances + Ringz.ar(trig, freq * 1.5 * (1 + (LFNoise0.kr(2) * crack * 0.15)), ringTime * 0.7, 0.25);
    resonances = resonances + Ringz.ar(trig, freq * 2.2, ringTime * 0.5, 0.2 * (1 - moss));
    resonances = resonances + Ringz.ar(trig, freq * 0.7, ringTime * 1.2, 0.2);

    // Crumble noise texture
    crumbleNoise = BPF.ar(Crackle.ar(1.6 + (crumble * 0.3), 0.3), freq * 1.5, 0.4) * 2;
    crumbleNoise = crumbleNoise * (0.3 + (crumble * 0.7));

    // Rust creak - periodic groans
    rustCreak = SinOsc.ar(freq * 0.3 * LFNoise2.kr(0.2).range(0.9, 1.1), 0, 0.15 * rust);
    rustCreak = rustCreak * LFNoise2.kr(0.5).range(0.3, 1.0);

    sig = (resonances * 0.5) + crumbleNoise + rustCreak;

    // Years of decay filtering
    sig = LPF.ar(sig, years.linexp(0, 1, 6000, 1500));

    // Continuous concrete texture
    sig = sig + BPF.ar(BrownNoise.ar(0.2), freq, 0.35) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.12), 400);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_decay loaded".postln;
