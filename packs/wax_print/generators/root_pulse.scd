// wax_print/root_pulse — Lightweight end-stage generator
// ============================================================================
// WAX_PRINT: Root Pulse
// Role: Bed - deep earth connection, grounding rhythmic foundation
//
// ERT (Earth)    - Sub depth, how deep the roots go
// GRW (Grow)     - Organic swell, breathing expansion
// SOL (Soil)     - Texture richness, harmonic earth
// ANC (Ancestor) - Ancient resonance, deep time
// SED (Seed)     - New growth sparkle, high overtones
// ============================================================================

SynthDef(\forge_wax_print_root_pulse, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var earth, grow, soil, ancestor, seed;
    var subRoot, midEarth, ancientHum, seedSparkle, growthMod;

    freq = In.kr(freqBus);

    earth = p[0].linlin(0, 1, 0.5, 0.125);  // Sub octave multiplier
    grow = p[1].linexp(0, 1, 0.05, 0.5);  // Growth rate
    soil = p[2].linlin(0, 1, 0.0, 1.0);
    ancestor = p[3].linlin(0, 1, 0.0, 1.0);
    seed = p[4].linlin(0, 1, 0.0, 1.0);

    // Organic growth modulation
    growthMod = SinOsc.kr(grow).range(0.9, 1.1);
    growthMod = growthMod * (1 + (LFNoise2.kr(grow * 0.5).range(-0.05, 0.05)));

    // Sub root - deep earth
    subRoot = SinOsc.ar(freq * earth * growthMod);
    subRoot = subRoot + (SinOsc.ar(freq * earth * 0.5 * growthMod) * 0.5);
    subRoot = subRoot * 0.5;

    // Mid earth - soil texture
    midEarth = Saw.ar(freq * growthMod) * soil * 0.3;
    midEarth = midEarth + (Pulse.ar(freq * growthMod, 0.3) * soil * 0.2);
    midEarth = LPF.ar(midEarth, freq * 3);
    // Add some grit
    midEarth = midEarth + (BrownNoise.ar * soil * 0.05);
    midEarth = LPF.ar(midEarth, freq * 4);

    // Ancestor resonance - deep time drone
    ancientHum = SinOsc.ar(freq * 0.25 * growthMod) * ancestor * 0.3;
    ancientHum = ancientHum + (Resonz.ar(PinkNoise.ar * 0.1, freq * 0.5, 0.1) * ancestor);
    // Ancient beating
    ancientHum = ancientHum * (1 + (SinOsc.kr(0.1).range(-0.2, 0.2) * ancestor));

    // Seed sparkle - new growth
    seedSparkle = Ringz.ar(Dust.ar(5 * seed + 1), freq * 4, 0.05) * seed * 0.2;
    seedSparkle = seedSparkle + (Ringz.ar(Dust.ar(3 * seed + 0.5), freq * 6, 0.03) * seed * 0.15);
    seedSparkle = HPF.ar(seedSparkle, freq * 2);

    sig = subRoot + midEarth + ancientHum + seedSparkle;

    // Gentle saturation for warmth
    sig = (sig * 1.5).tanh * 0.6;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_wax_print_root_pulse loaded".postln;
