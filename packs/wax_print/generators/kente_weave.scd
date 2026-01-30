// wax_print/kente_weave — Lightweight end-stage generator
// ============================================================================
// WAX_PRINT: Kente Weave
// Role: Bed - interlocking patterns like woven fabric
//
// WRP (Warp)     - Vertical thread density, base pulse rate
// WFT (Weft)     - Horizontal crossing, counter-rhythm intensity
// DYE (Dye)      - Color saturation, harmonic richness
// TGT (Tight)    - Weave tightness, envelope snap
// GLO (Gold)     - Metallic thread highlights
// ============================================================================

SynthDef(\forge_wax_print_kente_weave, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var warp, weft, dye, tight, gold;
    var warpPulse, weftCross, goldShine;
    var baseOsc, harmLayer;

    freq = In.kr(freqBus);

    // === THEMED PARAMS ===
    warp = p[0].linexp(0, 1, 1, 8);
    weft = p[1].linlin(0, 1, 0.0, 1.0);
    dye = p[2].linlin(0, 1, 0.0, 1.0);
    tight = p[3].linexp(0, 1, 0.3, 0.02);
    gold = p[4].linlin(0, 1, 0.0, 1.0);

    // === WARP (vertical pulse) ===
    warpPulse = Impulse.ar(warp);
    baseOsc = SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.001, tight), warpPulse);
    baseOsc = baseOsc + (SinOsc.ar(freq * 2) * EnvGen.ar(Env.perc(0.001, tight * 0.7), warpPulse) * 0.5);

    // === WEFT (cross-rhythm) ===
    weftCross = Impulse.ar(warp * 1.5);  // 3:2 polyrhythm
    weftCross = SinOsc.ar(freq * 1.5) * EnvGen.ar(Env.perc(0.001, tight), weftCross) * weft;
    weftCross = weftCross + (SinOsc.ar(freq * 0.75) * EnvGen.ar(Env.perc(0.001, tight * 1.2), Impulse.ar(warp * 0.75)) * weft * 0.7);

    // === DYE (harmonic color) ===
    harmLayer = Pulse.ar(freq, 0.3) * dye * 0.3;
    harmLayer = harmLayer + (Saw.ar(freq * 2) * dye * 0.2);
    harmLayer = LPF.ar(harmLayer, freq * 4);
    harmLayer = harmLayer * EnvGen.ar(Env.perc(0.01, tight * 2), warpPulse);

    // === GOLD (metallic highlights) ===
    goldShine = Ringz.ar(warpPulse, freq * 5, 0.1) * gold * 0.3;
    goldShine = goldShine + (Ringz.ar(warpPulse, freq * 7, 0.08) * gold * 0.2);
    goldShine = HPF.ar(goldShine, 1000);

    // === MIX ===
    sig = baseOsc + weftCross + harmLayer + goldShine;
    sig = (sig * 2).tanh * 0.5;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_wax_print_kente_weave loaded".postln;
