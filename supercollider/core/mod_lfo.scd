/*
Mod LFO SynthDef
TTLFO v2 inspired clock-synced LFO with 3 independent outputs

Each output has:
- Waveform select (8 types)
- Phase offset (0-315° in 45° steps)
- Polarity (unipolar 0-1 or bipolar -1 to +1)

Shared controls:
- Rate (clock division/multiplication)
- Shape (waveform distortion / centre point shift)

Clock sync:
- Uses x32 clock (index 12) = 32 triggers per quarter note
- Phasor generates smooth ramp between ticks
- PulseDivider resets phase on cycle boundary

Rate table (ticks per cycle at x32):
  /64 = 2048 (16 bars)
  /32 = 1024 (8 bars)
  /16 = 512  (4 bars)
  /8  = 256  (2 bars)
  /4  = 128  (1 bar)
  /2  = 64   (2 beats)
  1   = 32   (1 beat)
  x2  = 16   (1/2 beat)
  x4  = 8    (1/4 beat)
  x8  = 4    (1/8 beat)
  x16 = 2    (1/16 beat)
  x32 = 1    (1/32 beat)

Reference: Ginkosynthese TTLFO v2
*/

SynthDef(\modLFO, {
    arg outA, outB, outC,           // Output bus indices
        rate = 0.5,                  // Clock division (0-1 maps to rate index)
        shape = 0.5,                 // Waveform distortion (0.5 = no distortion)
        waveA = 0, waveB = 0, waveC = 0,     // Waveform indices (0-7)
        phaseA = 0, phaseB = 0, phaseC = 0,  // Phase indices (0-7 = 0°-315°)
        polarityA = 1, polarityB = 1, polarityC = 1,  // 0=UNI, 1=BI
        clockTrigBus = 0,            // Clock trigger bus base
        clockIndex = 10,             // Set from ~modClockSourceIndex in mod_slots.scd
        bpmBus = 0;                  // BPM control bus
    
    var basePhase, pA, pB, pC;
    var sigA, sigB, sigC;
    var rateIndex, ticksPerCycle;
    var clk, trig, tickHz, resetTrig, freq;
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
    
    // ---- CLOCK-SYNCED PHASE (Smooth Phasor) ----
    // Read high-res clock (x32 = index 12 = 32 ticks per quarter)
    clk = In.ar(clockTrigBus + clockIndex);
    
    // Convert audio impulse to control-rate trigger robustly:
    // 1) stretch at audio-rate so we can't miss 1-sample impulses
    // 2) convert to control-rate and re-trigger as a short kr pulse
    var atrig;
    atrig = Trig1.ar(clk > 0.5, 0.001);     // 1ms audio pulse
    trig  = Trig1.kr(A2K.kr(atrig), 0.001); // 1ms control pulse
    
    // RATE: 0-1 maps to 12 divisions: /64, /32, /16, /8, /4, /2, 1, x2, x4, x8, x16, x32
    // Ticks per cycle at x32 resolution
    // Must match MOD_CLOCK_RATES order in Python config
    rateIndex = (rate * 11).round.clip(0, 11);
    ticksPerCycle = Select.kr(rateIndex, [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]);
    
    // Reset trigger: fires once per LFO cycle
    resetTrig = PulseDivider.kr(trig, ticksPerCycle);
    
    // Calculate LFO frequency from BPM
    // At 120 BPM: quarter = 2Hz, x32 tick = 64Hz
    // LFO freq = (bpm/60 * 32) / ticksPerCycle
    freq = In.kr(bpmBus) / 60 * 32 / ticksPerCycle;
    
    // Smooth phase ramp 0..1, resets on cycle boundary
    // Phasor gives continuous movement between ticks
    basePhase = Phasor.kr(resetTrig, freq * ControlDur.ir, 0, 1, 0);
    
    // S&H: sample once per LFO cycle (on reset trigger)
    sah = Latch.kr(WhiteNoise.kr, resetTrig) * 0.5 + 0.5;
    
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

"  ✓ modLFO SynthDef loaded (clock-synced, Phasor-smooth)".postln;
