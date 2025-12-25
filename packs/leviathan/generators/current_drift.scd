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

SynthDef(\forge_leviathan_current_drift, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flow, turbulence, debris, thermal, drag;
    var currentNoise, eddies, debrisParticles;
    var thermalLayers, flowMod, dragFilter;

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
    flow = In.kr(customBus0).linexp(0, 1, 0.05, 2.0);
    turbulence = In.kr(customBus1).linlin(0, 1, 0.0, 1.0);
    debris = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    thermal = In.kr(customBus3).linlin(0, 1, 0.0, 1.0);
    drag = In.kr(customBus4).linexp(0, 1, 200, 4000);

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
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_leviathan_current_drift loaded".postln;
