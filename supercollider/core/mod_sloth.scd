/*
Mod Sloth SynthDef
NLC Triple Sloth inspired chaos modulation source

Outputs X, Y, Z from different stages of chaos circuit.
Z is inverted Y.

Controls:
- Mode: Torpor (15-30s), Apathy (60-90s), Inertia (30-40min)
- Bias: Attractor weight (time spent in each chaos state)

Reference: Nonlinear Circuits 8HP Triple Sloth (Andrew F)
*/

SynthDef(\modSloth, {
    arg outX, outY, outZ,           // Output bus indices
        mode = 0,                    // 0=Torpor, 1=Apathy, 2=Inertia
        bias = 0.5,                  // Attractor weight
        polarityX = 1, polarityY = 1, polarityZ = 1;  // 0=UNI, 1=BI
    
    var freq, x, y, z;
    var sigX, sigY, sigZ;
    var freqs, biasScaled;
    
    // Base frequencies for each mode
    // Torpor: 15-30s cycle = 0.033-0.067 Hz
    // Apathy: 60-90s cycle = 0.011-0.017 Hz
    // Inertia: 30-40min cycle = 0.0004-0.0006 Hz
    freqs = [
        0.05,    // Torpor (~20s)
        0.013,   // Apathy (~75s)
        0.0005   // Inertia (~33min)
    ];
    
    freq = Select.kr(mode.clip(0, 2), freqs);
    
    // Bias affects frequency slightly (simulating attractor weight)
    biasScaled = bias.linlin(0, 1, 0.7, 1.3);
    freq = freq * biasScaled;
    
    // Lorenz-like chaos system
    // Using coupled oscillators with feedback for chaotic behavior
    // This is a simplified approximation - true Lorenz would need more computation
    
    // X: Primary chaos signal
    x = LFNoise2.kr(freq * 1.1);
    
    // Y: Secondary chaos signal (coupled to X)
    y = LFNoise2.kr(freq * 0.9);
    
    // Add some cross-modulation for more chaotic interaction
    x = (x + (y * 0.3 * bias)).clip(-1, 1);
    y = (y + (x * 0.3 * (1 - bias))).clip(-1, 1);
    
    // Z: Inverted Y (as per NLC design)
    z = y.neg;
    
    // Scale to 0-1 range (unipolar base)
    sigX = x * 0.5 + 0.5;
    sigY = y * 0.5 + 0.5;
    sigZ = z * 0.5 + 0.5;
    
    // Apply polarity: 0=UNI (0 to 1), 1=BI (-1 to +1)
    sigX = Select.kr(polarityX, [sigX, x]);
    sigY = Select.kr(polarityY, [sigY, y]);
    sigZ = Select.kr(polarityZ, [sigZ, z]);
    
    // Output to control buses
    Out.kr(outX, sigX);
    Out.kr(outY, sigY);
    Out.kr(outZ, sigZ);
}).add;

"  ✓ modSloth SynthDef loaded".postln;
