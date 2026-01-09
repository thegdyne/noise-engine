/*
Mod Sloth SynthDef
NLC Triple Sloth inspired chaos modulation source

Uses coupled LFNoise2 oscillators to approximate strange attractor dynamics.
Per-mode bias scaling ensures exact timing windows matching NLC hardware specs.

Outputs:
- X: Primary chaos axis
- Y: Secondary chaos axis (coupled to X)
- Z: Inverted Y (as per NLC design)
- R: Gate output (fires on attractor transitions)

Controls:
- Mode: Torpor (15-30s), Apathy (60-90s), Inertia (30-40min)
- Bias: Controls cycle time within mode's range
        0 = slow end of range, 1 = fast end of range

Reference: Nonlinear Circuits 8HP Triple Sloth (Andrew F)
*/

SynthDef(\modSloth, {
    arg outX, outY, outZ, outR,      // 4 output bus indices
        mode = 0,                     // 0=Torpor, 1=Apathy, 2=Inertia
        bias = 0.5,                   // Speed within mode's range (0=slow, 1=fast)
        polarityX = 0, polarityY = 0, polarityZ = 0, polarityR = 0;  // 0=NORM, 1=INV
    
    var freq, x, y, z, r;
    var sigX, sigY, sigZ, sigR;
    var baseFreqs, scaleLo, scaleHi, biasScale;
    
    // Exact midpoint frequencies for each mode
    // Torpor midpoint (22.5s): 1/22.5 = 0.044444 Hz
    // Apathy midpoint (75s): 1/75 = 0.013333 Hz
    // Inertia midpoint (35min/2100s): 1/2100 = 0.000476 Hz
    baseFreqs = [
        0.044444444,  // Torpor midpoint
        0.013333333,  // Apathy midpoint
        0.0004761905  // Inertia midpoint
    ];
    
    // Per-mode bias scaling to hit exact timing windows
    // bias 0 = slow end (scaleLo), bias 1 = fast end (scaleHi)
    // Torpor: 15-30s -> scaleLo=0.75 (30s), scaleHi=1.5 (15s)
    // Apathy: 60-90s -> scaleLo=0.833 (90s), scaleHi=1.25 (60s)
    // Inertia: 30-40min -> scaleLo=0.875 (40min), scaleHi=1.167 (30min)
    scaleLo = Select.kr(mode.clip(0, 2), [0.75, 0.833333, 0.875]);
    scaleHi = Select.kr(mode.clip(0, 2), [1.5, 1.25, 1.166667]);
    
    // Interpolate between slow and fast based on bias
    biasScale = bias.linlin(0, 1, scaleLo, scaleHi);
    
    freq = Select.kr(mode.clip(0, 2), baseFreqs) * biasScale;
    
    // Coupled chaos oscillators (approximating Lorenz-like behavior)
    // X: Primary chaos signal
    x = LFNoise2.kr(freq);
    
    // Y: Secondary chaos signal (slightly different rate for coupling)
    y = LFNoise2.kr(freq * 0.9);
    
    // Add cross-modulation for chaotic interaction
    x = (x + (y * 0.3)).clip(-1, 1);
    y = (y + (x * 0.2)).clip(-1, 1);
    
    // Z: Inverted Y (as per NLC Triple Sloth design)
    z = y.neg;
    
    // R: Zero-crossing detector - fires when X crosses zero
    // Creates gate pulses similar to attractor wing transitions
    r = (x.abs < 0.15).lag(0.1);
    
    // Prepare outputs (all bipolar -1 to +1)
    sigX = x;
    sigY = y;
    sigZ = z;
    sigR = r * 2 - 1;  // Convert 0-1 to bipolar
    
    // Polarity invert option
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

"  [x] modSloth SynthDef loaded (4 outputs: X/Y/Z + R gate)".postln;
