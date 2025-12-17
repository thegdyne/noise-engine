/*
Mod Sloth SynthDef
NLC Triple Sloth inspired chaos modulation source

Outputs:
- X: Primary chaos (fast movement)
- Y: Secondary chaos (coupled to X)
- Z: Inverted Y (as per NLC design)
- R: Rectified gate (fires when slow > fast, irregular bursts)

Controls:
- Mode: Torpor (15-30s), Apathy (60-90s), Inertia (30-40min)
- Bias: Attractor weight (time spent in each chaos state)

The R output creates gate-like pulses useful for triggering events.
It pulses when the slower chaos outputs exceed the faster one,
creating musically interesting irregular rhythms.

Reference: Nonlinear Circuits 8HP Triple Sloth (Andrew F)
*/

SynthDef(\modSloth, {
    arg outX, outY, outZ, outR,      // 4 output bus indices (was 3)
        mode = 0,                     // 0=Torpor, 1=Apathy, 2=Inertia
        bias = 0.5,                   // Attractor weight
        polarityX = 0, polarityY = 0, polarityZ = 0, polarityR = 0;  // 0=NORM, 1=INV
    
    var freq, x, y, z, r;
    var sigX, sigY, sigZ, sigR;
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
    
    // X: Primary chaos signal (faster movement)
    x = LFNoise2.kr(freq * 1.1);
    
    // Y: Secondary chaos signal (coupled to X, slower)
    y = LFNoise2.kr(freq * 0.9);
    
    // Add some cross-modulation for more chaotic interaction
    x = (x + (y * 0.3 * bias)).clip(-1, 1);
    y = (y + (x * 0.3 * (1 - bias))).clip(-1, 1);
    
    // Z: Inverted Y (as per NLC design)
    z = y.neg;
    
    // R: Rectified sum - fires when slow outputs exceed fast
    // Creates irregular gate-like pulses
    // max(0, y + z - x) simplified since z = -y:
    // max(0, y - y - x) = max(0, -x) = max(0, x.neg)
    // But more interesting: max(0, (y.abs + z.abs) - x.abs)
    r = ((y.abs + z.abs * 0.5) - x.abs).max(0);
    r = r * 2;  // Scale up for more prominent gate
    r = r.clip(0, 1);
    
    // Always output -1 to +1 (true bipolar)
    // x, y, z are already -1 to +1
    // r needs conversion from 0-1
    sigX = x;
    sigY = y;
    sigZ = z;
    sigR = r * 2 - 1;
    
    // Polarity button now controls invert: 0=normal, 1=inverted
    sigX = Select.kr(polarityX, [sigX, sigX.neg]);
    sigY = Select.kr(polarityY, [sigY, sigY.neg]);
    sigZ = Select.kr(polarityZ, [sigZ, sigZ.neg]);
    sigR = Select.kr(polarityR, [sigR, sigR.neg]);
    
    // Output to control buses
    Out.kr(outX, sigX);
    Out.kr(outY, sigY);
    Out.kr(outZ, sigZ);
    Out.kr(outR, sigR);
}).add;

"  ✓ modSloth SynthDef loaded (4 outputs: X/Y/Z + R gate)".postln;
