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

SynthDef(\forge_leviathan_breach, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, surge, spray, air, drop;
    var bodyOsc, massLayers, surgeEnv, sprayNoise;
    var airBright, dropMod, breachSig;
    var trig, envTrig;

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
    // MAS: Mass - adds weight via lower octave layers
    mass = In.kr(customBus0).linlin(0, 1, 0.0, 1.0);
    
    // SRG: Surge - upward pitch bend intensity
    surge = In.kr(customBus1).linlin(0, 1, 0.0, 0.5);
    
    // SPR: Spray - water splash noise amount
    spray = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    
    // AIR: Air exposure - high frequency brightness
    air = In.kr(customBus3).linlin(0, 1, 0.0, 1.0);
    
    // DRP: Drop - pitch fall amount after peak
    drop = In.kr(customBus4).linlin(0, 1, 0.0, 0.3);

    // === TRIGGER FOR ENVELOPE SHAPES ===
    // Use MIDI or clock trigger for surge envelope
    envTrig = Select.ar(envSource, [
        Impulse.ar(0),  // OFF - continuous
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),  // CLK
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))  // MIDI
    ]);

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
    sig = ~stereoSpread.(sig, 0.1, 0.4);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_leviathan_breach loaded".postln;
