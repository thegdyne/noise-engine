// pripyat/reactor — Lightweight end-stage generator
SynthDef(\forge_pripyat_reactor, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var core, cool, throb, mass, warn;
    var baseDrone, feedbackAmt, throbMod, coolSig, warnSig, instability;

    freq = In.kr(freqBus);

    core = p[0];
    cool = p[1];
    throb = p[2];
    mass = p[3];
    warn = p[4];

    // Throbbing modulation
    throbMod = SinOsc.kr(throb.linexp(0, 1, 0.2, 4)).range(0.7, 1);

    // Core instability
    instability = LFNoise2.kr(core.linexp(0, 1, 0.1, 3)).range(
        1 - (core * 0.1),
        1 + (core * 0.1)
    );

    // Feedback amount varies with instability
    feedbackAmt = core.linlin(0, 1, 0.2, 0.9) * instability;

    // Main reactor drone - low frequency feedback FM
    baseDrone = SinOscFB.ar(freq * 0.5 * instability, feedbackAmt);
    baseDrone = baseDrone + SinOscFB.ar(freq * 0.25, feedbackAmt * 0.7);

    // Mass - add sub harmonics
    baseDrone = baseDrone + SinOsc.ar(freq * 0.125 * instability, 0, mass * 0.5);
    baseDrone = baseDrone * throbMod;

    // Cooling system - resonant mid frequencies
    coolSig = SinOscFB.ar(freq * cool.linexp(0, 1, 2, 6), 0.3);
    coolSig = coolSig * LFPulse.kr(cool.linexp(0, 1, 1, 8), 0, 0.5).lag(0.02);
    coolSig = coolSig * cool * 0.2;

    // Warning tone - distant alarm
    warnSig = SinOsc.ar(freq * 4 * LFPulse.kr(1, 0, 0.5).range(0.95, 1.05));
    warnSig = warnSig * LFPulse.kr(0.5, 0, 0.3);
    warnSig = LPF.ar(warnSig, 2000);
    warnSig = warnSig * warn * 0.15;

    // Mix
    sig = (baseDrone * 0.4) + coolSig + warnSig;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_reactor loaded".postln;
