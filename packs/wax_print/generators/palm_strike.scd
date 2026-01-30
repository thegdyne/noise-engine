// wax_print/palm_strike — Lightweight end-stage generator
// ============================================================================
// WAX_PRINT: Palm Strike
// Role: Accent - hand striking drum skin, djembe character
//
// SKN (Skin)     - Membrane tension, pitch
// SLP (Slap)     - Edge slap vs center tone
// BOD (Body)     - Drum body resonance
// SIZ (Size)     - Drum diameter
// HND (Hand)     - Hand technique, finger articulation
// ============================================================================

SynthDef(\forge_wax_print_palm_strike, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var skin, slap, body, size, hand;
    var membrane, slapNoise, bodyRes;
    var envTrig, pitchEnv;

    freq = In.kr(freqBus);

    skin = p[0].linexp(0, 1, 0.5, 2.0);
    slap = p[1].linlin(0, 1, 0.0, 1.0);
    body = p[2].linlin(0, 1, 0.0, 1.0);
    size = p[3].linexp(0, 1, 1.5, 0.5);
    hand = p[4].linlin(0, 1, 0.0, 1.0);

    envTrig = Select.ar(envSource, [
        Impulse.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

    // Pitch drop on strike
    pitchEnv = EnvGen.ar(Env([2, 1, 0.9], [0.005, 0.1], [\exp, \lin]), envTrig);

    // Membrane modes
    membrane = SinOsc.ar(freq * skin * size * pitchEnv);
    membrane = membrane + (SinOsc.ar(freq * 1.6 * skin * size * pitchEnv) * 0.5);
    membrane = membrane + (SinOsc.ar(freq * 2.14 * skin * size * pitchEnv) * 0.3);
    membrane = membrane * EnvGen.ar(Env.perc(0.001, 0.3), envTrig);

    // Slap (high, sharp)
    slapNoise = WhiteNoise.ar * slap;
    slapNoise = HPF.ar(slapNoise, 2000);
    slapNoise = slapNoise * EnvGen.ar(Env.perc(0.001, 0.03 + (hand * 0.02)), envTrig);

    // Body resonance
    bodyRes = Ringz.ar(envTrig * 0.1, freq * 0.5 * size, 0.2) * body;
    bodyRes = LPF.ar(bodyRes, 300);

    sig = membrane + slapNoise + bodyRes;

    // Hand articulation adds subtle pitch variation
    sig = sig * (1 + (LFNoise1.kr(20).range(-0.02, 0.02) * hand));

    sig = (sig * 2).clip(-1, 1) * 0.6;

    sig = ~stereoSpread.(sig, 0.1, 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_wax_print_palm_strike loaded".postln;
