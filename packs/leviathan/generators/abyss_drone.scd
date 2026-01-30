// leviathan/abyss_drone — Lightweight end-stage generator
// ============================================================================
// LEVIATHAN: Abyss Drone
// Role: Bed - the eternal darkness of the deep
//
// VOD (Void)     - Depth into the abyss, brings in subsonic layers
// PRS (Pressure) - Crushing intensity, layered beating oscillators
// CUR (Current)  - Deep water movement, slow drift modulation
// BIO (Bio)      - Bioluminescent hints, occasional high sparkles
// RUM (Rumble)   - Tectonic rumble, infrasonic throb
// ============================================================================

SynthDef(\forge_leviathan_abyss_drone, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var void_depth, pressure, current, bio, rumble;
    var deepLayer, midLayer, subLayer, infraLayer;
    var bioSpark, currentMod, pressureBeat;
    var rumbleOsc, voidDrone;

    // Read standard params
    freq = In.kr(freqBus);

    // === THEMED PARAMS ===
    // VOD: Void depth - how deep into the abyss (0=surface murk, 1=hadal zone)
    void_depth = p[0].linlin(0, 1, 0.0, 1.0);

    // PRS: Pressure - crushing intensity via beating detuned layers
    pressure = p[1].linlin(0, 1, 0.0, 1.0);

    // CUR: Current - deep water movement modulation rate
    current = p[2].linexp(0, 1, 0.02, 0.5);

    // BIO: Bioluminescence - high frequency sparkle amount
    bio = p[3].linlin(0, 1, 0.0, 1.0);

    // RUM: Rumble - infrasonic tectonic throb
    rumble = p[4].linlin(0, 1, 0.0, 1.0);

    // === CURRENT MODULATION (affects everything) ===
    currentMod = LFNoise2.kr(current).range(0.97, 1.03);

    // === THE VOID (subsonic foundation) ===
    // Multiple octaves below the base frequency
    subLayer = SinOsc.ar(freq * 0.25 * currentMod) * 0.4;
    subLayer = subLayer + (SinOsc.ar(freq * 0.5 * currentMod * 1.002) * 0.3);  // Slight detune for thickness
    subLayer = subLayer * void_depth;

    // === PRESSURE (beating oscillators) ===
    // Closely detuned oscillators create crushing pressure feeling
    pressureBeat = SinOsc.ar(freq * currentMod);
    pressureBeat = pressureBeat + (SinOsc.ar(freq * 1.003 * currentMod) * pressure);
    pressureBeat = pressureBeat + (SinOsc.ar(freq * 0.997 * currentMod) * pressure);
    pressureBeat = pressureBeat + (SinOsc.ar(freq * 1.007 * currentMod) * pressure * 0.5);
    pressureBeat = pressureBeat * 0.3;

    // === INFRASONIC RUMBLE ===
    // Below hearing but felt - tectonic movement
    rumbleOsc = SinOsc.ar(freq * 0.125 * LFNoise2.kr(0.1).range(0.98, 1.02));
    rumbleOsc = rumbleOsc + (LFPulse.ar(freq * 0.0625, 0, 0.5) * 0.3);
    rumbleOsc = LPF.ar(rumbleOsc, 80) * rumble * 0.5;

    // === BIOLUMINESCENT SPARKLE ===
    // Rare, high, ethereal pings from the darkness
    bioSpark = Dust.ar(bio * 3 + 0.1) * 0.3;
    bioSpark = Ringz.ar(bioSpark, freq * 8 * LFNoise0.kr(2).range(0.8, 1.2), 0.3);
    bioSpark = bioSpark + Ringz.ar(Dust.ar(bio * 2), freq * 12, 0.2) * 0.5;
    bioSpark = HPF.ar(bioSpark, 2000) * bio;

    // === MIX THE ABYSS ===
    voidDrone = subLayer + pressureBeat + rumbleOsc;

    // Dark filtered noise bed
    deepLayer = PinkNoise.ar * 0.1 * void_depth;
    deepLayer = LPF.ar(deepLayer, 200 + (void_depth * 100));

    sig = voidDrone + deepLayer + bioSpark;

    // Gentle saturation for warmth
    sig = (sig * 1.5).tanh * 0.7;

    // === OUTPUT CHAIN ===

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_leviathan_abyss_drone loaded".postln;
