// wicker/wicker — Lightweight end-stage generator
SynthDef(\forge_wicker_wicker, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var weave, strain, hollow, cage, bound;
    var weaveMod, strainMod, hollowMod, cageMod, boundMod;
    var creaks, resonance, body, stress;

    // Read custom params
    weave = p[0];  // P1: Weave density - scaled by hollow
    strain = p[1];  // P2: Strain tension - curve set by bound
    hollow = p[2];  // P3: Hollow resonance - modulates weave AND cage
    cage = p[3];  // P4: Cage enclosure - feeds back to strain
    bound = p[4];  // P5: Bound captivity - master claustrophobia axis

    // BUTTERFLY EFFECT: Cross-modulation network
    weaveMod = weave * (0.4 + (hollow * 0.6));
    strainMod = strain.linexp(0, 1, 0.3, 6) * (1 + (cage * bound * 1.8));
    hollowMod = hollow * (1 + (bound.squared * 0.5));
    cageMod = cage * (0.3 + (weave * strain * 0.7));
    boundMod = bound * (1 + (hollow * cage * 0.35));

    freq = In.kr(freqBus);

    // DSP: Wicker structure creaking

    // Creaks: wood stress sounds
    creaks = Dust.ar(weaveMod.linexp(0, 1, 1, 15) * [1, 0.9]);
    creaks = Ringz.ar(creaks, freq * [1.3, 2.1, 3.4, 5.5], strainMod.linlin(0, 1, 0.03, 0.15)).sum;
    creaks = creaks + (Crackle.ar(strainMod.linlin(0, 1, 1.2, 1.7)) * 0.1 * boundMod);

    // Resonance: hollow body via comb filters
    resonance = PinkNoise.ar(0.15) + (BrownNoise.ar(0.1) * hollowMod);
    resonance = CombL.ar(resonance, 0.1, freq.reciprocal * hollowMod.linlin(0, 1, 0.8, 1.2), cageMod * 0.5);
    resonance = resonance + CombL.ar(resonance, 0.1, (freq * 1.5).reciprocal, cageMod * 0.3);
    resonance = resonance * 0.4;

    // Body: wood tone foundation
    body = Pulse.ar(freq * [1, 1.003], weaveMod.linlin(0, 1, 0.3, 0.6)) * 0.1;
    body = body + (Saw.ar(freq * 0.5) * 0.05 * hollowMod);
    body = RLPF.ar(body, freq * cageMod.linlin(0, 1, 2, 6), 0.4);

    // Stress: high tension harmonics
    stress = SinOsc.ar(freq * [5.3, 7.7, 11.2], 0, [0.03, 0.02, 0.01]).sum;
    stress = stress * strainMod.linlin(0, 1, 0.1, 1);
    stress = stress * (1 + (LFNoise1.kr(boundMod * 4) * 0.3));

    // Mix based on bound (claustrophobia axis)
    sig = (body * (1 - (boundMod * 0.4))) + resonance + (creaks * 0.5) + (stress * boundMod);

    // Enclosure effect
    sig = sig + (AllpassC.ar(sig, 0.05, LFNoise1.kr(0.3).range(0.01, 0.04), cageMod * 0.2) * 0.15);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_wicker_wicker loaded".postln;
