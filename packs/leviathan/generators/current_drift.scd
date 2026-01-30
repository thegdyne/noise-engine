// leviathan/current_drift — Lightweight end-stage generator
// ============================================================================
// LEVIATHAN: Current Drift
// Role: Motion - underwater currents carrying debris and sound
//
// FLO (Flow)     - Current strength, movement intensity
// TUR (Turbulence) - Chaotic eddies vs laminar flow
// DEB (Debris)   - Particles carried in the water
// THR (Thermal)  - Temperature layers, thermocline effects
// DRG (Drag)     - Resistance, viscosity of water
// ============================================================================

SynthDef(\forge_leviathan_current_drift, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var flow, turbulence, debris, thermal, drag;
    var currentNoise, eddies, debrisParticles;
    var thermalLayers, flowMod, dragFilter;

    // Read standard params
    freq = In.kr(freqBus);

    // === THEMED PARAMS ===
    flow = p[0].linexp(0, 1, 0.05, 2.0);
    turbulence = p[1].linlin(0, 1, 0.0, 1.0);
    debris = p[2].linlin(0, 1, 0.0, 1.0);
    thermal = p[3].linlin(0, 1, 0.0, 1.0);
    drag = p[4].linexp(0, 1, 200, 4000);

    // === FLOW MODULATION ===
    flowMod = LFNoise2.kr(flow).range(0.7, 1.3);

    // === CURRENT NOISE (base water movement) ===
    currentNoise = PinkNoise.ar * 0.5;
    currentNoise = currentNoise + (BrownNoise.ar * 0.3);
    // Resonant filter at base freq for tonal quality
    currentNoise = Resonz.ar(currentNoise, freq * flowMod, 0.2) * 3;
    currentNoise = currentNoise + (BPF.ar(PinkNoise.ar, freq * 2 * flowMod, 0.3) * 0.5);

    // === TURBULENT EDDIES ===
    eddies = LFNoise1.ar(flow * 10 * turbulence) * turbulence;
    eddies = eddies + (LFNoise2.ar(flow * 5) * turbulence * 0.5);
    // Chaotic modulation
    eddies = eddies * SinOsc.ar(flow * LFNoise0.kr(0.5).range(1, 5));
    eddies = LPF.ar(eddies, 500 + (turbulence * 1000));

    // === DEBRIS PARTICLES ===
    debrisParticles = Dust.ar(debris * 30 * flow) * 0.5;
    debrisParticles = Ringz.ar(debrisParticles, freq * LFNoise0.kr(2).range(0.5, 2), 0.05);
    debrisParticles = debrisParticles + (Crackle.ar(1.5 + (debris * 0.3)) * debris * 0.1);
    debrisParticles = BPF.ar(debrisParticles, freq * 2, 0.5);

    // === THERMAL LAYERS (filtered bands) ===
    thermalLayers = BPF.ar(currentNoise, freq * 0.5 * (1 + (thermal * 0.5)), 0.2) * thermal;
    thermalLayers = thermalLayers + BPF.ar(currentNoise, freq * 1.5 * (1 - (thermal * 0.3)), 0.15) * thermal * 0.7;
    // Slow modulation between layers
    thermalLayers = thermalLayers * SinOsc.kr(0.1).range(0.5, 1);

    // === DRAG FILTER ===
    sig = currentNoise + (eddies * 0.4) + (debrisParticles * 0.3) + (thermalLayers * 0.3);
    sig = LPF.ar(sig, drag);

    // Movement in stereo field
    sig = Balance2.ar(sig, DelayC.ar(sig, 0.05, LFNoise2.kr(flow).range(0.01, 0.04)),
                      LFNoise2.kr(flow * 0.5).range(-0.5, 0.5));

    // Soft saturation
    sig = (sig * 1.5).tanh * 0.5;

    // === OUTPUT CHAIN ===

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_leviathan_current_drift loaded".postln;
