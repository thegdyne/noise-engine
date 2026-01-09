/*
Mod LFO SynthDef
TTLFO v2 inspired clock-synced LFO with 4 independent outputs (quadrature)

Each output has:
- Waveform select (8 types)
- Phase offset (derived from pattern + rotate)
- Polarity = invert (outputs are always bipolar -1..+1)

Shared controls:
- Mode (0=CLK sync, 1=FREE running)
- Rate (CLK: clock division, FREE: manual frequency 0.01-100Hz)
- Shape (waveform distortion / centre point shift)
- Pattern (0-5: QUAD/PAIR/SPREAD/TIGHT/WIDE/SYNC)
- Rotate (0-23: 15 degree steps, shifts all phases together)

Global overrides (for mod matrix P1-P4):
- globalWave: when >= 0, overrides all waveA/B/C/D
- globalPolarity: when >= 0, overrides all polarityA/B/C/D

Phase patterns (degrees for A/B/C/D):
  QUAD:   0, 90, 180, 270  (classic quadrature)
  PAIR:   0, 0, 180, 180   (two pairs)
  SPREAD: 0, 45, 180, 225  (spread across cycle)
  TIGHT:  0, 22, 45, 67    (tight cluster)
  WIDE:   0, 120, 180, 300 (wide spread)
  SYNC:   0, 0, 0, 0       (all in phase)

Clock sync mode (mode=0):
- Uses x32 clock (index 12) = 32 triggers per quarter note
- Phasor generates smooth ramp between ticks
- PulseDivider resets phase on cycle boundary

Free mode (mode=1):
- Manual frequency 0.01-100Hz
- No clock reset, drifts freely
- Good for organic modulation

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
    arg outA, outB, outC, outD,      // 4 output bus indices (was 3)
        mode = 0,                     // 0=CLK, 1=FREE
        rate = 0.5,                   // CLK: division (0-1), FREE: freq (0-1 maps to 0.01-100Hz)
        shape = 0.5,                  // Waveform distortion (0.5 = no distortion)
        pattern = 0,                  // Phase pattern index (0-5)
        rotate = 0,                   // Phase rotation (0-23 = 0-345 deg in 15 deg steps)
        waveA = 0, waveB = 0, waveC = 0, waveD = 0,  // Waveform indices (0-7)
        polarityA = 0, polarityB = 0, polarityC = 0, polarityD = 0,  // 0=NORM, 1=INV
        globalWave = -1,              // P2: when >= 0, overrides all wave params
        globalPolarity = -1,          // P4: when >= 0, overrides all polarity params
        clockTrigBus = 0,             // Clock trigger bus base
        clockIndex = 12,              // Set from ~modClockSourceIndex in mod_slots.scd
        bpmBus = 0;                   // BPM control bus

    var basePhase, pA, pB, pC, pD;
    var sigA, sigB, sigC, sigD;
    var rateIndex, ticksPerCycle;
    var clk, trig, atrig, resetTrig, freq, modeSel;
    var wrapTrig, sah;
    var freeFreq, clkFreq;
    var patternPhases, rotateOffset;
    var phaseA, phaseB, phaseC, phaseD;
    var effWaveA, effWaveB, effWaveC, effWaveD;
	var effPolA, effPolB, effPolC, effPolD, gw, gp, makeWave;

    gw = globalWave.clip(0, 7).round(1);
    gp = globalPolarity.clip(0, 1).round(1);

    effWaveA = Select.kr(globalWave >= 0, [waveA.clip(0,7).round(1), gw]);
    effWaveB = Select.kr(globalWave >= 0, [waveB.clip(0,7).round(1), gw]);
    effWaveC = Select.kr(globalWave >= 0, [waveC.clip(0,7).round(1), gw]);
    effWaveD = Select.kr(globalWave >= 0, [waveD.clip(0,7).round(1), gw]);

    effPolA  = Select.kr(globalPolarity >= 0, [polarityA.clip(0,1).round(1), gp]);
    effPolB  = Select.kr(globalPolarity >= 0, [polarityB.clip(0,1).round(1), gp]);
    effPolC  = Select.kr(globalPolarity >= 0, [polarityC.clip(0,1).round(1), gp]);
    effPolD  = Select.kr(globalPolarity >= 0, [polarityD.clip(0,1).round(1), gp]);


    // Waveform generation function
	makeWave = { |p, waveIndex, shapeVal, sahSig|
        var saw, ramp, sqr, tri, sin, rectP, rectN;
		var sh = shapeVal.linlin(0, 1, 0.1, 0.9).clip(0.001, 0.999);


        // 0: Saw (ramp down)
        saw = 1 - p;

        // 1: Ramp (ramp up)
        ramp = p;

        // 2: Square (shape = PWM)
        sqr = (p < sh);

        // 3: Triangle (shape = symmetry)
        tri = Select.kr((p < sh), [
            1 - ((p - sh) / (1 - sh)),    // index 0 => p >= sh (fall)
            p / sh                        // index 1 => p < sh  (rise)
        ]);

        // 4: Sine
        sin = (p * 2pi).sin * 0.5 + 0.5;

        // 5: Rectified sine +
        rectP = (p * 2pi).sin.abs;

        // 6: Rectified sine -
        rectN = 1 - (p * 2pi).sin.abs;

        // 7: Sample & Hold (uses shared S&H signal)
        Select.kr(waveIndex.clip(0, 7).round(1), [saw, ramp, sqr, tri, sin, rectP, rectN, sahSig]);
    };

    // ---- PHASE PATTERN SELECTION ----

    // Pattern index 0-5 selects base phases (in 1/8ths of cycle, i.e. 45 deg steps)
    // Stored as [A, B, C, D] offsets
	patternPhases = Select.kr(pattern.clip(0, 5).round(1), [
        // QUAD: 0, 90, 180, 270 deg = 0, 2, 4, 6 (in 1/8ths)
        [0, 2, 4, 6],
        // PAIR: 0, 0, 180, 180 deg = 0, 0, 4, 4
        [0, 0, 4, 4],
        // SPREAD: 0, 45, 180, 225 deg = 0, 1, 4, 5
        [0, 1, 4, 5],
        // TIGHT: 0, 22.5, 45, 67.5 deg = 0, 0.5, 1, 1.5
        [0, 0.5, 1, 1.5],
        // WIDE: 0, 120, 180, 300 deg = 0, 2.67, 4, 6.67
        [0, 2.67, 4, 6.67],
        // SYNC: 0, 0, 0, 0 deg = 0, 0, 0, 0
        [0, 0, 0, 0]
    ]);

    // Rotate offset: 0-23 maps to 0-345 deg in 15 deg steps = 0-7.67 in 1/8ths
	rotateOffset = rotate.clip(0, 23).round(1) / 3;  // 24 steps / 8 eighths = 3

    // Calculate final phase offsets (in 0-1 range)
    phaseA = (patternPhases[0] + rotateOffset) / 8;
    phaseB = (patternPhases[1] + rotateOffset) / 8;
    phaseC = (patternPhases[2] + rotateOffset) / 8;
    phaseD = (patternPhases[3] + rotateOffset) / 8;

    // ---- MODE SELECTION ----
    // mode: 0 = CLK (clock synced), 1 = FREE (manual frequency)

    // ---- CLOCK-SYNCED MODE (mode = 0) ----
    // Read high-res clock (x32 = index 12 = 32 ticks per quarter)
    clk = In.ar(clockTrigBus + clockIndex);

	// ensure atrig spans >= 1-2 control blocks so A2K can't miss it
	atrig = Trig1.ar(clk > 0.5, ControlDur.ir * 2);
	trig  = Trig1.kr(A2K.kr(atrig) > 0, ControlDur.ir);

    // RATE (CLK mode): 0-1 maps to 12 divisions: /64, /32, /16, /8, /4, /2, 1, x2, x4, x8, x16, x32
    // Ticks per cycle at x32 resolution
    // Must match MOD_CLOCK_RATES order in Python config
    rateIndex = (rate * 11).round.clip(0, 11);

    // integer-safe divider (and never < 1)
	ticksPerCycle = Select.kr(rateIndex, [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]).round(1).max(1);

    // Reset trigger: fires once per LFO cycle (CLK mode only)
    resetTrig = PulseDivider.kr(trig, ticksPerCycle);

    // Calculate LFO frequency from BPM (CLK mode)
    // At 120 BPM: quarter = 2Hz, x32 tick = 64Hz
    // LFO freq = (bpm/60 * 32) / ticksPerCycle
    clkFreq = In.kr(bpmBus).max(1) / 60 * 32 / ticksPerCycle;

    // ---- FREE MODE (mode = 1) ----
    // Rate 0-1 maps exponentially to 0.01-100Hz
    freeFreq = rate.linexp(0, 1, 0.01, 100);

    // ---- SELECT FREQUENCY BASED ON MODE ----
    modeSel = mode.round.clip(0, 1);
    freq = Select.kr(modeSel, [clkFreq, freeFreq]);

    // ---- PHASE GENERATION ----
    // CLK mode: reset on cycle boundary
    // FREE mode: no reset (continuous)
    basePhase = Select.kr(modeSel, [
        Phasor.kr(resetTrig, freq * ControlDur.ir, 0, 1, 0),  // CLK: reset
        Phasor.kr(0,        freq * ControlDur.ir, 0, 1, 0)    // FREE: no reset
    ]);

	// FREE wrap detection: HPZ1 goes negative on wrap (near 1 -> near 0 jump)
	wrapTrig = Select.kr(modeSel, [
		trig,  // CLK: sample each clock tick
		Trig1.kr(HPZ1.kr(basePhase) < 0, ControlDur.ir)
	]);
    sah = Latch.kr(WhiteNoise.kr, wrapTrig) * 0.5 + 0.5;

    // Apply phase offsets (wrap to 0-1)
    pA = (basePhase + phaseA).wrap(0, 1);
    pB = (basePhase + phaseB).wrap(0, 1);
    pC = (basePhase + phaseC).wrap(0, 1);
    pD = (basePhase + phaseD).wrap(0, 1);

    // Generate waveforms (using effective wave params)
    sigA = makeWave.(pA, effWaveA, shape, sah);
    sigB = makeWave.(pB, effWaveB, shape, sah);
    sigC = makeWave.(pC, effWaveC, shape, sah);
    sigD = makeWave.(pD, effWaveD, shape, sah);

    // Always output -1 to +1 (true bipolar)
    // Polarity button now controls invert: 0=normal, 1=inverted
    sigA = sigA * 2 - 1;
    sigB = sigB * 2 - 1;
    sigC = sigC * 2 - 1;
    sigD = sigD * 2 - 1;

    // Apply effective polarity
    sigA = Select.kr(effPolA, [sigA, sigA.neg]);
    sigB = Select.kr(effPolB, [sigB, sigB.neg]);
    sigC = Select.kr(effPolC, [sigC, sigC.neg]);
    sigD = Select.kr(effPolD, [sigD, sigD.neg]);

    // Output to control buses
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
    Out.kr(outD, sigD);
}).add;

"  [x] modLFO SynthDef loaded (4 outputs, quadrature patterns, rotate, globalWave, globalPolarity)".postln;
