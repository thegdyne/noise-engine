/*
Mod ARSEq+ SynthDef
4-output AR envelope sequencer with SEQ/PAR modes

Each output has independent AR envelope with:
- Attack time (0.1ms - 10s SYNC, 0.1ms - 120s LOOP)
- Release time (same ranges)
- Curve shape (LOG/LIN/EXP)
- Sync mode (SYNC: follow master, LOOP: self-cycle)
- Loop rate (when LOOP mode)
- Polarity (NORM: 0→+1, INV: 0→-1)

Master controls:
- Mode: SEQ (sequential 1→2→3→4) or PAR (parallel, all at once)
- Clock mode: CLK (sync to clock) or FREE (manual rate)
- Rate: master trigger rate

SEQ algorithm:
- Two pulses per envelope: pulse 1 = attack, pulse 2 = release
- env_idx = (seq_step // 2) % 4
- Cycles through envelopes in order

PAR algorithm:
- All envelopes triggered simultaneously
- Each runs independently

LOOP mode (per-envelope):
- Envelope self-retriggers at its own rate
- Overrides master clock for that envelope

Reference: docs/ARSEQ_PLUS_SPEC_v1.2.md
*/

SynthDef(\modARSeqPlus, {
    arg outA, outB, outC, outD,           // 4 output bus indices
        mode = 0,                          // 0=SEQ, 1=PAR
        clockMode = 0,                     // 0=CLK, 1=FREE
        rate = 0.5,                        // Master rate (0-1)
        // Per-envelope attack (0-1 normalized)
        atkA = 0.5, atkB = 0.5, atkC = 0.5, atkD = 0.5,
        // Per-envelope release (0-1 normalized)
        relA = 0.5, relB = 0.5, relC = 0.5, relD = 0.5,
        // Per-envelope curve (0=log, 0.5=lin, 1=exp)
        curveA = 0.5, curveB = 0.5, curveC = 0.5, curveD = 0.5,
        // Per-envelope sync mode (0=SYNC, 1=LOOP)
        syncModeA = 0, syncModeB = 0, syncModeC = 0, syncModeD = 0,
        // Per-envelope loop rate index (0-11)
        loopRateA = 6, loopRateB = 6, loopRateC = 6, loopRateD = 6,
        // Per-envelope polarity (0=NORM, 1=INV)
        polarityA = 0, polarityB = 0, polarityC = 0, polarityD = 0,
        // Clock infrastructure
        clockTrigBus = 0,
        clockIndex = 12,                   // x32 clock
        bpmBus = 0;

    var sigA, sigB, sigC, sigD;
    var envA, envB, envC, envD;
    var trigA, trigB, trigC, trigD;
    var gateA, gateB, gateC, gateD;
    var masterTrig, seqStep, seqTrig;
    var clk, atrig, trig;
    var rateIndex, ticksPerCycle, masterFreq;
    var freeFreq, clkFreq;
    var bpm;

    // Time mapping functions
    var mapSyncTime = { |norm| norm.linexp(0, 1, 0.0001, 10.0) };
    var mapLoopTime = { |norm| norm.linexp(0, 1, 0.0001, 120.0) };
    var mapCurve = { |norm| (norm * 2.0) - 1.0 };  // 0-1 → -1 to +1

    // Envelope generator function
    var makeEnv = { |gate, atkNorm, relNorm, curveNorm, isLoop|
        var atkTime, relTime, curve, env;
        // Use loop time range if in LOOP mode, sync range otherwise
        atkTime = Select.kr(isLoop, [mapSyncTime.(atkNorm), mapLoopTime.(atkNorm)]);
        relTime = Select.kr(isLoop, [mapSyncTime.(relNorm), mapLoopTime.(relNorm)]);
        curve = mapCurve.(curveNorm);
        
        // AR envelope with variable curve
        env = EnvGen.kr(
            Env.perc(atkTime, relTime, 1.0, curve),
            gate,
            doneAction: 0
        );
        env;
    };

    // ---- CLOCK INPUT ----
    clk = In.ar(clockTrigBus + clockIndex);
    atrig = Trig1.ar(clk > 0.5, 0.001);
    trig = Trig1.kr(A2K.kr(atrig), 0.001);

    // ---- MASTER RATE ----
    // CLK mode: rate 0-1 maps to 12 divisions
    rateIndex = (rate * 11).round.clip(0, 11);
    ticksPerCycle = Select.kr(rateIndex, [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]);
    
    bpm = In.kr(bpmBus);
    clkFreq = bpm / 60 * 32 / ticksPerCycle;
    
    // FREE mode: 0.01-100Hz
    freeFreq = rate.linexp(0, 1, 0.01, 100);
    
    masterFreq = Select.kr(clockMode.round, [clkFreq, freeFreq]);
    
    // Master trigger from clock or free-running impulse
    masterTrig = Select.kr(clockMode.round, [
        PulseDivider.kr(trig, ticksPerCycle),
        Impulse.kr(masterFreq)
    ]);

    // ---- SEQ MODE: SEQUENTIAL TRIGGERING ----
    // Count master pulses, 2 per envelope (attack + release phase)
    seqStep = PulseCount.kr(masterTrig) % 8;  // 0-7 (2 steps × 4 envelopes)
    
    // ---- TRIGGER GENERATION ----
    // SEQ mode: each envelope gets triggered in sequence
    // PAR mode: all envelopes triggered together
    
    // SEQ triggers: envelope N fires on steps 2N and 2N+1
    seqTrig = masterTrig;  // Use master trigger timing
    
    // Generate per-envelope gates
    // In SEQ: gate high during envelope's active steps
    // In PAR: all gates follow master
    gateA = Select.kr(mode.round, [
        // SEQ: active on steps 0,1
        (seqStep < 2) * Trig1.kr(masterTrig * (seqStep < 2), 0.001),
        // PAR: all triggered together
        Trig1.kr(masterTrig, 0.001)
    ]);
    
    gateB = Select.kr(mode.round, [
        ((seqStep >= 2) * (seqStep < 4)) * Trig1.kr(masterTrig * ((seqStep >= 2) * (seqStep < 4)), 0.001),
        Trig1.kr(masterTrig, 0.001)
    ]);
    
    gateC = Select.kr(mode.round, [
        ((seqStep >= 4) * (seqStep < 6)) * Trig1.kr(masterTrig * ((seqStep >= 4) * (seqStep < 6)), 0.001),
        Trig1.kr(masterTrig, 0.001)
    ]);
    
    gateD = Select.kr(mode.round, [
        (seqStep >= 6) * Trig1.kr(masterTrig * (seqStep >= 6), 0.001),
        Trig1.kr(masterTrig, 0.001)
    ]);

    // ---- LOOP MODE OVERRIDE ----
    // When envelope is in LOOP mode, it self-triggers at its own rate
    trigA = Select.kr(syncModeA.round, [
        gateA,
        Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateA.round.clip(0, 11), 
            [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]))
    ]);
    
    trigB = Select.kr(syncModeB.round, [
        gateB,
        Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateB.round.clip(0, 11),
            [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]))
    ]);
    
    trigC = Select.kr(syncModeC.round, [
        gateC,
        Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateC.round.clip(0, 11),
            [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]))
    ]);
    
    trigD = Select.kr(syncModeD.round, [
        gateD,
        Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateD.round.clip(0, 11),
            [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]))
    ]);

    // ---- ENVELOPE GENERATION ----
    envA = makeEnv.(trigA, atkA, relA, curveA, syncModeA);
    envB = makeEnv.(trigB, atkB, relB, curveB, syncModeB);
    envC = makeEnv.(trigC, atkC, relC, curveC, syncModeC);
    envD = makeEnv.(trigD, atkD, relD, curveD, syncModeD);

    // ---- OUTPUT SCALING ----
    // Convert 0-1 envelope to bipolar based on polarity
    // NORM (0): 0 to +1 → output 0 to +1
    // INV (1): 0 to +1 → output 0 to -1
    sigA = Select.kr(polarityA.round, [envA, envA.neg]);
    sigB = Select.kr(polarityB.round, [envB, envB.neg]);
    sigC = Select.kr(polarityC.round, [envC, envC.neg]);
    sigD = Select.kr(polarityD.round, [envD, envD.neg]);

    // ---- OUTPUT TO BUSES ----
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
    Out.kr(outD, sigD);
}).add;

"  ✓ modARSeqPlus SynthDef loaded (4 AR envelopes, SEQ/PAR modes)".postln;
