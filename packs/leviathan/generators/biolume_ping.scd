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

SynthDef(\forge_leviathan_biolume_ping, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var glow, flicker, swarm, dim, spark;
    var pingTrig, mainPing, swarmPings;
    var glowHarmonics, flickerMod, sparkTransient;
    var envTrig;

    // Read standard params
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // === THEMED PARAMS ===
    glow = In.kr(customBus0).linlin(0, 1, 0.0, 1.0);
    flicker = In.kr(customBus1).linlin(0, 1, 0.0, 1.0);
    swarm = In.kr(customBus2).linexp(0, 1, 0.5, 20);
    dim = In.kr(customBus3).linexp(0, 1, 0.1, 2.0);
    spark = In.kr(customBus4).linlin(0, 1, 0.0, 1.0);

    // === TRIGGER ===
    envTrig = Select.ar(envSource, [
        Impulse.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

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
    sig = ~stereoSpread.(sig, 0.3, 0.5);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_leviathan_biolume_ping loaded".postln;
