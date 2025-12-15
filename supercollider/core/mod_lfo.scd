/*
Mod LFO SynthDef
TTLFO v2 inspired clock-synced LFO with 3 independent outputs

Each output has:
- Waveform select (8 types)
- Phase offset (0-315° in 45° steps)
- Polarity (unipolar 0-1 or bipolar -1 to +1)

Shared controls:
- Rate (clock division)
- Shape (waveform distortion / centre point shift)

Clock sync: Phase locked to master clock via ~clockTrigBus
Uses quarter note (index 6) as reference tick.

Reference: Ginkosynthese TTLFO v2
*/

SynthDef(\modLFO, {
    arg outA, outB, outC,           // Output bus indices
        rate = 0.5,                  // Clock division (0-1 maps to rate index)
        shape = 0.5,                 // Waveform distortion (0.5 = no distortion)
        waveA = 0, waveB = 0, waveC = 0,     // Waveform indices (0-7)
        phaseA = 0, phaseB = 0, phaseC = 0,  // Phase indices (0-7 = 0°-315°)
        polarityA = 1, polarityB = 1, polarityC = 1,  // 0=UNI, 1=BI
        clockTrigBus = 0;            // Clock trigger bus (audio rate impulses)
    
    var basePhase, pA, pB, pC;
    var sigA, sigB, sigC;
    var rateIndex, ticksPerCycle;
    var clk, trig, inc, tickCount;
    var wrapTrig, sah;
    
    // Waveform generation function
    var makeWave = { |p, waveIndex, shapeVal, sahSig|
        var saw, ramp, sqr, tri, sin, rectP, rectN;
        var sh = shapeVal.linlin(0, 1, 0.1, 0.9);
        
        // 0: Saw (ramp down)
        saw = 1 - p;
        
        // 1: Ramp (ramp up)
        ramp = p;
        
        // 2: Square (shape = PWM)
        sqr = (p < sh);
        
        // 3: Triangle (shape = symmetry)
        tri = Select.kr(p < sh,
            [1 - ((p - sh) / (1 - sh)), p / sh]
        );
        
        // 4: Sine
        sin = (p * 2pi).sin * 0.5 + 0.5;
        
        // 5: Rectified sine +
        rectP = (p * 2pi).sin.abs;
        
        // 6: Rectified sine -
        rectN = 1 - (p * 2pi).sin.abs;
        
        // 7: Sample & Hold (uses shared S&H signal)
        Select.kr(waveIndex.clip(0, 7), [saw, ramp, sqr, tri, sin, rectP, rectN, sahSig]);
    };
    
    // ---- CLOCK-SYNCED PHASE ----
    // Read quarter note clock (index 6 in clockTrigBus)
    clk = In.ar(clockTrigBus + 6);
    
    // Convert audio impulse to control rate trigger
    trig = A2K.kr(clk) > 0.5;
    trig = Trig1.kr(trig, 0.001);
    
    // RATE: 0-1 maps to 6 divisions: /4, /2, 1, x2, x3, x4
    // Ticks per cycle (tick = quarter note)
    // /4 = 4 quarters per cycle, /2 = 2, 1 = 1, x2 = 0.5, x3 = 0.333, x4 = 0.25
    rateIndex = (rate * 5).round.clip(0, 5);
    ticksPerCycle = Select.kr(rateIndex, [4, 2, 1, 0.5, 0.333, 0.25]);
    
    // Phase increments per tick (cycles per tick)
    inc = 1 / ticksPerCycle;
    tickCount = PulseCount.kr(trig);
    
    // Base phase 0..1, hard-locked to clock ticks
    basePhase = (tickCount * inc).frac;
    
    // S&H: sample once per LFO cycle (on phase wrap)
    wrapTrig = HPZ1.kr(basePhase) < 0;  // negative jump = wrap
    wrapTrig = Trig1.kr(wrapTrig, 0.001);
    sah = Latch.kr(WhiteNoise.kr, wrapTrig) * 0.5 + 0.5;
    
    // Phase offsets (index 0-7 = 0°-315° in 45° steps = 0-0.875)
    pA = (basePhase + (phaseA / 8)).wrap(0, 1);
    pB = (basePhase + (phaseB / 8)).wrap(0, 1);
    pC = (basePhase + (phaseC / 8)).wrap(0, 1);
    
    // Generate waveforms
    sigA = makeWave.(pA, waveA, shape, sah);
    sigB = makeWave.(pB, waveB, shape, sah);
    sigC = makeWave.(pC, waveC, shape, sah);
    
    // Apply polarity: 0=UNI (0 to 1), 1=BI (-1 to +1)
    sigA = Select.kr(polarityA, [sigA, sigA * 2 - 1]);
    sigB = Select.kr(polarityB, [sigB, sigB * 2 - 1]);
    sigC = Select.kr(polarityC, [sigC, sigC * 2 - 1]);
    
    // Output to control buses
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
}).add;

"  ✓ modLFO SynthDef loaded (clock-synced)".postln;
