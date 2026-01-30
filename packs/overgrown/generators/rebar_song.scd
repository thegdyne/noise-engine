// overgrown/rebar_song — Lightweight end-stage generator
SynthDef(\forge_overgrown_rebar_song, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tension, rust, ringTime, strike, rods;
    var trig, exciter, pluck1, pluck2, pluck3, noise;

    tension = p[0];
    rust = p[1];
    ringTime = p[2];
    strike = p[3];
    rods = p[4];

    freq = In.kr(freqBus);

    // Continuous triggers for drone mode (higher minimum rate)
    trig = Dust.ar(rods.linexp(0, 1, 2, 12));

    // Exciter - filtered noise burst
    exciter = WhiteNoise.ar * Decay2.ar(trig, 0.0001, strike.linexp(0, 1, 0.003, 0.025));
    exciter = HPF.ar(exciter, strike.linexp(0, 1, 200, 2000));

    // Karplus-Strong metallic strings (balanced decay times)
    pluck1 = Pluck.ar(exciter, trig, 1/20, 1/(freq * tension.linexp(0, 1, 0.8, 1.2)), ringTime.linexp(0, 1, 1, 5), rust.linexp(0, 1, 0.15, 0.45));
    pluck2 = Pluck.ar(exciter, trig, 1/20, 1/(freq * 1.002 * tension.linexp(0, 1, 0.85, 1.15)), ringTime.linexp(0, 1, 0.8, 4), rust.linexp(0, 1, 0.2, 0.5)) * 0.7;
    pluck3 = Pluck.ar(exciter, trig, 1/20, 1/(freq * 2.01), ringTime.linexp(0, 1, 0.5, 3), rust.linexp(0, 1, 0.25, 0.55)) * rods * 0.4;

    // Rust noise layer (continuous bed for drone safety)
    noise = BPF.ar(PinkNoise.ar(0.15), freq * 2, 0.4) * rust * LFNoise1.kr(0.3).range(0.3, 1);
    noise = noise + (BPF.ar(BrownNoise.ar(0.08), freq, 0.5) * 0.3);

    // Combine
    sig = [pluck1 + (pluck3 * 0.7), pluck2 + (pluck3 * 0.7)] + noise;

    // HPF to prevent low-frequency buildup
    sig = HPF.ar(sig, 50);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_rebar_song loaded".postln;
