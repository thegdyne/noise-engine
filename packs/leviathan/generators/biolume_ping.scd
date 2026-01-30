// leviathan/biolume_ping — Lightweight end-stage generator
// ============================================================================
// LEVIATHAN: Biolume Ping
// Role: Accent - bioluminescent creatures signaling in darkness
//
// GLW (Glow)     - Luminescence intensity, harmonic brightness
// FLK (Flicker)  - Signal instability, organic variation
// SWM (Swarm)    - Multiple creatures, density of pings
// DIM (Dim)      - Fade distance, how far the light travels
// SPK (Spark)    - Initial flash intensity, attack brightness
// ============================================================================

SynthDef(\forge_leviathan_biolume_ping, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var glow, flicker, swarm, dim, spark;
    var pingTrig, mainPing, swarmPings;
    var glowHarmonics, flickerMod, sparkTransient;
    var envTrig;

    // Read standard params
    freq = In.kr(freqBus);

    // === THEMED PARAMS ===
    glow = p[0].linlin(0, 1, 0.0, 1.0);
    flicker = p[1].linlin(0, 1, 0.0, 1.0);
    swarm = p[2].linexp(0, 1, 0.5, 20);
    dim = p[3].linexp(0, 1, 0.1, 2.0);
    spark = p[4].linlin(0, 1, 0.0, 1.0);

    // One-shot trigger (end-stage handles retriggering)
    envTrig = Impulse.ar(0);

    // === MAIN PING (bell-like, pure) ===
    mainPing = SinOsc.ar(freq * 4) * EnvGen.ar(Env.perc(0.001, dim), envTrig);
    mainPing = mainPing + (SinOsc.ar(freq * 6) * EnvGen.ar(Env.perc(0.001, dim * 0.7), envTrig) * 0.5);
    mainPing = mainPing + (SinOsc.ar(freq * 8) * EnvGen.ar(Env.perc(0.001, dim * 0.5), envTrig) * 0.3);

    // === GLOW HARMONICS (sustained shimmer) ===
    glowHarmonics = SinOsc.ar(freq * 3) * glow * 0.3;
    glowHarmonics = glowHarmonics + (SinOsc.ar(freq * 5) * glow * 0.2);
    glowHarmonics = glowHarmonics + (SinOsc.ar(freq * 7) * glow * 0.1);
    glowHarmonics = glowHarmonics * EnvGen.ar(Env.perc(0.01, dim * 2), envTrig);

    // === FLICKER (organic instability) ===
    flickerMod = LFNoise2.kr(10 + (flicker * 20)).range(1 - (flicker * 0.3), 1);
    mainPing = mainPing * flickerMod;

    // === SWARM PINGS (multiple smaller creatures) ===
    swarmPings = Dust.ar(swarm) * 0.3;
    swarmPings = Ringz.ar(swarmPings, freq * 4 * LFNoise0.kr(5).range(0.8, 1.5), 0.1);
    swarmPings = swarmPings + Ringz.ar(Dust.ar(swarm * 0.5), freq * 6 * LFNoise0.kr(3).range(0.9, 1.3), 0.08) * 0.5;
    swarmPings = HPF.ar(swarmPings, 1000);

    // === SPARK TRANSIENT (initial flash) ===
    sparkTransient = WhiteNoise.ar * spark;
    sparkTransient = sparkTransient * EnvGen.ar(Env.perc(0.001, 0.02), envTrig);
    sparkTransient = HPF.ar(sparkTransient, 3000);
    sparkTransient = sparkTransient + (Impulse.ar(0) * EnvGen.ar(Env.perc(0.0001, 0.01), envTrig) * spark * freq * 0.001);

    // === MIX ===
    sig = (mainPing * 0.4) + (glowHarmonics * 0.3) + (swarmPings * 0.2) + (sparkTransient * 0.3);

    // High-pass to keep it ethereal
    sig = HPF.ar(sig, 500);

    // Soft limit
    sig = sig.tanh * 0.7;

    // === OUTPUT CHAIN ===

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_leviathan_biolume_ping loaded".postln;
