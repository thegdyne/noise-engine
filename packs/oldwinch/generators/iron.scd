// oldwinch/iron — Lightweight end-stage generator
SynthDef(\forge_oldwinch_iron, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var forgeAmt, strike, blade, rust, tool;
    var trig, modes, exciter, ringTime, forgeHeat;

    forgeAmt = p[0];
    strike = p[1];
    blade = p[2];
    rust = p[3];
    tool = p[4];

    freq = In.kr(freqBus);

    // Strike trigger
    trig = Dust.ar(strike.linexp(0, 1, 1, 12));

    // Exciter - continuous + impacts
    exciter = PinkNoise.ar(0.15 * forgeAmt) + (trig * 0.5);

    // Ring time based on blade and rust
    ringTime = blade.linexp(0, 1, 0.1, 0.6) * (1 - (rust * 0.5));

    // Metal modal resonances - iron tool character
    modes = Ringz.ar(exciter, freq, ringTime, 0.3);
    modes = modes + Ringz.ar(exciter, freq * (1.5 + (tool * 0.5)), ringTime * 0.7, 0.25);
    modes = modes + Ringz.ar(exciter, freq * (2.2 + (tool * 0.8)), ringTime * 0.5, 0.2);
    modes = modes + Ringz.ar(exciter, freq * (3.1 + tool), ringTime * 0.4, 0.15 * blade);
    modes = modes + Ringz.ar(exciter, freq * (4.3 + (tool * 0.5)), ringTime * 0.3, 0.1 * blade);

    // Low resonance
    modes = modes + Ringz.ar(exciter, freq * 0.5, ringTime * 1.3, 0.2);

    sig = modes * 0.5;

    // Forge heat - crackling fire
    forgeHeat = Crackle.ar(1.5 + (forgeAmt * 0.4), 0.15 * forgeAmt);
    forgeHeat = BPF.ar(forgeHeat, 800 + (freq * 0.5), 0.4);
    sig = sig + forgeHeat;

    // Rust damping - filter and noise
    sig = LPF.ar(sig, rust.linexp(0, 1, 8000, 2000));
    sig = sig + (BPF.ar(BrownNoise.ar(0.1 * rust), freq, 0.3) * 2);

    // Continuous metal hum
    sig = sig + BPF.ar(PinkNoise.ar(0.15), freq, 0.25) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.08), 250);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_oldwinch_iron loaded".postln;
