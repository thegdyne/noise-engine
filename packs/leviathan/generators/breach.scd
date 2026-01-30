// leviathan/breach — Lightweight end-stage generator
// ============================================================================
// LEVIATHAN: Breach
// Role: Accent - the explosive moment of breaking the surface
//
// MAS (Mass)     - Creature mass, adds lower detuned layers
// SRG (Surge)    - Upward surge intensity, pitch rise amount
// SPR (Spray)    - Water spray/splash noise component
// AIR (Air)      - Exposure to air, brightness increase
// DRP (Drop)     - Gravity's pull, the fall back down
// ============================================================================

SynthDef(\forge_leviathan_breach, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, surge, spray, air, drop;
    var bodyOsc, massLayers, surgeEnv, sprayNoise;
    var airBright, dropMod, breachSig;
    var envTrig;

    // Read standard params
    freq = In.kr(freqBus);

    // === THEMED PARAMS ===
    // MAS: Mass - adds weight via lower octave layers
    mass = p[0].linlin(0, 1, 0.0, 1.0);

    // SRG: Surge - upward pitch bend intensity
    surge = p[1].linlin(0, 1, 0.0, 0.5);

    // SPR: Spray - water splash noise amount
    spray = p[2].linlin(0, 1, 0.0, 1.0);

    // AIR: Air exposure - high frequency brightness
    air = p[3].linlin(0, 1, 0.0, 1.0);

    // DRP: Drop - pitch fall amount after peak
    drop = p[4].linlin(0, 1, 0.0, 0.3);

    // One-shot trigger (end-stage handles retriggering)
    envTrig = Impulse.ar(0);

    // === SURGE ENVELOPE (pitch rises then falls) ===
    surgeEnv = EnvGen.ar(
        Env([0, 1, 1 - drop], [0.1, 0.5], [\sine, \sine]),
        envTrig
    );

    // === BODY OSCILLATORS (thick supersaw-style) ===
    bodyOsc = Saw.ar(freq * (1 + (surgeEnv * surge)));
    bodyOsc = bodyOsc + (Saw.ar(freq * 1.005 * (1 + (surgeEnv * surge))) * 0.7);
    bodyOsc = bodyOsc + (Saw.ar(freq * 0.995 * (1 + (surgeEnv * surge))) * 0.7);
    bodyOsc = bodyOsc + (Saw.ar(freq * 1.01 * (1 + (surgeEnv * surge))) * 0.5);
    bodyOsc = bodyOsc + (Saw.ar(freq * 0.99 * (1 + (surgeEnv * surge))) * 0.5);
    bodyOsc = bodyOsc * 0.25;

    // === MASS LAYERS (lower octaves) ===
    massLayers = Saw.ar(freq * 0.5 * (1 + (surgeEnv * surge * 0.5)));
    massLayers = massLayers + (SinOsc.ar(freq * 0.25) * 0.5);
    massLayers = massLayers + (Pulse.ar(freq * 0.5, 0.3) * 0.3);
    massLayers = LPF.ar(massLayers, 500) * mass * 0.4;

    // === SPRAY NOISE (water explosion) ===
    sprayNoise = WhiteNoise.ar * spray;
    sprayNoise = sprayNoise * EnvGen.ar(Env.perc(0.01, 0.3), envTrig);
    sprayNoise = BPF.ar(sprayNoise, 3000 + (air * 5000), 0.5);
    sprayNoise = sprayNoise + (PinkNoise.ar * spray * 0.3 * EnvGen.ar(Env.perc(0.05, 0.5), envTrig));

    // === AIR BRIGHTNESS ===
    airBright = bodyOsc * air;
    airBright = HPF.ar(airBright, 1000);
    airBright = airBright + (Saw.ar(freq * 2 * (1 + (surgeEnv * surge))) * air * 0.2);

    // === MIX THE BREACH ===
    breachSig = bodyOsc + massLayers + sprayNoise + airBright;

    // Impact transient
    breachSig = breachSig + (SinOsc.ar(freq * 0.5) * EnvGen.ar(Env.perc(0.001, 0.1), envTrig) * mass * 0.5);

    sig = breachSig;

    // Hard clip for impact
    sig = (sig * 2).clip(-1, 1) * 0.7;

    // === OUTPUT CHAIN ===

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_leviathan_breach loaded".postln;
