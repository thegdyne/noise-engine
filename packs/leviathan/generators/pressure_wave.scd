// ============================================================================
// LEVIATHAN: Pressure Wave
// Role: Motion - underwater pressure pulses, the weight of water
// 
// TON (Tonnage)  - Water mass above, sub frequency content
// WAV (Wave)     - Pulse shape and rate
// CRU (Crush)    - Compression intensity, sidechain-like pumping
// DEP (Depth)    - Distance traveled, diffusion
// TEC (Tectonic) - Seismic undertone, earth movement
// ============================================================================

SynthDef(\forge_leviathan_pressure_wave, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tonnage, wave, crush, depth, tectonic;
    var pressurePulse, subOsc, crushEnv;
    var tectonicRumble, depthDiffuse;
    var pulseRate, pulseTrig;

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
    tonnage = In.kr(customBus0).linlin(0, 1, 0.0, 1.0);
    wave = In.kr(customBus1).linexp(0, 1, 0.1, 2.0);
    crush = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    depth = In.kr(customBus3).linlin(0, 1, 0.0, 1.0);
    tectonic = In.kr(customBus4).linlin(0, 1, 0.0, 1.0);

    // === PRESSURE PULSE ===
    pulseRate = wave;
    pulseTrig = Impulse.kr(pulseRate);
    
    // Main pressure oscillator - low sine waves
    pressurePulse = SinOsc.ar(freq * 0.5);
    pressurePulse = pressurePulse + (SinOsc.ar(freq * 0.5 * 1.01) * 0.7);  // Beating
    pressurePulse = pressurePulse + (SinOsc.ar(freq) * 0.4);

    // === TONNAGE (sub frequencies) ===
    subOsc = SinOsc.ar(freq * 0.25) * tonnage;
    subOsc = subOsc + (SinOsc.ar(freq * 0.125) * tonnage * 0.5);
    subOsc = LPF.ar(subOsc, 100);

    // === CRUSH ENVELOPE (pumping compression feel) ===
    crushEnv = EnvGen.kr(
        Env([1, 1 - (crush * 0.7), 1], [0.05, wave.reciprocal * 0.8]),
        pulseTrig
    );
    
    pressurePulse = pressurePulse * crushEnv;

    // === TECTONIC RUMBLE ===
    tectonicRumble = LFNoise2.ar(freq * 0.1) * tectonic;
    tectonicRumble = tectonicRumble + (SinOsc.ar(freq * 0.0625 * LFNoise2.kr(0.05).range(0.95, 1.05)) * tectonic * 0.5);
    tectonicRumble = LPF.ar(tectonicRumble, 60);
    tectonicRumble = tectonicRumble * EnvGen.kr(Env([0, 1, 0.3, 0], [0.5, 2, 1]), Dust.kr(0.2 * tectonic));

    // === DEPTH DIFFUSION ===
    depthDiffuse = AllpassC.ar(pressurePulse, 0.3, LFNoise2.kr(0.1).range(0.05, 0.15), depth * 2);
    depthDiffuse = LPF.ar(depthDiffuse, 500);

    // === MIX ===
    sig = (pressurePulse * 0.4) + (subOsc * 0.3) + (tectonicRumble * 0.2) + (depthDiffuse * depth * 0.3);

    // Soft clip
    sig = (sig * 2).tanh * 0.5;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.08, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_leviathan_pressure_wave loaded".postln;
